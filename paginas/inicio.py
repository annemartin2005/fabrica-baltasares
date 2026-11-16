"""Inicio: hero, contador en vivo, cuatro puertas, pasos, cartas y confianza."""
import streamlit as st

from core import metrics, theme
from core.components import boton_cta, html, ilustracion, kpi, numero, seccion

# --- Hero ------------------------------------------------------------------
with st.container(key="hero"):
    html(theme.cielo_estrellas(22))
    izq, der = st.columns([1.25, 1], vertical_alignment="center", gap="large")
    with izq:
        html('<p class="fb-antetitulo">Juguetes con segunda vida</p>'
             '<h1>Que ningún niño se quede sin su carta respondida</h1>'
             '<p style="font-size:19px;max-width:520px">Recogemos juguetes que ya no se usan o que no se pueden '
             'vender y los llevamos, revisados, a los niños que más los esperan.</p>')
        b1, b2, _ = st.columns([1, 1, 0.2])
        with b1:
            boton_cta("Quiero donar", "paginas/donar.py", "cta_quiero_donar", "donante", key="hero_donar",
                      icono=":material/redeem:", ancho=True)
        with b2:
            boton_cta("Necesito juguetes", "paginas/carta.py", "cta_necesito_juguetes", "familia", key="hero_pedir",
                      tipo="secondary", ancho=True)
    with der:
        html("""
<svg viewBox="0 0 360 300" role="img" aria-label="Caja de regalo abierta con juguetes asomando y una estrella encima" style="width:100%;max-width:420px;display:block;margin:auto">
  <path d="M180 8 L188 34 L214 42 L188 50 L180 76 L172 50 L146 42 L172 34 Z" fill="#E8B04B"/>
  <circle cx="96" cy="118" r="26" fill="#C8553D" stroke="#F6DFA8" stroke-width="4"/>
  <circle cx="88" cy="112" r="4" fill="#121D35"/><circle cx="104" cy="112" r="4" fill="#121D35"/>
  <circle cx="74" cy="96" r="10" fill="#C8553D" stroke="#F6DFA8" stroke-width="4"/><circle cx="118" cy="96" r="10" fill="#C8553D" stroke="#F6DFA8" stroke-width="4"/>
  <rect x="150" y="92" width="44" height="44" rx="6" fill="#2F6B57" stroke="#F6DFA8" stroke-width="4"/>
  <rect x="198" y="106" width="34" height="30" rx="5" fill="#E8B04B" stroke="#F6DFA8" stroke-width="4"/>
  <path d="M244 136 L262 92 L282 136 Z" fill="#7C8BB0" stroke="#F6DFA8" stroke-width="4" stroke-linejoin="round"/>
  <rect x="58" y="136" width="244" height="40" rx="10" fill="#E8B04B"/>
  <path d="M70 176 h220 v96 a12 12 0 0 1 -12 12 h-196 a12 12 0 0 1 -12 -12z" fill="#1B2A4A" stroke="#E8B04B" stroke-width="5"/>
  <rect x="164" y="136" width="32" height="148" fill="#C8553D"/>
  <path d="M130 136 q-40 -40 0 -46 q30 0 50 46 q20 -46 50 -46 q40 6 0 46" fill="none" stroke="#C8553D" stroke-width="8" stroke-linecap="round"/>
</svg>""")

# --- Contador en vivo --------------------------------------------------------
@st.fragment(run_every="15s")
def contador() -> None:
    k = metrics.kpis()
    html('<div class="fb-franja-kpi" aria-live="polite" style="margin-top:24px">'
         + kpi(numero(k["entregados"]), "Juguetes entregados")
         + kpi(numero(k["ninos"]), "Niños alcanzados")
         + kpi(numero(k["entidades"]), "Entidades atendidas")
         + kpi(numero(k["rescatados"]), "Juguetes rescatados del desecho")
         + "</div>")


contador()
c1, c2 = st.columns([3, 1])
with c2:
    st.page_link("paginas/impacto.py", label="Ver el impacto completo", icon=":material/arrow_forward:")
with c1:
    html('<p class="fb-modo">Cifras reales de la base de datos, actualizadas cada pocos segundos · '
         '<span class="fb-demo">Datos de demostración</span></p>')

# --- Cuatro puertas -----------------------------------------------------------
seccion("¿Qué te trae por aquí?", "Elige tu puerta: cada una te lleva a lo que necesitas.", "Cuatro puertas")
puertas = [
    ("peluche", "Donar", "Dale una segunda vida a un juguete en buen estado.", "Donar un juguete",
     "paginas/donar.py", "cta_puerta_donar", "donante"),
    ("libro", "Pedir juguetes", "Escribe la carta a los Reyes con el código de tu entidad.", "Escribir la carta",
     "paginas/carta.py", "cta_puerta_pedir", "familia"),
    ("construccion", "Soy una organización", "ONG, centros de menores, hospitales y colegios.", "Ver el servicio",
     "paginas/organizaciones.py", "cta_ver_servicio", "organizacion"),
    ("juego_mesa", "Quiero colaborar como empresa", "Aportaciones, stock fuera de catálogo o voluntariado.",
     "Ver el impacto", "paginas/empresas.py", "cta_ver_impacto", "empresa_financiadora"),
]
with st.container(key="rejilla_puertas"):
    cols = st.columns(4)
    for col, (cat, titulo, texto, boton, destino, evento, publico) in zip(cols, puertas):
        with col:
            html(f'<div class="fb-etiqueta fb-puerta"><img class="fb-ilus" src="{ilustracion(cat)}" alt="" '
                 f'aria-hidden="true"><h3>{titulo}</h3><p>{texto}</p></div>')
            boton_cta(boton, destino, evento, publico, key=f"puerta_{cat}", tipo="secondary", ancho=True)

# --- Cómo funciona en 4 pasos --------------------------------------------------
seccion("Cómo funciona", "Del armario de una casa a las manos de un niño, con cada paso trazado.", "En cuatro pasos")
pasos = [("Donas", "Subes tu juguete con fotos. Las revisamos y lo publicamos; sigue en tu casa."),
         ("Emparejamos", "Leemos la carta a los Reyes y el niño elige el juguete que mejor encaja."),
         ("Recogemos y revisamos", "GUBI lo recoge en tu casa o en un punto y lo revisa en su local."),
         ("Entregamos", "En casa o en el punto del barrio. Y tú lo sigues con tu código.")]
html('<div class="fb-pasos">' + "".join(
    f'<div class="fb-paso"><div class="fb-paso-num">{i}</div><h4>{t}</h4><p>{d}</p></div>'
    for i, (t, d) in enumerate(pasos, 1)) + "</div>")
st.write("")
st.page_link("paginas/como_funciona.py", label="Ver cómo funciona en detalle", icon=":material/arrow_forward:")

# --- Fragmentos de cartas -------------------------------------------------------
seccion("Lo que piden las cartas", "Fragmentos reales del prototipo, anonimizados: sin nombres ni direcciones.",
        "Voz del proyecto")
frags = metrics.fragmentos_cartas(3)
html('<div class="fb-cartas">' + "".join(
    f'<blockquote class="fb-carta-frag fb-gira-{i}">«{f["texto_anon"]}»<small>Carta de un niño de {f["edad"]} años</small></blockquote>'
    for i, f in enumerate(frags, 1)) + "</div>")

# --- Franja de confianza ---------------------------------------------------------
seccion("Puedes confiar", ante="Seguridad, logística y privacidad")
html(f"""
<div class="fb-confianza">
  <div class="fb-etiqueta"><h3>{theme.estrella_svg(16)} Juguetes seguros</h3>
    <p>Solo aceptamos taras estéticas: caja dañada, color defectuoso o fuera de catálogo. Nunca piezas sueltas,
    pilas de botón accesibles, bordes cortantes ni juguetes rotos. Dos revisiones: las fotos antes de publicarlo y
    el juguete en mano, en el local de GUBI, antes de entregarlo.</p></div>
  <div class="fb-etiqueta"><h3>{theme.estrella_svg(16)} Logística con GUBI</h3>
    <p>Nuestro socio logístico recoge en casa del donante o en los puntos del barrio y entrega en casa o en el punto.
    Cada movimiento queda registrado y se puede seguir con un código.</p></div>
  <div class="fb-etiqueta"><h3>{theme.estrella_svg(16)} Privacidad de los menores</h3>
    <p>Las familias acceden con un código de su entidad. No pedimos documentos y las cartas se anonimizan
    antes de guardarse. Nunca mostramos caras ni datos de niños.</p></div>
</div>""")
