"""Catálogo estilo Vinted: filtros, rejilla y reserva con código de entidad."""
import uuid

import streamlit as st

from core import ai, db, tracking
from core.components import chips, html, imagen_juguete, tarjeta_juguete, texto_edad, vacio
from core.events import registrar

S = st.session_state
S.setdefault("familia_ref", "F-" + uuid.uuid4().hex[:8].upper())
if not S.get("_ev_cat"):
    registrar("cta_ver_catalogo", "familia")
    S["_ev_cat"] = True


@st.cache_data(ttl=30)
def stock() -> list[dict]:
    return db.juguetes_publicados()


html('<p class="fb-antetitulo">Pedir juguetes</p><h1>Catálogo</h1>'
     '<p>Juguetes revisados por GUBI y disponibles ahora. Si prefieres que te propongamos los que mejor encajan, '
     'escribe la <a href="/carta" target="_self">carta a los Reyes</a>.</p>')

juguetes = stock()
with st.container(border=True):
    c1, c2, c3, c4 = st.columns([1.6, 1, 1, 1])
    busca = c1.text_input("Buscar", placeholder="Dinosaurio, puzle, balón…")
    franja = c2.selectbox("Edad", ["Todas"] + list(db.FRANJAS), format_func=lambda f: f if f == "Todas" else f"{f} años")
    categoria = c3.selectbox("Categoría", ["Todas"] + list(db.CATEGORIAS),
                             format_func=lambda c: c if c == "Todas" else db.CATEGORIAS[c])
    punto = c4.selectbox("Punto de recogida", ["Todos"] + [p["barrio"] for p in db.puntos()])
    estado = st.pills("Estado", db.ESTADOS_FISICOS, selection_mode="multi")


def pasa(j: dict) -> bool:
    if busca:
        t = ai.normalizar(busca)
        if t not in ai.normalizar(f"{j['nombre']} {j['descripcion']} {' '.join(j['intereses'])}"):
            return False
    if franja != "Todas":
        a, b = db.FRANJAS[franja]
        if j["edad_max"] < a or j["edad_min"] > b:
            return False
    if categoria != "Todas" and j["categoria"] != categoria:
        return False
    if punto != "Todos" and j.get("barrio") != punto:
        return False
    return not estado or j["estado_fisico"] in estado


filtrados = [j for j in juguetes if pasa(j)]
st.caption(f"{len(filtrados)} juguetes disponibles")


@st.dialog("Detalle del juguete", width="large")
def detalle(j: dict) -> None:
    c1, c2 = st.columns([1, 1.2], gap="large")
    with c1:
        fotos = [f for f in j["fotos"] if (db.RAIZ / f).exists()]
        if fotos:
            st.image([str(db.RAIZ / f) for f in fotos], width=220)
        else:
            src, alt = imagen_juguete(j)
            html(f'<img src="{src}" alt="{alt}" style="width:100%;border-radius:12px">')
    with c2:
        st.subheader(j["nombre"])
        html(chips([texto_edad(j["edad_min"], j["edad_max"]), db.CATEGORIAS[j["categoria"]], j["estado_fisico"]]))
        st.write(j["descripcion"])
        if j["restricciones"]:
            st.caption("Cumple: " + ", ".join(db.RESTRICCIONES[r].lower() for r in j["restricciones"]))
        st.caption(f"📍 {j['punto_nombre']}")
    st.divider()
    ent = S.get("entidad")
    if not ent:
        codigo = st.text_input("Código de tu entidad", placeholder="REYES-…",
                               help="Para reservar necesitas el código que te da tu entidad derivadora.")
    edad = st.selectbox("Edad del niño o niña", list(range(j["edad_min"], min(j["edad_max"], 16) + 1)),
                        format_func=lambda e: f"{e} años")
    modo = st.radio("Entrega", ["Punto de encuentro", "Entrega en domicilio"], horizontal=True)
    if st.button("Reservar", type="primary", icon=":material/bookmark_added:", width="stretch"):
        if not ent:
            ent = db.entidad_por_codigo(codigo)
            if not ent:
                st.error("Indica un código de entidad válido para reservar.")
                return
            S["entidad"] = ent
        S.setdefault("nino_catalogo", "N-" + uuid.uuid4().hex[:8].upper())
        nino = S.get("carta", {}).get("nino_ref") or S["nino_catalogo"]
        if db.juguetes_reservados_por_nino(nino) >= db.LIMITE_POR_NINO:
            st.error(f"Ya hay {db.LIMITE_POR_NINO} juguetes reservados para este niño en la campaña (es el máximo).")
            return
        try:
            r = tracking.crear_pedido(j["id"], "familia", entidad_id=ent["id"], nino_ref=nino,
                                      familia_ref=S["familia_ref"], edad=int(edad),
                                      modo_entrega="punto" if modo == "Punto de encuentro" else "domicilio",
                                      punto_id=j["punto_id"], email=ent["email"])
        except tracking.TransicionInvalida as e:
            st.error(str(e))
            return
        registrar("pedido_confirmado", "familia", r["codigo"])
        stock.clear()
        S["reserva_ok"] = r["codigo"]
        st.rerun()


if S.get("reserva_ok"):
    st.success(f"Reserva hecha. Tu código de seguimiento es **{S['reserva_ok']}**.", icon=":material/check_circle:")
    if st.button("Ver el seguimiento", icon=":material/local_shipping:"):
        st.switch_page("paginas/seguimiento.py", query_params={"codigo": S.pop("reserva_ok")})

if not filtrados:
    vacio("No hay juguetes con esos filtros.", "puzle", "Prueba a quitar algún filtro o escribe la carta a los Reyes "
          "para que te avisemos cuando llegue algo que encaje.")
    st.stop()

POR_PAGINA = 12
paginas = (len(filtrados) - 1) // POR_PAGINA + 1
pagina = st.session_state.get("cat_pagina", 1)
pagina = min(pagina, paginas)
visibles = filtrados[(pagina - 1) * POR_PAGINA: pagina * POR_PAGINA]

with st.container(key="rejilla_catalogo"):
    for fila in range(0, len(visibles), 4):
        cols = st.columns(4)
        for col, j in zip(cols, visibles[fila:fila + 4]):
            with col:
                html(tarjeta_juguete(j))
                if st.button("Ver detalle", key=f"det_{j['id']}", width="stretch"):
                    detalle(j)

if paginas > 1:
    st.write("")
    c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="center")
    if c1.button("Anterior", icon=":material/arrow_back:", disabled=pagina == 1, width="stretch"):
        S["cat_pagina"] = pagina - 1
        st.rerun()
    c2.markdown(f"<p style='text-align:center'>Página {pagina} de {paginas}</p>", unsafe_allow_html=True)
    if c3.button("Siguiente", icon=":material/arrow_forward:", disabled=pagina == paginas, width="stretch"):
        S["cat_pagina"] = pagina + 1
        st.rerun()
