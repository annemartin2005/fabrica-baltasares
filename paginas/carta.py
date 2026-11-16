"""Carta a los Reyes: acceso con código, carta anonimizada, interpretación, propuesta explicada y reserva."""
import uuid

import streamlit as st

from core import ai, db, matching, theme, tracking
from core.components import chips, estrellas, html, modo_ia, tarjeta_juguete
from core.events import registrar

S = st.session_state
S.setdefault("familia_ref", "F-" + uuid.uuid4().hex[:8].upper())

EJEMPLO = ("Queridos Reyes Magos: tengo 6 años y este año me he portado muy bien. Me encantan los dinosaurios y "
           "pintar. No me gustan mucho los peluches. ¡Gracias!")

html('<p class="fb-antetitulo">Pedir juguetes</p><h1>Carta a los Reyes</h1>'
     '<p style="max-width:720px">Escribe con tu hijo o hija lo que le gustaría. Leemos la carta, entendemos qué le '
     'ilusiona y te proponemos tres juguetes revisados que encajan con su edad.</p>')

# --- 1. Acceso con código de entidad ----------------------------------------------
if not S.get("entidad"):
    with st.form("acceso_entidad"):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        codigo = c1.text_input("Código de tu entidad", placeholder="REYES-…",
                               help="Te lo facilita tu entidad derivadora: servicios sociales, una ONG o el colegio.")
        entrar = c2.form_submit_button("Continuar", type="primary", width="stretch")
    if entrar:
        ent = db.entidad_por_codigo(codigo)
        if ent:
            S["entidad"] = ent
            st.rerun()
        st.error("No reconocemos ese código. Revisa que esté bien escrito o pide uno nuevo a tu entidad.")
    html('<div class="fb-etiqueta fb-sobrio"><h3>¿No tienes código?</h3><p>Las familias llegan a través de una '
         '<strong>entidad derivadora</strong>: los servicios sociales de tu barrio, una ONG o el colegio. Pídeles el '
         'código de La Fábrica de Baltasares: así no tienes que enseñarnos ningún documento.</p>'
         '<p>Mientras tanto, puedes ver qué juguetes hay en el catálogo.</p></div>')
    st.write("")
    if st.button("Ver catálogo", type="secondary", icon=":material/toys:"):
        registrar("cta_ver_catalogo", "familia")
        st.switch_page("paginas/catalogo.py")
    st.stop()

ent = S["entidad"]
c1, c2 = st.columns([4, 1], vertical_alignment="center")
c1.success(f"Acceso con el código de **{ent['nombre']}**.", icon=":material/verified_user:")
if c2.button("Cambiar código", type="secondary"):
    for k in ("entidad", "carta", "prop_excluir", "pedido_ok"):
        S.pop(k, None)
    st.rerun()

# --- Pedido confirmado -------------------------------------------------------------------
if S.get("pedido_ok"):
    p = S["pedido_ok"]
    html(f'<div class="fb-etiqueta" style="text-align:center;padding:36px">{theme.estrella_svg(44)}'
         f'<h2>¡Carta respondida!</h2><p>Hemos reservado <strong>{p["juguete"]}</strong>. '
         f'{p["entrega"]}</p><p class="fb-antetitulo" style="margin-top:12px">Código de seguimiento</p>'
         f'<div class="fb-cifra-grande" style="color:var(--noche)">{p["codigo"]}</div>'
         '<p class="fb-meta">Hemos enviado la confirmación por email. Te avisaremos en cada paso.</p></div>')
    c1, c2, _ = st.columns([1, 1.3, 1])
    if c1.button("Ver el seguimiento", type="primary", icon=":material/local_shipping:"):
        st.switch_page("paginas/seguimiento.py", query_params={"codigo": p["codigo"]})
    if c2.button("Escribir otra carta (otro hermano)", type="secondary"):
        for k in ("carta", "prop_excluir", "pedido_ok"):
            S.pop(k, None)
        st.rerun()
    st.stop()

# --- 2. Escritura ---------------------------------------------------------------------------
if not S.get("carta"):
    st.subheader("Escribe la carta")
    c1, c2 = st.columns(2)
    edad = c1.selectbox("Edad del niño o niña", list(range(0, 17)), index=None, placeholder="Elige la edad",
                        format_func=lambda e: "Menos de 1 año" if e == 0 else f"{e} años")
    franja = c2.selectbox("Franja de entrega preferida", ["Tarde (16-20 h)", "Mañana (9-13 h)", "Sábado por la mañana"])
    st.warning("No escribas nombres, apellidos ni direcciones. Si aparecen, los quitaremos antes de guardar la carta.",
               icon=":material/privacy_tip:")
    with st.expander("Ver una carta de ejemplo"):
        st.write(f"*{EJEMPLO}*")
    with st.container(key="papel_carta"):
        texto = st.text_area("Querid@s Reyes Magos…", height=260, max_chars=1200,
                             placeholder="Este año me gustaría…", key="texto_carta")
    email = st.text_input("Email para avisarte (opcional)", placeholder="Si lo dejas vacío, avisaremos a tu entidad")
    if st.button("Enviar la carta", type="primary", icon=":material/send:"):
        errores = []
        if edad is None:
            errores.append("Indica la edad del niño o niña.")
        if len((texto or "").strip()) < 12:
            errores.append("Escribe un poco más en la carta para que podamos entender qué le gusta.")
        for e in errores:
            st.error(e)
        if not errores:
            with st.spinner("Leyendo la carta…"):
                anon = ai.anonimizar(texto.strip())
                ext = ai.extraer_carta(anon, int(edad))
            ext["edad"] = int(edad)
            nino_ref = "N-" + uuid.uuid4().hex[:8].upper()
            carta_id = db.insertar("cartas", {
                "entidad_id": ent["id"], "nino_ref": nino_ref, "edad": int(edad), "texto_anon": anon,
                "intereses": db.a_json(ext["intereses"]), "categorias": db.a_json(ext["categorias_preferidas"]),
                "rechazos": db.a_json(ext["rechazos"]), "objetos": db.a_json(ext["objetos"]), "modo": ext["modo"],
                "creado": db.ahora()})
            S["carta"] = {**ext, "id": carta_id, "nino_ref": nino_ref, "texto_anon": anon, "franja": franja,
                          "email": email.strip() or ent["email"]}
            S["prop_excluir"] = set()
            registrar("carta_enviada", "familia", str(carta_id))
            st.rerun()
    st.stop()

carta = S["carta"]

# --- 3. Lo que hemos entendido --------------------------------------------------------------
st.subheader("Lo que hemos entendido")
modo_ia(carta["modo"])
c1, c2 = st.columns([1.1, 1], gap="large")
with c1:
    html(f'<div class="fb-carta-frag">«{carta["texto_anon"]}»<small>Texto guardado, ya anonimizado</small></div>')
with c2:
    html(f'<p><strong>Edad:</strong> {carta["edad"]} años</p>'
         f'<p><strong>Le gusta:</strong> {chips(carta["intereses"]) or "<em>no hemos detectado intereses</em>"}</p>'
         f'<p><strong>Tipo de juguete:</strong> {chips([db.CATEGORIAS[c] for c in carta["categorias_preferidas"]], "fb-chip-carton") or "—"}</p>'
         + (f'<p><strong>No quiere:</strong> {chips(carta["rechazos"], "fb-chip-no")}</p>' if carta["rechazos"] else ""))
    with st.expander("¿Algo no está bien? Corrígelo"):
        with st.form("corregir"):
            nueva_edad = st.selectbox("Edad", list(range(0, 17)), index=carta["edad"])
            intereses = st.multiselect("Intereses", list(ai.INTERESES), default=carta["intereses"])
            rechazos = st.multiselect("No quiere", list(ai.INTERESES), default=carta["rechazos"])
            if st.form_submit_button("Actualizar propuesta", type="primary"):
                carta.update({"edad": int(nueva_edad), "intereses": intereses, "rechazos": rechazos,
                              "categorias_preferidas": ai.categorias_de(intereses)})
                db.actualizar("cartas", carta["id"], {"edad": int(nueva_edad), "intereses": db.a_json(intereses),
                                                       "rechazos": db.a_json(rechazos),
                                                       "categorias": db.a_json(carta["categorias_preferidas"])})
                S["prop_excluir"] = set()
                registrar("interpretacion_corregida", "familia", str(carta["id"]))
                st.rerun()

# --- 4. Propuesta ------------------------------------------------------------------------------
reservados = db.juguetes_reservados_por_nino(carta["nino_ref"])
if reservados >= db.LIMITE_POR_NINO:
    st.info(f"Este niño ya tiene {reservados} juguetes reservados en esta campaña (máximo {db.LIMITE_POR_NINO}).")
    st.stop()

st.subheader("Nuestra propuesta")
res = matching.proponer(carta, db.juguetes_publicados(), n=3, excluir=S.get("prop_excluir", set()))
if not S.get(f"_ev_prop_{carta['id']}"):
    registrar("propuesta_vista", "familia", str(carta["id"]))
    S[f"_ev_prop_{carta['id']}"] = True

for aviso in res["avisos"]:
    st.info(aviso, icon=":material/info:")

if res["sin_encaje"] or not res["propuestas"]:
    with st.container(border=True):
        st.write("¿Prefieres esperar a que llegue algo más parecido? Te avisaremos (sin guardar datos del niño).")
        if st.button("Avisadme si llega", icon=":material/notifications:"):
            for interes in (carta["intereses"] or ["cualquiera"]):
                db.insertar("avisos", {"entidad_id": ent["id"], "edad": carta["edad"], "interes": interes,
                                       "objeto": ", ".join(res["objetos_faltan"]), "estado": "pendiente",
                                       "creado": db.ahora()})
            registrar("aviso_solicitado", "familia", str(carta["id"]))
            st.success("Hecho. Avisaremos a tu entidad en cuanto llegue un juguete que encaje.")

if not res["propuestas"]:
    st.stop()


@st.dialog("Confirmar el juguete")
def confirmar(j: dict) -> None:
    html(tarjeta_juguete(j))
    modo = st.radio("¿Cómo lo recibes?", ["Punto de encuentro", "Entrega en domicilio"], horizontal=True)
    pts = db.puntos()
    punto = None
    if modo == "Punto de encuentro":
        idx = next((i for i, p in enumerate(pts) if p["id"] == j["punto_id"]), 0)
        punto = st.selectbox("Punto", pts, index=idx, format_func=lambda p: f"{p['barrio']} · {p['horario']}")
    else:
        st.caption("GUBI coordinará la dirección con tu entidad: no la guardamos en esta web.")
        punto = st.selectbox("Barrio", pts, format_func=lambda p: p["barrio"])
    if st.button("Confirmar entrega", type="primary", icon=":material/check:", width="stretch"):
        if db.juguetes_reservados_por_nino(carta["nino_ref"]) >= db.LIMITE_POR_NINO:
            st.error(f"Ya has alcanzado el máximo de {db.LIMITE_POR_NINO} juguetes por niño en esta campaña.")
            return
        try:
            r = tracking.crear_pedido(j["id"], "familia", entidad_id=ent["id"], carta_id=carta["id"],
                                      nino_ref=carta["nino_ref"], familia_ref=S["familia_ref"], edad=carta["edad"],
                                      modo_entrega="domicilio" if modo != "Punto de encuentro" else "punto",
                                      punto_id=punto["id"], email=carta["email"])
        except tracking.TransicionInvalida as e:
            st.error(str(e))
            return
        registrar("pedido_confirmado", "familia", r["codigo"])
        st.cache_data.clear()
        entrega = (f"Lo recogerás en el punto de {punto['barrio']} ({punto['horario']})." if modo == "Punto de encuentro"
                   else "GUBI lo llevará a casa en la franja elegida.")
        S["pedido_ok"] = {"codigo": r["codigo"], "juguete": j["nombre"], "entrega": entrega}
        st.rerun()


with st.container(key="rejilla_propuesta"):
    cols = st.columns(3)
    for col, p in zip(cols, res["propuestas"]):
        j = p["juguete"]
        with col:
            extra = (f'<p>{estrellas(p["estrellas"])}</p><p style="color:var(--tinta)"><strong>Por qué encaja:</strong> '
                     f'{p["explicacion"]}</p>')
            html(tarjeta_juguete(j, extra))
            if st.button("Elegir este juguete", key=f"elegir_{j['id']}", type="primary", width="stretch"):
                registrar("juguete_elegido", "familia", str(j["id"]))
                confirmar(j)

if st.button("Ver otras opciones", type="secondary", icon=":material/refresh:"):
    if res["total_candidatos"] <= len(res["propuestas"]):
        S["prop_excluir"] = set()
        st.toast("No hay más opciones que encajen: volvemos a las primeras.")
    else:
        S["prop_excluir"] = S.get("prop_excluir", set()) | {p["juguete"]["id"] for p in res["propuestas"]}
    st.rerun()
