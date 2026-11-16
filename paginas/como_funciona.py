"""Cómo funciona: recorridos, GUBI, puntos de encuentro, criterios y preguntas frecuentes."""
import plotly.graph_objects as go
import streamlit as st

from core import db, metrics, theme, tracking
from core.components import boton_cta, html, linea_tiempo, seccion
from core.events import registrar

if not st.session_state.get("_ev_como"):
    registrar("cta_ver_como_funciona", "donante")
    st.session_state["_ev_como"] = True

html('<p class="fb-antetitulo">Cómo funciona</p><h1>Dos recorridos, un mismo taller</h1>'
     '<p style="max-width:720px">Unos donan y otros reciben. En medio, la plataforma empareja cada carta con el '
     'juguete que mejor encaja y GUBI recoge, revisa y entrega cada juguete.</p>'
     f'<p class="fb-meta">Campaña de Reyes: donaciones del {tracking.CAMPANA["donaciones_desde"]} al '
     f'{tracking.CAMPANA["donaciones_hasta"]} · entregas hasta el {tracking.CAMPANA["entregas_hasta"]}.</p>')

c1, c2 = st.columns(2, gap="large")
with c1:
    st.subheader("Si donas")
    linea_tiempo([
        {"titulo": "Subes tu juguete con fotos", "nota": "Descripción y estado. Te proponemos las etiquetas.", "estado": "hecho"},
        {"titulo": "Revisión online y publicación", "nota": "Revisamos las fotos y lo publicamos. El juguete sigue en tu casa.", "estado": "hecho"},
        {"titulo": "Un niño lo elige: te avisamos", "nota": "Por email o WhatsApp. Tienes 3 días para elegir recogida en casa (gratis) o dejarlo en un punto.", "estado": "hecho"},
        {"titulo": "GUBI lo lleva a su local y lo revisa", "nota": "Revisión física: seguridad, piezas y estado.", "estado": "hecho"},
        {"titulo": "Te avisamos cuando se entrega", "nota": "«Tu juguete ya tiene nuevo dueño».", "estado": "actual"},
    ])
    boton_cta("Subir mi juguete", "paginas/donar.py", "cta_subir_juguete", "donante", key="cf_donar")
with c2:
    st.subheader("Si recibes")
    linea_tiempo([
        {"titulo": "Tu entidad te da un código", "nota": "Servicios sociales, una ONG o el colegio.", "estado": "hecho"},
        {"titulo": "Escribes la carta a los Reyes", "nota": "Sin nombres ni direcciones: solo edad y lo que le gusta.", "estado": "hecho"},
        {"titulo": "Te proponemos tres juguetes", "nota": "Con una explicación de por qué encajan.", "estado": "hecho"},
        {"titulo": "Eliges y confirmas", "nota": "El juguete queda reservado para ti.", "estado": "hecho"},
        {"titulo": "GUBI lo recoge y lo revisa", "nota": "Si no pasa la revisión física, te asignamos otro parecido y te avisamos por email.", "estado": "hecho"},
        {"titulo": "Lo recibes", "nota": "En casa o en el punto de encuentro.", "estado": "actual"},
    ])
    boton_cta("Escribir la carta", "paginas/carta.py", "cta_puerta_pedir", "familia", key="cf_carta")

seccion("El papel de GUBI", ante="Socio logístico")
st.markdown("GUBI es el socio logístico del proyecto. Cuando un niño elige un juguete, GUBI lo **recoge** en casa "
            "del donante o en el punto de recogida donde lo ha dejado y lo lleva a **su local**, donde lo **revisa "
            "físicamente**. Si supera la revisión, lo **entrega** en casa o en el punto de encuentro. Cada cambio de "
            "estado queda registrado y se puede consultar en *Seguimiento*.")
html(f'<div class="fb-etiqueta fb-sobrio"><h3>📦 {tracking.ALMACEN["nombre"]}</h3><p>{tracking.ALMACEN["direccion"]} · '
     f'{tracking.ALMACEN["horario"]}</p><p class="fb-meta">Solo se usa durante la campaña de Reyes: guarda los '
     'juguetes que ya tienen niño asignado mientras pasan la revisión física y se preparan para la entrega.</p></div>')

seccion("Dos revisiones antes de cada entrega", ante="Seguridad")
c1, c2 = st.columns(2, gap="large")
with c1:
    html('<div class="fb-etiqueta"><h3>1 · Revisión online</h3><p>Antes de publicar un juguete revisamos sus fotos y '
         'su descripción: que se vea bien, que esté completo y que cumpla los criterios de aceptación. Solo entonces '
         'aparece en el catálogo.</p></div>')
with c2:
    html('<div class="fb-etiqueta"><h3>2 · Revisión física</h3><p>Cuando un niño lo elige, GUBI lo lleva a su local y lo '
         'revisa en mano: seguridad, piezas y estado. Si no la supera, el niño no se queda sin regalo: le asignamos '
         'otro juguete parecido y avisamos a su familia por email.</p></div>')

seccion("Puntos de encuentro", "Cuatro puntos en barrios de Bilbao para dejar o recoger juguetes.", "Mapa")
pts = metrics.volumen_puntos()
fig = go.Figure(go.Scattermap(
    lat=pts["lat"], lon=pts["lon"], mode="markers+text", text=pts["barrio"], textposition="top right",
    marker=dict(size=18, color=theme.GRANADA), customdata=pts[["nombre", "horario"]],
    hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>"))
fig.update_layout(map=dict(style="carto-positron", center=dict(lat=43.262, lon=-2.93), zoom=12.2),
                  height=380, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
st.plotly_chart(fig, config={"displayModeBar": False, "scrollZoom": False})
cols = st.columns(4)
for col, p in zip(cols, db.puntos()):
    with col:
        html(f'<div class="fb-etiqueta"><h4>{p["barrio"]}</h4><p>{p["nombre"]}</p><p class="fb-meta">{p["horario"]}</p></div>')

seccion("Qué juguetes aceptamos", "Solo taras estéticas: la seguridad no se negocia.", "Criterios de aceptación")
c1, c2 = st.columns(2, gap="large")
with c1:
    html('<div class="fb-etiqueta"><h3>✓ Sí aceptamos</h3><ul class="fb-lista-si">'
         '<li>Juguetes nuevos, con o sin caja</li><li>Cajas dañadas o abiertas con el contenido completo</li>'
         '<li>Colores o acabados defectuosos que no afectan al uso</li><li>Stock fuera de catálogo o excedente</li>'
         '<li>Juegos de mesa y puzles completos</li></ul></div>')
with c2:
    html('<div class="fb-etiqueta"><h3>✕ No aceptamos</h3><ul>'
         '<li>Piezas sueltas o juegos incompletos</li><li>Pilas de botón accesibles</li>'
         '<li>Bordes cortantes, astillas o piezas rotas</li><li>Peluches manchados o con relleno a la vista</li>'
         '<li>Aparatos electrónicos (consolas, tablets, móviles)</li></ul></div>')

seccion("Preguntas frecuentes", ante="FAQ")
faqs = [
    ("¿Cuánto cuesta?", "Nada. Nadie compra ni vende: la logística se financia con aportaciones de empresas colaboradoras."),
    ("¿Cómo consigo un código de entidad?", "Pídelo a tus servicios sociales, a una ONG o al colegio. Ellos nos derivan a las "
     "familias y así no tenemos que pedirte ningún documento."),
    ("¿Cuántos juguetes puede recibir cada niño?", "Hasta dos por campaña, para que lleguen a más niños."),
    ("¿Tengo que llevar el juguete a algún sitio al donarlo?", "No. Se queda en tu casa hasta que un niño lo elige. "
     "Entonces te avisamos por email o WhatsApp y tienes 3 días para elegir si GUBI lo recoge en tu casa (gratis) "
     "o si lo dejas en un punto de recogida. Si no respondes, el niño recibe otro juguete parecido."),
    ("¿Qué pasa si mi juguete no pasa la revisión?", "Te lo decimos con el motivo. Si es la revisión online, no lo "
     "publicamos; si es la física, el niño que lo había elegido recibe otro juguete parecido."),
    ("¿Cuándo se puede donar?", f"Durante la campaña de Reyes: del {tracking.CAMPANA['donaciones_desde']} al "
     f"{tracking.CAMPANA['donaciones_hasta']}. Las entregas se hacen hasta el {tracking.CAMPANA['entregas_hasta']}."),
    ("¿Qué datos guardáis de los niños?", "Solo la edad y los intereses extraídos de la carta, ya anonimizada. Nunca "
     "nombres, direcciones ni fotos."),
    ("Soy una empresa, ¿cómo puedo colaborar?", "Con una aportación económica, donando stock fuera de catálogo o con "
     "voluntariado. Recibiréis un dashboard y un informe de impacto social."),
]
for q, a in faqs:
    with st.expander(q):
        st.write(a)
