"""Organizaciones: necesidades, propuesta de reparto, revisión humana y aprobación."""
import re
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import allocation, db, tracking
from core.components import badge, html, seccion, texto_edad
from core.events import registrar

S = st.session_state
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOTIVOS = ["No es adecuado para nuestros niños", "Ya tenemos uno parecido", "Problema de espacio o tamaño",
           "No cumple una necesidad concreta", "Preferimos otra categoría"]

if not S.get("_ev_org"):
    registrar("cta_ver_servicio", "organizacion")
    S["_ev_org"] = True

with st.container(key="oscuro_org"):
    html('<p class="fb-antetitulo">Organizaciones</p><h1>Juguetes revisados para los niños que atendéis</h1>'
         '<p style="max-width:760px">Para ONG, centros de menores, hospitales y centros educativos. Nos contáis '
         'cuántos niños tenéis por edad y qué restricciones hay; el sistema propone un lote equitativo, vosotros lo '
         'revisáis y GUBI lo entrega.</p>')

c1, c2, c3 = st.columns(3)
for col, (t, d) in zip([c1, c2, c3], [
        ("1 · Enviad vuestras necesidades", "Niños por franja de edad, categorías y restricciones de seguridad."),
        ("2 · Revisad la propuesta", "Quitad o sustituid cualquier juguete indicando el motivo."),
        ("3 · Aprobad el reparto", "Los juguetes quedan reservados y GUBI organiza la entrega.")]):
    with col:
        html(f'<div class="fb-etiqueta fb-sobrio"><h4>{t}</h4><p>{d}</p></div>')


def guardar_propuesta(nec_id: int, prop: dict) -> None:
    ninos_nec = db.de_json(db.uno("SELECT ninos FROM necesidades WHERE id = ?", (nec_id,))["ninos"], {})
    allocation.recalcular_cobertura(prop, ninos_nec)
    db.actualizar("necesidades", nec_id, {"propuesta": db.a_json(prop)})


# --- Formulario ---------------------------------------------------------------------
if not S.get("nec_id"):
    seccion("Enviad vuestras necesidades")
    with st.form("necesidades"):
        c1, c2 = st.columns(2)
        codigo = c1.text_input("Código de entidad", placeholder="ORG-…",
                               help="Si ya colaboráis con nosotros, rellenamos vuestros datos.")
        tipo = c2.selectbox("Tipo de entidad", ["ONG", "Centro de menores", "Hospital", "Centro educativo", "Otra"])
        nombre = c1.text_input("Nombre de la entidad")
        contacto = c2.text_input("Persona de contacto")
        email = c1.text_input("Email de contacto")
        fecha_limite = c2.date_input("Fecha límite", value=date.today() + timedelta(days=21), min_value=date.today(),
                                     format="DD/MM/YYYY")
        st.markdown("**Número de niños por franja de edad**")
        cols = st.columns(5)
        ninos = {f: cols[i].number_input(f"{f} años", 0, 200, 0, key=f"n_{f}") for i, f in enumerate(db.FRANJAS)}
        categorias = st.multiselect("Categorías preferidas (opcional)", list(db.CATEGORIAS),
                                    format_func=lambda c: db.CATEGORIAS[c])
        st.markdown("**Restricciones**")
        rc = st.columns(3)
        restricciones = [r for i, (r, et) in enumerate(db.RESTRICCIONES.items()) if rc[i % 3].checkbox(et, key=f"r_{r}")]
        c1, c2 = st.columns(2)
        por_nino = c1.radio("Juguetes por niño", [1, 2], horizontal=True,
                            help="Con 2, primero se da uno a cada niño y solo después los segundos.")
        entrega = c2.selectbox("Preferencia de entrega", ["En nuestra sede", "Punto de encuentro"])
        enviar = st.form_submit_button("Enviar necesidades", type="primary", icon=":material/send:")
    if enviar:
        org = db.organizacion_por_codigo(codigo) if codigo else None
        nombre = nombre.strip() or (org["nombre"] if org else "")
        contacto = contacto.strip() or (org["contacto"] if org else "")
        email = email.strip() or (org["email"] if org else "")
        errores = []
        if codigo and not org:
            errores.append("No reconocemos ese código de entidad. Déjalo vacío si es vuestra primera vez.")
        if not nombre:
            errores.append("Indica el nombre de la entidad.")
        if not contacto:
            errores.append("Indica una persona de contacto.")
        if not EMAIL_RE.match(email):
            errores.append("Indica un email de contacto válido.")
        if sum(ninos.values()) == 0:
            errores.append("Indica cuántos niños hay al menos en una franja de edad.")
        for e in errores:
            st.error(e)
        if not errores:
            fl = fecha_limite.isoformat()
            nec_id = db.insertar("necesidades", {
                "organizacion_id": org["id"] if org else None, "nombre_entidad": nombre, "tipo": org["tipo"] if org else tipo,
                "contacto": contacto, "email": email, "codigo": codigo.strip().upper(), "ninos": db.a_json(ninos),
                "categorias": db.a_json(categorias), "restricciones": db.a_json(restricciones),
                "juguetes_por_nino": por_nino, "fecha_limite": fl, "entrega": entrega, "estado": "propuesta",
                "creado": db.ahora()})
            prop = allocation.repartir(ninos, allocation.stock_para(fl, nec_id), restricciones, categorias, por_nino)
            guardar_propuesta(nec_id, prop)
            registrar("necesidades_enviadas", "organizacion", str(nec_id))
            registrar("reparto_propuesto", "organizacion", str(nec_id))
            S["nec_id"] = nec_id
            st.rerun()

    st.write("")
    with st.expander("Prefiero hablar con el equipo"):
        with st.form("contacto_org", clear_on_submit=True):
            n = st.text_input("Nombre y entidad")
            e = st.text_input("Email")
            m = st.text_area("¿En qué os podemos ayudar?")
            if st.form_submit_button("Enviar mensaje"):
                if not n.strip() or not EMAIL_RE.match(e.strip()) or not m.strip():
                    st.error("Rellena nombre, un email válido y el mensaje.")
                else:
                    db.insertar("contactos", {"origen": "organizaciones", "nombre": n, "email": e, "mensaje": m,
                                              "creado": db.ahora()})
                    tracking.notificar("equipo@fabricadebaltasares.example", f"Contacto de organización: {n}", m)
                    registrar("contacto_equipo", "organizacion")
                    st.success("Mensaje enviado. Os escribiremos en 48 horas laborables.")
    st.stop()

# --- Propuesta y revisión ---------------------------------------------------------------
nec = db.uno("SELECT * FROM necesidades WHERE id = ?", (S["nec_id"],))
prop = db.de_json(nec["propuesta"], {})
ninos = db.de_json(nec["ninos"], {})
restricciones = db.de_json(nec["restricciones"])
asig = prop.get("asignaciones", [])
stock = {j["id"]: j for j in allocation.stock_para(nec["fecha_limite"], nec["id"])}

if nec["estado"] == "aprobada":
    if S.get("org_msg"):
        st.warning(S.pop("org_msg"))
    pedidos = db.consulta("SELECT codigo FROM pedidos WHERE necesidad_id = ?", (nec["id"],))
    html(f'<div class="fb-etiqueta fb-sobrio" style="text-align:center;padding:32px"><h2>Reparto aprobado</h2>'
         f'<p>Hemos reservado <strong>{len(pedidos)} juguetes</strong> para {nec["nombre_entidad"]}. GUBI os contactará '
         f'para coordinar la entrega antes del {nec["fecha_limite"]}.</p></div>')
    st.caption("Códigos de seguimiento: " + ", ".join(p["codigo"] for p in pedidos))
    if st.button("Enviar otra solicitud"):
        S.pop("nec_id")
        st.rerun()
    st.stop()

seccion("Propuesta de reparto", f"{nec['nombre_entidad']} · fecha límite {nec['fecha_limite']}", "Revisad y aprobad")
cub, total = prop.get("cubiertos_total", 0), prop.get("ninos_total", 0)
c1, c2, c3 = st.columns(3)
c1.metric("Niños cubiertos", f"{cub} de {total}")
c2.metric("Juguetes propuestos", len(asig))
c3.metric("Descartados por restricciones", prop.get("descartados_por_restricciones", 0))
if restricciones:
    st.caption("Restricciones aplicadas: " + ", ".join(db.RESTRICCIONES[r].lower() for r in restricciones) +
               ". Ningún juguete propuesto las incumple.")
for c in prop.get("conflictos", []):
    st.warning(c["motivo"], icon=":material/warning:")

usados = {a["juguete_id"] for a in asig}
for franja, cob in prop.get("cobertura", {}).items():
    tipo = "completado" if cob["cubiertos"] >= cob["ninos"] else "proceso"
    etiqueta = f"{cob['cubiertos']} de {cob['ninos']} niños"
    st.markdown(f"#### {franja} años &nbsp; {badge(etiqueta, tipo)}", unsafe_allow_html=True)
    filas = [a for a in asig if a["franja"] == franja]
    if not filas:
        st.caption("Sin juguetes disponibles para esta franja.")
    for i, a in enumerate(filas):
        j = db.juguete(a["juguete_id"])
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.4, 2, 1, 1.2], vertical_alignment="center")
            c1.markdown(f"**{j['nombre']}**  \n{db.CATEGORIAS[j['categoria']]} · {texto_edad(j['edad_min'], j['edad_max'])}"
                        f"{' · 2.º juguete' if a.get('ronda') == 2 else ''}")
            motivo = c2.selectbox("Motivo", MOTIVOS, key=f"mot_{a['juguete_id']}", label_visibility="collapsed")
            if c3.button("Quitar", key=f"q_{a['juguete_id']}", width="stretch"):
                asig.remove(a)
                db.insertar("correcciones", {"necesidad_id": nec["id"], "juguete_id": a["juguete_id"], "franja": franja,
                                             "accion": "quitar", "motivo": motivo, "ts": db.ahora()})
                prop["asignaciones"] = asig
                guardar_propuesta(nec["id"], prop)
                st.rerun()
            alternativas = [x for x in stock.values() if x["id"] not in usados and allocation.encaja_en_franja(x, franja)
                            and allocation.cumple_restricciones(x, restricciones)]
            alternativas.sort(key=lambda x: (x["categoria"] == j["categoria"], x["nombre"] == j["nombre"], x["id"]))
            if c4.button("Sustituir", key=f"s_{a['juguete_id']}", width="stretch", disabled=not alternativas):
                nuevo = alternativas[0]
                db.insertar("correcciones", {"necesidad_id": nec["id"], "juguete_id": a["juguete_id"],
                                             "sustituto_id": nuevo["id"], "franja": franja, "accion": "sustituir",
                                             "motivo": motivo, "ts": db.ahora()})
                a.update({"juguete_id": nuevo["id"], "nombre": nuevo["nombre"], "categoria": nuevo["categoria"]})
                prop["asignaciones"] = asig
                guardar_propuesta(nec["id"], prop)
                st.rerun()

correcciones = db.consulta("SELECT * FROM correcciones WHERE necesidad_id = ? ORDER BY id", (nec["id"],))
if correcciones:
    with st.expander(f"Correcciones registradas ({len(correcciones)})"):
        st.dataframe(pd.DataFrame(correcciones)[["ts", "franja", "accion", "motivo"]], hide_index=True)

st.write("")
c1, c2, _ = st.columns([1.2, 1, 1.5])
if c1.button("Aprobar el reparto", type="primary", icon=":material/task_alt:", disabled=not asig):
    creados, fallidos = 0, 0
    for a in asig:
        try:
            tracking.crear_pedido(a["juguete_id"], "organizacion", organizacion_id=nec["organizacion_id"],
                                  necesidad_id=nec["id"], franja=a["franja"], email=nec["email"],
                                  modo_entrega="punto" if nec["entrega"] == "Punto de encuentro" else "domicilio",
                                  nota="Reparto aprobado por la entidad")
            creados += 1
        except tracking.TransicionInvalida:
            fallidos += 1
    db.actualizar("necesidades", nec["id"], {"estado": "aprobada"})
    registrar("reparto_aprobado", "organizacion", str(nec["id"]))
    st.cache_data.clear()
    if fallidos:
        S["org_msg"] = f"{fallidos} juguetes ya no estaban disponibles y no se han incluido."
    st.rerun()
if c2.button("Empezar de nuevo", type="secondary"):
    db.actualizar("necesidades", nec["id"], {"estado": "descartada"})
    S.pop("nec_id")
    st.rerun()
