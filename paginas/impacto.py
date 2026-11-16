"""Dashboard de impacto: KPIs, gráficos, mapa, galería y necesidades pendientes (refresco automático)."""
import time

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core import db, metrics, report, theme
from core.components import euros, etiqueta_demo, html, kpi, numero, seccion, tarjeta_juguete
from core.events import registrar

S = st.session_state
theme.registrar_plantilla()
CFG = {"displayModeBar": False}

# --- Campaña: pública (selector) o privada (?campana=CODIGO) ----------------------------
privada = db.campana_por_codigo(st.query_params.get("campana", "")) if st.query_params.get("campana") else None
camps = db.campanas()

with st.container(key="oscuro_impacto"):
    if privada:
        html(f'<p class="fb-antetitulo">Dashboard privado · {privada["codigo"]}</p><h1>{privada["nombre"]}</h1>'
             f'<p>{privada["empresa"]} · {privada["zona"]} · del {privada["fecha_inicio"]} al {privada["fecha_fin"]}</p>')
    else:
        html('<p class="fb-antetitulo">Impacto</p><h1>Cada aportación, convertida en entregas trazables</h1>'
             '<p>Cifras calculadas en directo desde la base de datos de la plataforma. Todas agregadas, sin datos personales.</p>')

c1, c2, c3 = st.columns([1.4, 1.2, 1], vertical_alignment="bottom")
if privada:
    campana = privada
    c1.markdown(f"Vista filtrada por vuestra campaña · {etiqueta_demo() if privada['codigo'] in ('LANTEGI-2026', 'TXOKOA-2026') else ''}",
                unsafe_allow_html=True)
    if c3.button("Salir de la vista privada", type="secondary"):
        st.query_params.clear()
        st.rerun()
else:
    campana = c1.selectbox("Campaña", [None] + camps,
                           format_func=lambda c: "Todas las campañas" if c is None else c["nombre"])
    c3.markdown(etiqueta_demo(), unsafe_allow_html=True)
cid = campana["id"] if campana else None


@st.cache_data(ttl=60, show_spinner="Generando el informe…")
def pdf(campana_id):
    return report.generar(campana_id)


with c2:
    st.download_button("Descargar informe de impacto" if campana else "Descargar informe global", data=pdf(cid),
                       file_name=f"informe_impacto_{campana['codigo'] if campana else 'global'}.pdf".lower(),
                       mime="application/pdf", icon=":material/picture_as_pdf:", width="stretch",
                       on_click=registrar, args=("informe_descargado", "empresa_financiadora",
                                                 campana["codigo"] if campana else "global"))


@st.fragment(run_every="1s")
def reloj() -> None:
    hace = int(time.time() - S.get("impacto_ts", time.time()))
    st.caption(f"Actualizado hace {hace} s · se actualiza solo cada 10 s")


reloj()


def barras(df, x, y, color, titulo, horizontal=False):
    if horizontal:
        fig = px.bar(df, x=y, y=x, orientation="h", title=titulo, color_discrete_sequence=[color])
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_xaxes(title=None, showgrid=True, gridcolor="rgba(233,220,198,.55)")
    else:
        fig = px.bar(df, x=x, y=y, title=titulo, color_discrete_sequence=[color])
        fig.update_xaxes(title=None)
        fig.update_yaxes(title=None)
    fig.update_traces(hovertemplate="%{x}: %{y}<extra></extra>" if not horizontal else "%{y}: %{x}<extra></extra>")
    fig.update_layout(height=300)
    return fig


@st.fragment(run_every="10s")
def panel() -> None:
    S["impacto_ts"] = time.time()
    k = metrics.kpis(cid)

    if campana:
        av = metrics.avance_campana(campana)
        st.progress(min(av["porcentaje"] / 100, 1.0),
                    text=f"Objetivo de la campaña: {av['entregados']} de {av['objetivo']} juguetes entregados "
                         f"({str(av['porcentaje']).replace('.', ',')} %) · aportación comprometida {euros(av['aportacion'], 0)}")

    html('<div class="fb-franja-kpi" aria-live="polite">'
         + kpi(numero(k["donados"]), "Juguetes asignados" if campana else "Juguetes donados")
         + kpi(numero(k["entregados"]), "Juguetes entregados")
         + kpi(numero(k["ninos"]), "Niños alcanzados")
         + kpi(numero(k["familias"]), "Familias atendidas") + "</div>")
    st.write("")
    html('<div class="fb-franja-kpi" style="--x:1">'
         + kpi(numero(k["entidades"]), "Entidades atendidas")
         + kpi(euros(k["coste_medio"]), "Coste medio por juguete entregado")
         + kpi(f"{k['dias_medios']:.1f} días".replace(".", ","), "De la donación a la entrega")
         + kpi(numero(k["rescatados"]), "Rescatados del desecho", f"≈ {str(k['kg_rescatados']).replace('.', ',')} kg")
         + "</div>")

    seccion("Entregas", ante="Resultados")
    c1, c2 = st.columns(2, gap="large")
    sem = metrics.entregas_por_semana(cid)
    if not sem.empty:
        sem["semana"] = sem["semana"].dt.strftime("%d/%m")
        c1.plotly_chart(barras(sem, "semana", "entregas", theme.NOCHE, "Entregas por semana"), config=CFG, key="g_sem")
    fr = metrics.distribucion("franja", cid)
    if not fr.empty:
        fr["orden"] = fr["franja"].map({f: i for i, f in enumerate(db.FRANJAS)})
        fr = fr.sort_values("orden")
        fr["franja"] = fr["franja"] + " años"
        c2.plotly_chart(barras(fr, "franja", "entregas", theme.ORO, "Por franja de edad"), config=CFG, key="g_fr")
    c1, c2 = st.columns(2, gap="large")
    cat = metrics.distribucion("categoria", cid)
    if not cat.empty:
        cat["categoria"] = cat["categoria"].map(db.CATEGORIAS)
        c1.plotly_chart(barras(cat, "categoria", "entregas", theme.GRANADA, "Por categoría", horizontal=True),
                        config=CFG, key="g_cat")
    br = metrics.distribucion("barrio", cid)
    if not br.empty:
        c2.plotly_chart(barras(br, "barrio", "entregas", theme.PINO, "Por barrio", horizontal=True), config=CFG, key="g_br")

    seccion("Del armario al niño", ante="Embudo y aportaciones")
    c1, c2 = st.columns([1.2, 1], gap="large")
    emb = metrics.embudo_donacion()
    fig = go.Figure(go.Funnel(y=emb["etapa"], x=emb["donaciones"], textinfo="value+percent initial",
                              marker=dict(color=[theme.NOCHE, "#2C3E66", "#46598A", theme.ORO, "#D9A04A", theme.PINO]),
                              connector=dict(line=dict(color=theme.CARTON))))
    fig.update_layout(title="Embudo de donación (todo el proyecto)", height=360)
    c1.plotly_chart(fig, config=CFG, key="g_emb")
    dest = metrics.destino_aportaciones(cid)
    if not dest.empty:
        fig = go.Figure(go.Pie(labels=dest["destino"], values=dest["importe"], hole=.58, sort=False,
                               marker=dict(colors=[theme.NOCHE, theme.ORO, theme.PINO, theme.GRANADA]),
                               texttemplate="%{percent:.0%}", hovertemplate="%{label}: %{value:.2f} €<extra></extra>"))
        fig.update_layout(title="Destino de las aportaciones", height=380, margin=dict(l=8, r=8, t=48, b=48),
                          legend=dict(orientation="h", yanchor="top", y=-0.04, x=0.5, xanchor="center"),
                          annotations=[dict(text=f"<b>{euros(dest['importe'].sum(), 0)}</b><br>ejecutados", showarrow=False,
                                            font=dict(size=15, color=theme.NOCHE))])
        c2.plotly_chart(fig, config=CFG, key="g_dest")

    seccion("Puntos de encuentro", "Tamaño del círculo: donaciones y pedidos gestionados en cada punto.", "Mapa")
    pts = metrics.volumen_puntos()
    mx = max(pts["volumen"].max(), 1)
    fig = go.Figure(go.Scattermap(
        lat=pts["lat"], lon=pts["lon"], mode="markers+text", text=pts["barrio"], textposition="top right",
        marker=dict(size=14 + 36 * pts["volumen"] / mx, color=theme.GRANADA, opacity=.8),
        customdata=pts[["nombre", "donaciones", "pedidos"]],
        hovertemplate="<b>%{customdata[0]}</b><br>Donaciones: %{customdata[1]}<br>Pedidos: %{customdata[2]}<extra></extra>"))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=43.262, lon=-2.93), zoom=12.2), height=380,
                      margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, config={**CFG, "scrollZoom": False}, key="g_mapa")


panel()

# --- Galería e historias (fuera del refresco para no recargar imágenes) -------------------
seccion("Galería de impacto", "Juguetes entregados y fragmentos de cartas. Nunca mostramos caras de niños.", "Historias")
gal = metrics.galeria(4, cid)
if gal:
    with st.container(key="rejilla_galeria"):
        cols = st.columns(4)
        for col, g in zip(cols, gal):
            j = db.juguete(int(g["juguete_id"]))
            with col:
                html(tarjeta_juguete(j, f'<p class="fb-meta">Entregado a {"una familia" if g["destino"] == "familia" else "una entidad"}'
                                        f' · {g["franja"]} años</p>'))
frags = metrics.fragmentos_cartas(3)
html('<div class="fb-cartas" style="margin-top:24px">' + "".join(
    f'<blockquote class="fb-carta-frag fb-gira-{i}">«{f["texto_anon"]}»<small>Niño de {f["edad"]} años</small></blockquote>'
    for i, f in enumerate(frags, 1)) + "</div>")

seccion("Necesidades pendientes", "Dónde hace más falta ampliar la colaboración.", "Demanda sin cubrir")
nec = metrics.necesidades_pendientes()
c1, c2 = st.columns([1.4, 1], gap="large")
with c1:
    st.dataframe(nec.rename(columns={"franja": "Franja", "stock": "Stock disponible", "demanda_21d": "Pedidos (21 días)",
                                     "avisos": "Avisos en espera", "ninos_sin_cubrir_org": "Niños de entidades sin cubrir",
                                     "presion": "Presión"}),
                 hide_index=True, width="stretch",
                 column_config={"Presión": st.column_config.ProgressColumn("Presión (demanda ÷ stock)", min_value=0,
                                                                            max_value=max(1.0, float(nec["presion"].max())),
                                                                            format="%.2f")})
with c2:
    peor = nec.sort_values("presion", ascending=False).iloc[0]
    html(f'<div class="fb-etiqueta fb-sobrio"><p class="fb-antetitulo">Donde más falta hace</p>'
         f'<h3>{peor["franja"]} años</h3><p>Hay {peor["stock"]} juguetes disponibles para esta franja frente a '
         f'{peor["demanda_21d"]} pedidos recientes y {peor["avisos"]} avisos en espera.</p></div>')
    sin = metrics.intereses_sin_stock()
    if sin:
        st.caption("Intereses que las familias han pedido y no teníamos: " +
                   ", ".join(f"{s['interes']} ({s['n']})" for s in sin[:6]))
