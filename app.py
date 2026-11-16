"""La Fábrica de Baltasares · navegación, tema, cabecera y pie."""
from __future__ import annotations

import pandas  # noqa: F401 - importarlo antes que plotly evita una carrera de imports entre sesiones simultáneas
import streamlit as st

from core import db, theme, tracking
from core.components import html

st.set_page_config(
    page_title="La Fábrica de Baltasares",
    page_icon="assets/icono.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def _preparar_base() -> bool:
    db.inicializar()
    theme.registrar_plantilla()
    return True


@st.cache_data(ttl=300, show_spinner=False)
def _caducar_matches() -> int:
    """Cada 5 minutos como mucho: anula los matches en los que el donante no eligió en 3 días."""
    return tracking.caducar_matches()


_preparar_base()
theme.registrar_plantilla()
_caducar_matches()

# Origen de la visita (?src=...) guardado para toda la sesión
src = st.query_params.get("src")
if src and st.session_state.get("src") != src:
    st.session_state["src"] = src[:60]
st.session_state.setdefault("src", "directo")

html(theme.css_global())
st.logo("assets/logo.svg", size="large", icon_image="assets/icono.svg", link=None)

P = {
    "inicio": st.Page("paginas/inicio.py", title="Inicio", icon=":material/home:", default=True),
    "como": st.Page("paginas/como_funciona.py", title="Cómo funciona", icon=":material/route:"),
    "donar": st.Page("paginas/donar.py", title="Donar", icon=":material/volunteer_activism:"),
    "carta": st.Page("paginas/carta.py", title="Carta a los Reyes", icon=":material/edit_note:"),
    "catalogo": st.Page("paginas/catalogo.py", title="Catálogo", icon=":material/toys:"),
    "orgs": st.Page("paginas/organizaciones.py", title="Organizaciones", icon=":material/diversity_3:"),
    "empresas": st.Page("paginas/empresas.py", title="Empresas", icon=":material/handshake:"),
    "impacto": st.Page("paginas/impacto.py", title="Impacto", icon=":material/insights:"),
    "seguimiento": st.Page("paginas/seguimiento.py", title="Seguimiento", icon=":material/local_shipping:"),
    "panel": st.Page("paginas/panel_interno.py", title="Panel interno", icon=":material/lock:"),
}

nav = st.navigation(
    {
        "": [P["inicio"], P["como"], P["donar"], P["seguimiento"]],
        "Pedir": [P["carta"], P["catalogo"]],
        "Colaborar": [P["orgs"], P["empresas"], P["impacto"]],
        "Equipo": [P["panel"]],
    },
    position="top",
)
nav.run()

# --- Pie -------------------------------------------------------------------
html(f"""
<footer class="fb-pie" role="contentinfo">
  <div class="fb-pie-cols">
    <div>
      <img src="{theme.svg_data_uri('logo_claro.svg')}" alt="La Fábrica de Baltasares" style="height:56px;margin-bottom:12px">
      <p>Juguetes con segunda vida para que ningún niño se quede sin su carta respondida.</p>
      <p><strong style="color:#F6DFA8">Logística: GUBI</strong> · recogida, revisión y entrega.</p>
    </div>
    <div>
      <h4>La web</h4>
      <p><a href="/como_funciona" target="_self">Cómo funciona</a><a href="/donar" target="_self">Donar</a></p>
      <p><a href="/carta" target="_self">Carta a los Reyes</a><a href="/catalogo" target="_self">Catálogo</a></p>
      <p><a href="/organizaciones" target="_self">Organizaciones</a><a href="/empresas" target="_self">Empresas</a></p>
      <p><a href="/impacto" target="_self">Impacto</a><a href="/seguimiento" target="_self">Seguimiento</a></p>
    </div>
    <div>
      <h4>Privacidad</h4>
      <p>No pedimos documentación ni datos personales de menores. Las cartas se anonimizan antes de guardarse
      y las cifras de impacto son siempre agregadas.</p>
    </div>
  </div>
  <div class="fb-pie-legal">Prototipo académico · Mondragon Unibertsitatea · Grado en Business Data Analytics ·
  Los datos de esta web son de demostración.</div>
</footer>
""")
