"""Seguimiento de donaciones y pedidos por código. Tras el match, el donante elige aquí cómo entregar el juguete."""
import plotly.graph_objects as go
import streamlit as st

from core import db, theme, tracking
from core.components import badge, fecha_legible, html, ilustracion, linea_tiempo
from core.events import registrar
from core.tracking import ALMACEN, ESTADOS_DONACION, ESTADOS_PEDIDO, RUTA_PEDIDO, buscar_por_codigo, siguiente_paso

html('<p class="fb-antetitulo">Seguimiento</p><h1>¿Dónde está mi juguete?</h1>'
     '<p>Escribe tu código de donación (<strong>FB-DON-…</strong>) o de pedido (<strong>FB-PED-…</strong>).</p>')

if st.session_state.get("eleccion_ok"):
    st.success(st.session_state.pop("eleccion_ok"), icon=":material/check_circle:")

inicial = st.query_params.get("codigo", st.session_state.get("ultimo_codigo", ""))
with st.form("buscar"):
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    codigo = c1.text_input("Código de seguimiento", value=inicial, placeholder="FB-DON-4827")
    enviar = c2.form_submit_button("Buscar", type="primary", width="stretch")

if not codigo:
    st.stop()
codigo = codigo.strip().upper()
st.query_params["codigo"] = codigo
res = buscar_por_codigo(codigo)
if not res:
    st.error("No encontramos ese código. Revisa que empiece por FB-DON- o FB-PED- y que los números sean correctos.")
    st.stop()

reg, hist = res["registro"], res["historial"]
fechas, notas = {}, {}
for h in hist:
    fechas[h["estado"]] = h["fecha"]
    notas[h["estado"]] = h["nota"]
actual = reg["estado"]
FINALES = ("rechazada", "rechazada_online", "retirada", "cancelado", "sustituido")

if res["tipo"] == "donacion":
    estados, tipo = ESTADOS_DONACION, reg["tipo"]
    ruta = tracking.ruta_donacion(tipo)
    if tipo == "particular" and ("llevar_a_punto" in fechas or actual == "llevar_a_punto"):
        ruta[ruta.index("recogida_programada")] = "llevar_a_punto"
    elif tipo == "empresa" and "recogida_programada" not in fechas and actual != "recogida_programada":
        ruta.remove("recogida_programada")
    juguetes = db.consulta("SELECT * FROM juguetes WHERE donacion_id = ?", (reg["id"],))
    titulo = (reg["producto"] or "Lote de empresa") if tipo == "empresa" else (juguetes[0]["nombre"] if juguetes else "Tu juguete")
else:
    estados, tipo = ESTADOS_PEDIDO, "pedido"
    ruta = list(RUTA_PEDIDO)
    if "en_recogida" not in fechas and actual != "en_recogida" and "revisado" in fechas:
        ruta.remove("en_recogida")
    if actual == "listo_punto" or "listo_punto" in fechas or (reg["modo_entrega"] == "punto" and "en_camino" not in fechas):
        ruta[ruta.index("en_camino")] = "listo_punto"
    juguetes = [db.juguete(reg["juguete_id"])]
    titulo = juguetes[0]["nombre"]
if actual in FINALES:
    ruta = [e for e in ruta if e in fechas and e != actual] + [actual]

idx_actual = ruta.index(actual) if actual in ruta else 0
tipo_badge = ("completado" if actual in ("entregada", "entregado") else
              "error" if actual in FINALES else "proceso")

c1, c2 = st.columns([1.4, 1], gap="large")
with c1:
    html(f'<p class="fb-antetitulo">{"Donación" if res["tipo"] == "donacion" else "Pedido"} {reg["codigo"]}</p>'
         f'<h2 style="margin-top:0">{titulo}</h2><p>{badge(estados[actual], tipo_badge)}</p>')
    hitos = []
    for i, e in enumerate(ruta):
        estado = "hecho" if i < idx_actual else ("actual" if i == idx_actual else "pendiente")
        hitos.append({"titulo": estados[e], "fecha": fecha_legible(fechas.get(e)) if i <= idx_actual else "",
                      "estado": estado})
    linea_tiempo(hitos)
    if actual in ("rechazada", "rechazada_online") and reg.get("motivo_rechazo"):
        st.warning(f"Motivo de la revisión: {reg['motivo_rechazo']}")
    if actual == "sustituido" and notas.get("sustituido"):
        st.info(notas["sustituido"], icon=":material/swap_horiz:")
    html(f'<div class="fb-etiqueta fb-sobrio"><p class="fb-antetitulo">Siguiente paso</p>'
         f'<p>{siguiente_paso(actual, tipo)}</p></div>')
    if actual in ("recibida", "revisada") or (res["tipo"] == "pedido" and actual in ("en_recogida", "revisado")):
        st.caption(f"📦 {ALMACEN['nombre']} · {ALMACEN['direccion']}")

with c2:
    if res["tipo"] == "donacion" and actual == "entregada":
        ped = db.uno("SELECT p.* FROM pedidos p JOIN juguetes j ON j.id = p.juguete_id WHERE j.donacion_id = ? "
                     "AND p.estado = 'entregado' ORDER BY p.id DESC", (reg["id"],))
        destino = "una familia" if ped and ped["destino"] == "familia" else "una entidad"
        franja = ped["franja"] if ped else ""
        html(f'<div class="fb-etiqueta" style="text-align:center">{theme.estrella_svg(40)}'
             f'<h3>Tu juguete ya tiene nuevo dueño</h3><p>Ha llegado a {destino}, para un niño de la franja '
             f'<strong>{franja} años</strong>.</p><p class="fb-meta">Por privacidad no mostramos más datos.</p></div>')
    elif juguetes:
        j = db.juguete(juguetes[0]["id"])
        from core.components import tarjeta_juguete
        html(tarjeta_juguete(j))
    else:
        html(f'<div class="fb-etiqueta"><img class="fb-ilus" src="{ilustracion("construccion")}" alt="" aria-hidden="true">'
             f'<h3>{titulo}</h3><p>{reg.get("unidades") or ""} unidades aproximadas. Las unidades aceptadas se crean '
             'tras la revisión de GUBI.</p></div>')

# --- Elección del donante tras el match -------------------------------------------
if res["tipo"] == "donacion" and actual == "emparejada":
    st.write("")
    with st.container(border=True):
        html(f'<p class="fb-antetitulo">Un niño ha elegido tu juguete</p><h3 style="margin-top:0">¿Cómo nos lo das?</h3>'
             f'<p>Tienes hasta el <strong>{tracking.fecha_corta(reg["plazo_eleccion"])}</strong> para elegir. Si no '
             'recibimos respuesta, el niño recibirá otro juguete parecido.</p>')
        modo = st.radio("Elige una opción", ["Que GUBI lo recoja en mi casa (gratis)", "Lo dejo en un punto de recogida"],
                        horizontal=True, key="eleccion_modo")
        pts = db.puntos()
        entrega: dict = {}
        if modo.startswith("Lo dejo"):
            e1, e2 = st.columns([1, 1.2], gap="large")
            with e1:
                p = st.selectbox("Punto de recogida", pts, format_func=lambda p: f"{p['barrio']} · {p['horario']}",
                                 index=next((i for i, x in enumerate(pts) if x["id"] == reg["punto_id"]), 0))
                st.caption(p["nombre"] + " · " + p["direccion"])
            with e2:
                fig = go.Figure(go.Scattermap(lat=[x["lat"] for x in pts], lon=[x["lon"] for x in pts], mode="markers",
                                              marker=dict(size=[20 if x["id"] == p["id"] else 12 for x in pts],
                                                          color=[theme.GRANADA if x["id"] == p["id"] else theme.NOCHE
                                                                 for x in pts]),
                                              text=[x["nombre"] for x in pts], hoverinfo="text"))
                fig.update_layout(map=dict(style="carto-positron", center=dict(lat=43.262, lon=-2.93), zoom=11.6),
                                  height=220, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, config={"displayModeBar": False})
            entrega = {"modo": "punto", "punto_id": p["id"]}
        else:
            e1, e2 = st.columns(2)
            direccion = e1.text_input("Dirección de recogida", placeholder="Calle, número, piso")
            franja = e2.selectbox("Franja horaria", ["Mañana (9-13 h)", "Mediodía (13-16 h)", "Tarde (16-20 h)"])
            entrega = {"modo": "domicilio", "direccion": direccion.strip(), "franja": franja,
                       "punto_id": reg["punto_id"]}
        if st.button("Confirmar mi elección", type="primary", icon=":material/check:"):
            if entrega["modo"] == "domicilio" and len(entrega.get("direccion", "")) < 6:
                st.error("Indica la dirección de recogida.")
            else:
                try:
                    tracking.elegir_entrega(reg["id"], entrega)
                except tracking.TransicionInvalida as e:
                    st.error(str(e))
                else:
                    registrar("donante_elige_entrega", "donante", reg["codigo"])
                    st.session_state["eleccion_ok"] = ("¡Gracias! GUBI pasará a recogerlo en la franja elegida."
                                                       if entrega["modo"] == "domicilio" else
                                                       "¡Gracias! Déjalo en el punto elegido en su horario.")
                    st.rerun()
