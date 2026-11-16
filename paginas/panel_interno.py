"""Panel interno de GUBI y del equipo (protegido por contraseña)."""
import os
from datetime import date

import pandas as pd
import streamlit as st

from core import ai, db, metrics, tracking
from core.components import badge, euros, fecha_legible, html, ilustracion, texto_edad
from core.tracking import ESTADOS_DONACION, ESTADOS_PEDIDO, MANUALES_DONACION, TRANSICIONES_PEDIDO

S = st.session_state

html('<p class="fb-antetitulo">Equipo · GUBI</p><h1>Panel interno</h1>')

clave = None
try:
    clave = st.secrets.get("panel_password")
except Exception:  # noqa: BLE001 - sin secrets.toml
    clave = None
clave = clave or os.environ.get("PANEL_PASSWORD")  # secretos como variables de entorno

if not S.get("panel_ok"):
    if not clave:
        st.error("Falta la contraseña del panel. Crea `.streamlit/secrets.toml` con `panel_password = \"...\"` "
                 "o define la variable de entorno `PANEL_PASSWORD` (ver README).")
        st.stop()
    with st.form("acceso"):
        pwd = st.text_input("Contraseña del panel", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            if pwd == clave:
                S["panel_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop()

tabs = st.tabs(["Revisión online", "Revisión física", "Operaciones", "Costes", "Bandeja de salida",
                "Embudo y orígenes", "Evaluación del matching", "Datos"])


def aviso_ok(msg: str) -> None:
    S["panel_msg"] = msg
    st.cache_data.clear()  # el catálogo y el dashboard reflejan el cambio al momento


if S.get("panel_msg"):
    st.toast(S.pop("panel_msg"), icon=":material/check_circle:")


def editor_etiquetas(base: dict, clave: str) -> dict:
    """Categoría, edad, intereses y condiciones, corregibles por quien revisa."""
    c1, c2 = st.columns(2)
    cats = list(db.CATEGORIAS)
    cat = c1.selectbox("Categoría", cats, index=cats.index(base["categoria"]),
                       format_func=lambda c: db.CATEGORIAS[c], key=f"c{clave}")
    ed = c2.slider("Edad", 0, 16, (min(base["edad_min"], 16), min(base["edad_max"], 16)), key=f"e{clave}")
    intereses = c1.multiselect("Intereses", list(ai.INTERESES), default=[i for i in base["intereses"] if i in ai.INTERESES],
                               key=f"i{clave}")
    restr = c2.multiselect("Condiciones verificadas", list(db.RESTRICCIONES), default=base["restricciones_cumplidas"],
                           format_func=lambda r: db.RESTRICCIONES[r], key=f"r{clave}")
    return {"categoria": cat, "edad_min": ed[0], "edad_max": 99 if ed[1] >= 16 and cat == "juego_mesa" else ed[1],
            "intereses": intereses, "restricciones": restr}


def base_juguete(j: dict) -> dict:
    return {"categoria": j["categoria"], "edad_min": j["edad_min"], "edad_max": j["edad_max"],
            "intereses": j["intereses"], "restricciones_cumplidas": j["restricciones"]}


def ficha_juguete(j: dict) -> None:
    st.write(j["descripcion"])
    st.caption(f"Estado declarado: {j['estado_fisico']}")
    fotos = [db.RAIZ / f for f in j["fotos"] if (db.RAIZ / f).exists()]
    if fotos:
        st.image([str(f) for f in fotos], width=180)
    else:
        html(f'<img src="{ilustracion(j["categoria"])}" alt="" style="width:180px;border-radius:12px">')
        st.caption("Juguete de demostración sin fotos reales: se muestra su ilustración. Las donaciones hechas desde "
                   "la web siempre traen fotos y aquí se ven las del donante.")


# --- 1. Revisión online (antes de publicar) ------------------------------------
with tabs[0]:
    cola = db.consulta("SELECT * FROM donaciones WHERE tipo = 'particular' AND estado = 'registrada' ORDER BY creado")
    st.caption(f"{len(cola)} juguetes esperando la revisión de sus fotos. Si se aprueban, se publican en el catálogo; "
               "el juguete sigue en casa del donante hasta que un niño lo elija.")
    if not cola:
        st.info("No hay fotos pendientes de revisar.")
    for don in cola:
        j = db.juguete(db.uno("SELECT id FROM juguetes WHERE donacion_id = ?", (don["id"],))["id"])
        with st.expander(f"{don['codigo']} · {j['nombre']}"):
            ficha_juguete(j)
            etiquetas = editor_etiquetas(base_juguete(j), f"on{don['id']}")
            a1, a2, a3 = st.columns([1, 1.4, 1])
            if a1.button("Aprobar y publicar", type="primary", key=f"onok{don['id']}"):
                tracking.revisar_online(don["id"], True, etiquetas=etiquetas)
                aviso_ok(f"{don['codigo']} publicada en el catálogo.")
                st.rerun()
            motivo = a2.selectbox("Motivo de rechazo", ["Las fotos no permiten ver el estado del juguete",
                                                        "No cumple los criterios de aceptación",
                                                        "Producto no admitido (electrónica, armas de juguete…)",
                                                        "Faltan piezas según la descripción"],
                                  key=f"onmot{don['id']}", label_visibility="collapsed")
            if a3.button("No publicar", type="secondary", key=f"onno{don['id']}"):
                tracking.revisar_online(don["id"], False, motivo)
                aviso_ok(f"{don['codigo']} no publicada: {motivo}.")
                st.rerun()

# --- 2. Revisión física (en el local de GUBI) -----------------------------------
with tabs[1]:
    cola = db.consulta("SELECT * FROM donaciones WHERE estado = 'recibida' ORDER BY creado")
    en_camino = db.uno("SELECT COUNT(*) n FROM donaciones WHERE estado IN ('recogida_programada','llevar_a_punto')")["n"]
    st.caption(f"{len(cola)} donaciones en el {tracking.ALMACEN['nombre']} esperando revisión física · {en_camino} "
               "todavía de camino (márcalas como recibidas en Operaciones). Si un juguete con niño asignado no la "
               "supera, el sistema le reserva otro parecido y avisa a la familia por email.")
    if not cola:
        st.info("No hay juguetes pendientes de revisión física.")
    for don in cola:
        juguetes = db.consulta("SELECT * FROM juguetes WHERE donacion_id = ?", (don["id"],))
        es_lote = don["tipo"] == "empresa" and not juguetes
        ped = tracking.pedido_activo_de_donacion(don["id"])
        titulo = (f"Lote · {don['producto']} ({don['unidades']} uds.) · {don['empresa_nombre']}" if es_lote
                  else juguetes[0]["nombre"] if juguetes else don["codigo"])
        with st.expander(f"{don['codigo']} · {titulo}" + (f" · para el pedido {ped['codigo']}" if ped else "")):
            if es_lote:
                base = ai.etiquetar_juguete(don["producto"], f"{don['producto']}. Edad {don['edad_texto']} años.")
                st.write(f"Motivo: {don['motivo']} · Edad indicada: {don['edad_texto']} · Contacto: {don['contacto']}")
            else:
                j = db.juguete(juguetes[0]["id"])
                base = base_juguete(j)
                ficha_juguete(j)
            etiquetas = editor_etiquetas(base, f"fi{don['id']}")
            unidades = None
            if es_lote:
                unidades = st.number_input("Unidades aceptadas tras la revisión (se crean como juguetes, máx. 60)",
                                           0, 60, min(int(don["unidades"] or 1), 20), key=f"ru{don['id']}")
                etiquetas.update({"nombre": don["producto"], "descripcion": don["producto"]})
            a1, a2, a3 = st.columns([1, 1.4, 1])
            if a1.button("Revisión superada", type="primary", key=f"ok{don['id']}"):
                tracking.revisar_fisica(don["id"], True, etiquetas=etiquetas, unidades=unidades)
                aviso_ok(f"{don['codigo']}: revisión física superada." +
                         (" Publícalo en Operaciones." if don["tipo"] == "empresa" else " El pedido sigue su curso."))
                st.rerun()
            motivo = a2.selectbox("Motivo de rechazo", ["Faltan piezas", "Pieza suelta pequeña sin sujeción",
                                                        "Pilas de botón accesibles", "Bordes cortantes o roturas",
                                                        "Higiene (manchas, olor)", "Aparato electrónico"],
                                  key=f"mot{don['id']}", label_visibility="collapsed")
            if a3.button("No la supera", type="secondary", key=f"no{don['id']}"):
                nuevo = tracking.revisar_fisica(don["id"], False, motivo)
                aviso_ok(f"{don['codigo']} rechazada: {motivo}." +
                         (f" Sustituto reservado: {nuevo['codigo']}." if nuevo else
                          " Se ha avisado a la familia." if ped else ""))
                st.rerun()

# --- Operaciones ------------------------------------------------------------------
with tabs[2]:
    sub = st.segmented_control("Ver", ["Donaciones", "Pedidos"], default="Donaciones", key="ops_ver", required=True)
    filtro = st.text_input("Buscar por código", key="ops_buscar", placeholder="FB-…").strip().upper()
    if sub == "Donaciones":
        estados = st.multiselect("Estados", list(ESTADOS_DONACION), format_func=lambda e: ESTADOS_DONACION[e],
                                 default=["emparejada", "recogida_programada", "llevar_a_punto", "registrada"],
                                 key="ops_est_d")
        filas = db.consulta("SELECT d.*, (SELECT nombre FROM juguetes j WHERE j.donacion_id = d.id LIMIT 1) AS juguete "
                            "FROM donaciones d ORDER BY d.creado DESC")
        filas = [f for f in filas if (not estados or f["estado"] in estados) and filtro in f["codigo"]][:40]
        if not filas:
            st.info("No hay donaciones con esos filtros.")
        for f in filas:
            with st.container(border=True):
                c1, c2 = st.columns([2.2, 2])
                detalle = ""
                if f["estado"] == "emparejada":
                    detalle = f" · el donante tiene hasta el {tracking.fecha_corta(f['plazo_eleccion'])} para elegir"
                elif f["estado"] == "recogida_programada" and f["tipo"] == "particular":
                    detalle = f" · recoger en casa · {f['franja_horaria'] or ''}"
                elif f["estado"] == "llevar_a_punto":
                    punto = db.uno("SELECT barrio FROM puntos WHERE id = ?", (f["punto_id"],))
                    detalle = f" · lo dejará en el punto de {punto['barrio'] if punto else '—'}"
                c1.markdown(f"**{f['codigo']}** · {f['juguete'] or f['producto'] or 'Lote'}  \n"
                            f"{'Empresa' if f['tipo'] == 'empresa' else 'Particular'} · {fecha_legible(f['creado'])}"
                            f"{detalle}")
                c1.markdown(badge(ESTADOS_DONACION[f["estado"]], "completado" if f["estado"] == "entregada" else "proceso"),
                            unsafe_allow_html=True)
                botones = [n for n in tracking.transiciones_donacion(f) if (f["estado"], n) in MANUALES_DONACION]
                with c2:
                    for n in botones:
                        texto = (f"→ {ESTADOS_DONACION[n]}" if n != "recibida" else
                                 f"→ Recibida en el {tracking.ALMACEN['nombre'].split(' · ')[0]}")
                        if st.button(texto, key=f"d{f['id']}{n}", width="stretch"):
                            tracking.cambiar_estado_donacion(f["id"], n, "Cambio desde el panel", manual=True)
                            aviso_ok(f"{f['codigo']}: {ESTADOS_DONACION[n]}")
                            st.rerun()
                    if f["estado"] == "emparejada":
                        if st.button("Anular match (sin respuesta en 3 días)", key=f"anu{f['id']}", type="secondary",
                                     width="stretch"):
                            nuevo = tracking.anular_match(f["id"])
                            aviso_ok(f"{f['codigo']}: match anulado." +
                                     (f" Sustituto reservado: {nuevo['codigo']}." if nuevo else ""))
                            st.rerun()
                    elif not botones:
                        st.caption({"registrada": "Pendiente de la revisión online (pestaña Revisión online).",
                                    "recibida": "Pendiente de la revisión física (pestaña Revisión física).",
                                    "publicada": "En el catálogo, esperando a que un niño lo elija.",
                                    "revisada": "El resto lo marca el pedido.",
                                    "asignada": "El resto lo marca el pedido."}.get(f["estado"], "Proceso cerrado."))
    else:
        estados = st.multiselect("Estados", list(ESTADOS_PEDIDO), format_func=lambda e: ESTADOS_PEDIDO[e],
                                 default=["solicitado", "en_recogida", "revisado", "preparado", "en_camino", "listo_punto"],
                                 key="ops_est_p")
        filas = db.consulta("SELECT p.*, j.nombre AS juguete FROM pedidos p JOIN juguetes j ON j.id = p.juguete_id "
                            "ORDER BY p.creado DESC")
        filas = [f for f in filas if (not estados or f["estado"] in estados) and filtro in f["codigo"]][:40]
        if not filas:
            st.info("No hay pedidos con esos filtros.")
        for f in filas:
            with st.container(border=True):
                c1, c2 = st.columns([2.2, 2])
                c1.markdown(f"**{f['codigo']}** · {f['juguete']}  \n{'Familia' if f['destino'] == 'familia' else 'Entidad'}"
                            f" · {f['franja']} años · {f['barrio'] or ''} · {fecha_legible(f['creado'])}")
                c1.markdown(badge(ESTADOS_PEDIDO[f["estado"]], "completado" if f["estado"] == "entregado" else
                                  ("error" if f["estado"] in ("cancelado", "sustituido") else "proceso")),
                            unsafe_allow_html=True)
                with c2:
                    siguientes = [n for n in TRANSICIONES_PEDIDO[f["estado"]] if n not in tracking.AUTOMATICOS_PEDIDO]
                    if f["estado"] in ("solicitado", "en_recogida"):
                        st.caption("Esperando a que el juguete llegue al local de GUBI y supere la revisión física.")
                    elif not siguientes:
                        st.caption("Proceso cerrado.")
                    for n in siguientes:
                        tipo = "secondary" if n == "cancelado" else "primary"
                        if st.button(f"→ {ESTADOS_PEDIDO[n]}", key=f"p{f['id']}{n}", type=tipo, width="stretch"):
                            tracking.cambiar_estado_pedido(f["id"], n, "Cambio desde el panel")
                            aviso_ok(f"{f['codigo']}: {ESTADOS_PEDIDO[n]}")
                            st.rerun()

# --- Costes ------------------------------------------------------------------------
with tabs[3]:
    camps = db.campanas()
    with st.form("coste", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        camp = c1.selectbox("Campaña", camps, format_func=lambda c: c["codigo"])
        concepto = c2.selectbox("Concepto", ["Recogida", "Entrega", "Revisión", "Gestión"])
        importe = c3.number_input("Importe (€)", min_value=0.0, step=5.0, value=0.0)
        fecha = c4.date_input("Fecha", value=date.today(), format="DD/MM/YYYY")
        nota = st.text_input("Nota (opcional)")
        if st.form_submit_button("Registrar coste", type="primary"):
            if importe <= 0:
                st.error("Indica un importe mayor que cero.")
            else:
                db.insertar("costes", {"campana_id": camp["id"], "concepto": concepto, "importe": importe,
                                       "fecha": fecha.isoformat(), "nota": nota})
                aviso_ok("Coste registrado.")
                st.rerun()
    k = metrics.kpis()
    st.metric("Coste medio por juguete entregado", euros(k["coste_medio"]),
              help="Suma de costes registrados ÷ juguetes entregados.")
    df = metrics.costes()
    if not df.empty:
        df = df.merge(pd.DataFrame(camps)[["id", "codigo"]], left_on="campana_id", right_on="id", suffixes=("", "_c"))
        st.dataframe(df[["fecha", "codigo", "concepto", "importe", "nota"]].sort_values("fecha", ascending=False),
                     hide_index=True, column_config={"importe": st.column_config.NumberColumn("Importe", format="%.2f €")})

# --- Bandeja de salida ----------------------------------------------------------------
with tabs[4]:
    st.caption("Todos los emails que genera la plataforma. Se envían por SMTP solo si hay credenciales en "
               "`.streamlit/secrets.toml`.")
    notis = db.consulta("SELECT * FROM notificaciones ORDER BY id DESC LIMIT 60")
    for n in notis:
        with st.expander(f"{fecha_legible(n['creado'])} · {n['destinatario']} · {n['asunto']}"):
            st.caption(n["estado"])
            st.text(n["cuerpo"])

# --- Embudo y orígenes ------------------------------------------------------------------
with tabs[5]:
    emb = metrics.embudo_eventos()
    publico = st.selectbox("Público", list(dict.fromkeys(emb["publico"])))
    vista = emb[emb["publico"] == publico]
    tabla = vista.pivot_table(index="src", columns=["paso", "evento"], values="n/N", aggfunc="first")
    tabla.columns = [f"{p}. {e}" for p, e in tabla.columns]
    st.dataframe(tabla, width="stretch")
    st.caption("Cada celda: sesiones que llegan a ese paso / sesiones del paso anterior. Origen = parámetro ?src= "
               "de la visita (QR del punto, LinkedIn, entidad…).")
    ev = pd.DataFrame(db.consulta("SELECT src, evento, COUNT(*) n FROM eventos GROUP BY src, evento"))
    with st.expander("Eventos agregados por origen y CTA"):
        st.dataframe(ev.pivot_table(index="evento", columns="src", values="n", fill_value=0), width="stretch")

# --- Evaluación del matching -------------------------------------------------------------
with tabs[6]:
    st.write("Ejecuta los casos de prueba sobre el stock actual y compara el emparejamiento con una referencia "
             "aleatoria de la edad correcta.")
    if st.button("Ejecutar evaluación", type="primary", icon=":material/science:"):
        from evaluation.evaluar_matching import evaluar

        with st.spinner("Evaluando…"):
            S["eval"] = evaluar()
    if S.get("eval"):
        r = S["eval"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Casos con algún interés cubierto", f"{r['resumen']['cobertura_sistema']:.0f} %")
        c2.metric("Referencia aleatoria", f"{r['resumen']['cobertura_referencia']:.0f} %")
        c3.metric("Restricciones incumplidas", f"{r['resumen']['incumplimientos_sistema']:.0f} %")
        c4.metric("Casos superados", f"{r['resumen']['superados']}/{r['resumen']['total']}")
        st.dataframe(pd.DataFrame(r["casos"]), hide_index=True, width="stretch")
        st.subheader("Reparto a organizaciones vs. reparto manual")
        st.dataframe(pd.DataFrame(r["reparto"]), hide_index=True, width="stretch")

# --- Datos ------------------------------------------------------------------------------
with tabs[7]:
    st.write("Reinicia la base con los datos de demostración (borra donaciones, pedidos y eventos creados en la demo).")
    if st.button("Reiniciar los datos de demostración", type="secondary", icon=":material/restart_alt:"):
        S["confirmar_reset"] = True
    if S.get("confirmar_reset"):
        st.warning("Se perderán todos los cambios hechos desde el último reinicio.")
        c1, c2, _ = st.columns([1, 1, 2])
        if c1.button("Sí, reiniciar", type="primary"):
            db.inicializar(forzar=True)
            st.cache_data.clear()
            S.pop("confirmar_reset")
            aviso_ok("Datos de demostración reiniciados.")
            st.rerun()
        if c2.button("Cancelar"):
            S.pop("confirmar_reset")
            st.rerun()
    if st.button("Cerrar sesión del panel"):
        S["panel_ok"] = False
        st.rerun()
