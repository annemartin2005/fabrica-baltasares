"""Identidad visual: paleta, plantilla Plotly, CSS global y SVG decorativos."""
from __future__ import annotations

import base64
import random
from functools import lru_cache
from pathlib import Path

import pandas  # noqa: F401 - plotly lo importa de forma perezosa; así queda cargado antes
import plotly.graph_objects as go
import plotly.io as pio

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"

# --- Paleta de marca -------------------------------------------------------
NOCHE = "#1B2A4A"
NOCHE_PROFUNDA = "#121D35"
ORO = "#E8B04B"
ORO_SUAVE = "#F6DFA8"
GRANADA = "#C8553D"
PINO = "#2F6B57"
CREMA = "#FBF6EE"
PAPEL = "#FFFFFF"
CARTON = "#E9DCC6"
TINTA = "#2B2B33"
TINTA_SUAVE = "#5E6170"

# Secuencia para gráficos (orden pensado para contraste entre series contiguas)
SECUENCIA = [NOCHE, ORO, GRANADA, PINO, "#7C8BB0", "#D9A38A", "#8FB3A5", "#B9A27A"]

FUENTE_TITULOS = "Fraunces, Georgia, 'Times New Roman', serif"
FUENTE_TEXTO = "Nunito, 'Segoe UI', system-ui, -apple-system, Arial, sans-serif"


# --- Plantilla Plotly ------------------------------------------------------
def registrar_plantilla() -> None:
    """Registra la plantilla 'baltasares' y la deja por defecto."""
    if "baltasares" in pio.templates:
        pio.templates.default = "baltasares"
        return
    plantilla = go.layout.Template(
        layout=go.Layout(
            font=dict(family=FUENTE_TEXTO, size=14, color=TINTA),
            title=dict(font=dict(family=FUENTE_TITULOS, size=18, color=NOCHE), x=0, xanchor="left"),
            colorway=SECUENCIA,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=8, r=8, t=48, b=8),
            xaxis=dict(showgrid=False, linecolor=CARTON, tickcolor=CARTON, zeroline=False,
                       title=dict(font=dict(color=TINTA_SUAVE, size=13))),
            yaxis=dict(showgrid=True, gridcolor="rgba(233,220,198,.55)", zeroline=False,
                       linecolor=CARTON, title=dict(font=dict(color=TINTA_SUAVE, size=13))),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=13)),
            hoverlabel=dict(bgcolor=PAPEL, bordercolor=CARTON, font=dict(family=FUENTE_TEXTO, color=TINTA)),
            bargap=0.35,
        )
    )
    pio.templates["baltasares"] = plantilla
    pio.templates.default = "baltasares"


# --- Recursos --------------------------------------------------------------
@lru_cache(maxsize=64)
def svg_data_uri(ruta_relativa: str) -> str:
    """Devuelve un SVG de assets como data URI para usarlo en <img>."""
    ruta = ASSETS / ruta_relativa
    datos = ruta.read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(datos).decode()


def imagen_data_uri(ruta: str | Path) -> str:
    ruta = Path(ruta)
    tipo = {".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".webp": "webp"}.get(ruta.suffix.lower(), "jpeg")
    return f"data:image/{tipo};base64," + base64.b64encode(ruta.read_bytes()).decode()


def estrella_svg(tam: int = 18, color: str = ORO, clase: str = "fb-estrella") -> str:
    """Estrella de cuatro puntas decorativa (aria-hidden)."""
    return (
        f'<svg class="{clase}" width="{tam}" height="{tam}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        f'<path d="M12 0 L14.6 9.4 L24 12 L14.6 14.6 L12 24 L9.4 14.6 L0 12 L9.4 9.4 Z" fill="{color}"/></svg>'
    )


def cielo_estrellas(n: int = 22, semilla: int = 6) -> str:
    """Capa de estrellas pequeñas con opacidades y parpadeo distintos."""
    rnd = random.Random(semilla)
    piezas = []
    for _ in range(n):
        x, y = rnd.uniform(2, 98), rnd.uniform(4, 92)
        tam = rnd.choice([6, 8, 10, 12, 14])
        opac = rnd.choice([0.35, 0.5, 0.65, 0.85])
        retardo = rnd.uniform(0, 4)
        piezas.append(
            f'<span class="fb-cielo-estrella" style="left:{x:.1f}%;top:{y:.1f}%;opacity:{opac};'
            f'animation-delay:{retardo:.1f}s">{estrella_svg(tam)}</span>'
        )
    return f'<div class="fb-cielo" aria-hidden="true">{"".join(piezas)}</div>'


# --- CSS global ------------------------------------------------------------
def css_global() -> str:
    fuentes = (ASSETS / "fonts.css").read_text(encoding="utf-8")
    return f"""
<style>
{fuentes}
:root {{
  --noche:{NOCHE}; --noche-profunda:{NOCHE_PROFUNDA}; --oro:{ORO}; --oro-suave:{ORO_SUAVE};
  --granada:{GRANADA}; --pino:{PINO}; --crema:{CREMA}; --papel:{PAPEL}; --carton:{CARTON};
  --tinta:{TINTA}; --tinta-suave:{TINTA_SUAVE};
  --f-titulos:{FUENTE_TITULOS}; --f-texto:{FUENTE_TEXTO};
  --sombra:0 2px 10px rgba(27,42,74,.06);
}}

/* ---- Base ---- */
html, body, [data-testid="stApp"] {{ background: var(--crema); color: var(--tinta); }}
[data-testid="stApp"] p, [data-testid="stApp"] li, [data-testid="stApp"] label,
[data-testid="stMarkdownContainer"] {{ font-family: var(--f-texto); }}
[data-testid="stMarkdownContainer"] p {{ font-size: 17px; line-height: 1.6; }}
h1, h2, h3, h4 {{ font-family: var(--f-titulos) !important; color: var(--noche); letter-spacing: -0.01em; }}
h1 {{ font-size: clamp(32px, 4.6vw, 52px) !important; font-weight: 700 !important; line-height: 1.12 !important; }}
h2 {{ font-size: clamp(26px, 3vw, 32px) !important; font-weight: 650 !important; }}
h3 {{ font-size: 22px !important; font-weight: 650 !important; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1200px; padding: 72px 32px 0 32px; margin: 0 auto; }}
@media (max-width: 640px) {{ [data-testid="stMainBlockContainer"] {{ padding: 84px 16px 0 16px; }} }}
[data-testid="stHeader"] {{ background: var(--papel); border-bottom: 1px solid var(--carton); }}
a {{ color: var(--noche); }}

/* ---- Botones ---- */
[data-testid^="stBaseButton"] {{ border-radius: 999px !important; min-height: 46px; font-family: var(--f-texto);
  font-weight: 700 !important; padding: 0 22px !important; transition: transform .15s ease, box-shadow .15s ease; }}
[data-testid^="stBaseButton"] p {{ font-weight: 700 !important; font-size: 16px !important; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  background: var(--granada) !important; border-color: var(--granada) !important; color: #fff !important; }}
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
  background: transparent !important; border: 2px solid var(--noche) !important; color: var(--noche) !important; }}
[data-testid^="stBaseButton"]:hover {{ transform: translateY(-1px); box-shadow: 0 6px 16px rgba(27,42,74,.14); }}
[data-testid^="stBaseButton"]:focus-visible, a:focus-visible, input:focus-visible, textarea:focus-visible {{
  outline: 3px solid var(--oro) !important; outline-offset: 2px; }}
[data-testid="stPageLink"] a {{ min-height: 44px; }}

/* Botones sobre fondo oscuro (contenedores con clave fb-oscuro / hero) */
.st-key-hero [data-testid="stBaseButton-primary"], [class*="st-key-oscuro"] [data-testid="stBaseButton-primary"] {{
  background: var(--oro) !important; border-color: var(--oro) !important; color: var(--noche) !important; }}
.st-key-hero [data-testid="stBaseButton-primary"] p, [class*="st-key-oscuro"] [data-testid="stBaseButton-primary"] p {{ color: var(--noche) !important; }}
.st-key-hero [data-testid="stBaseButton-secondary"], [class*="st-key-oscuro"] [data-testid="stBaseButton-secondary"] {{
  border-color: var(--crema) !important; color: var(--crema) !important; }}
.st-key-hero [data-testid="stBaseButton-secondary"] p, [class*="st-key-oscuro"] [data-testid="stBaseButton-secondary"] p {{ color: var(--crema) !important; }}

/* ---- Hero y bloques oscuros ---- */
.st-key-hero, [class*="st-key-oscuro"] {{ position: relative; background: var(--noche-profunda); border-radius: 28px;
  padding: 48px 48px 56px 48px; overflow: hidden; }}
[class*="st-key-oscuro"] {{ background: var(--noche); padding: 40px; }}
.st-key-hero h1, .st-key-hero h2, [class*="st-key-oscuro"] h1, [class*="st-key-oscuro"] h2, [class*="st-key-oscuro"] h3 {{ color: var(--crema) !important; }}
.st-key-hero p, [class*="st-key-oscuro"] p, [class*="st-key-oscuro"] li {{ color: #E7E3DA; }}
@media (max-width: 640px) {{ .st-key-hero, [class*="st-key-oscuro"] {{ padding: 28px 20px 36px 20px; border-radius: 20px; }} }}
.fb-cielo {{ position: absolute; inset: 0; pointer-events: none; z-index: 0; }}
.st-key-hero [data-testid="stElementContainer"]:has(.fb-cielo),
.st-key-hero [data-testid="stElementContainer"]:has(.fb-cielo) * {{ position: static; }}
.st-key-hero .fb-cielo {{ position: absolute !important; }}
.st-key-hero .fb-cielo-estrella {{ position: absolute !important; }}
.st-key-hero [data-testid="stHorizontalBlock"] {{ position: relative; z-index: 1; }}
.visually-hidden {{ position:absolute !important; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }}
.fb-cielo-estrella {{ position: absolute; animation: fb-parpadeo 4s ease-in-out infinite; }}
@keyframes fb-parpadeo {{ 0%,100% {{ transform: scale(1); }} 50% {{ transform: scale(.72); opacity:.25; }} }}
@media (prefers-reduced-motion: reduce) {{
  .fb-cielo-estrella {{ animation: none !important; }}
  [data-testid^="stBaseButton"], .fb-etiqueta {{ transition: none !important; }}
}}
.fb-zigzag {{ height: 18px; margin: -2px 0 24px 0; background:
  linear-gradient(135deg, var(--noche-profunda) 25%, transparent 25%) -9px 0/18px 18px,
  linear-gradient(225deg, var(--noche-profunda) 25%, transparent 25%) -9px 0/18px 18px; }}
.fb-ola {{ display:block; width:100%; height:22px; margin: 8px 0 24px 0; }}

/* ---- Antetítulos, chips, badges ---- */
.fb-antetitulo {{ font-family: var(--f-texto); font-weight: 700; font-size: 13px; letter-spacing: .08em;
  text-transform: uppercase; font-variant: small-caps; color: var(--granada); margin: 0 0 6px 0; }}
.st-key-hero .fb-antetitulo, [class*="st-key-oscuro"] .fb-antetitulo {{ color: var(--oro); }}
.fb-chip {{ display: inline-block; background: var(--oro-suave); color: var(--noche); border-radius: 999px;
  padding: 3px 11px; font: 700 13px var(--f-texto); margin: 0 6px 6px 0; }}
.fb-chip-carton {{ background: #F2E9DA; }}
.fb-chip-no {{ background: #F3D9D2; color: #7A2C1C; }}
.fb-badge {{ display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 4px 12px;
  font: 700 13px var(--f-texto); }}
.fb-badge-pendiente {{ background: var(--carton); color: var(--noche); }}
.fb-badge-proceso {{ background: var(--oro-suave); color: var(--noche); }}
.fb-badge-completado {{ background: var(--pino); color: #fff; }}
.fb-badge-error {{ background: #F3D9D2; color: #7A2C1C; }}
.fb-demo {{ display:inline-block; border:1px dashed var(--tinta-suave); color: var(--tinta-suave); border-radius: 8px;
  font: 700 12px var(--f-texto); letter-spacing:.06em; text-transform: uppercase; padding: 2px 8px; }}
.fb-modo {{ font: 600 13px var(--f-texto); color: var(--tinta-suave); }}

/* ---- Tarjeta etiqueta de regalo ---- */
.fb-etiqueta {{ position: relative; background: var(--papel); border: 1px solid var(--carton); border-radius: 18px;
  box-shadow: var(--sombra); padding: 26px 20px 20px 20px; height: 100%; }}
.fb-etiqueta::before {{ content: ""; position: absolute; top: 12px; left: 12px; width: 10px; height: 10px;
  border-radius: 50%; background: var(--crema); border: 1px solid var(--carton); }}
.fb-etiqueta h3, .fb-etiqueta h4 {{ margin: 6px 0 6px 0; font-size: 20px !important; }}
.fb-etiqueta p {{ color: var(--tinta-suave); margin: 0 0 8px 0; font-size: 16px; line-height: 1.5; }}
.fb-etiqueta img.fb-ilus {{ width: 100%; aspect-ratio: 4/3; object-fit: cover; border-radius: 12px;
  background: var(--crema); margin-bottom: 10px; }}
.fb-etiqueta .fb-meta {{ font-size: 14px; color: var(--tinta-suave); }}
.fb-sobrio {{ border-radius: 14px; }}
.fb-sobrio::before {{ display:none; }}

/* ---- KPIs ---- */
.fb-kpi {{ background: var(--papel); border: 1px solid var(--carton); border-radius: 16px; padding: 18px 20px; height: 100%; }}
.fb-kpi .fb-kpi-valor {{ font: 800 clamp(30px, 3.4vw, 42px)/1.1 var(--f-texto); font-variant-numeric: tabular-nums; color: var(--noche); }}
.fb-kpi .fb-kpi-etiqueta {{ font: 700 13px var(--f-texto); letter-spacing: .08em; text-transform: uppercase; color: var(--tinta-suave); margin-top: 6px; }}
.fb-kpi .fb-kpi-nota {{ font-size: 13px; color: var(--tinta-suave); margin-top: 4px; }}
.fb-franja-kpi {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 16px; }}
@media (max-width: 900px) {{ .fb-franja-kpi {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}
.fb-franja-kpi .fb-kpi {{ background: var(--noche); border-color: var(--noche); }}
.fb-franja-kpi .fb-kpi-valor {{ color: var(--oro); }}
.fb-franja-kpi .fb-kpi-etiqueta {{ color: #E7E3DA; }}

/* ---- Pasos ---- */
.fb-pasos {{ display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 20px; position: relative; }}
.fb-pasos::before {{ content:""; position:absolute; top: 34px; left: 8%; right: 8%; border-top: 3px dotted var(--oro); z-index:0; }}
.fb-paso {{ position: relative; z-index: 1; text-align: center; }}
.fb-paso .fb-paso-num {{ width: 64px; height: 64px; margin: 0 auto 12px auto; border-radius: 50%; background: var(--noche);
  color: var(--oro); display:flex; align-items:center; justify-content:center; font: 800 24px var(--f-texto); border: 4px solid var(--crema); }}
.fb-paso h4 {{ margin: 0 0 4px 0; }}
.fb-paso p {{ color: var(--tinta-suave); font-size: 15px; margin: 0; }}
@media (max-width: 760px) {{ .fb-pasos {{ grid-template-columns: 1fr 1fr; }} .fb-pasos::before {{ display:none; }} }}

/* ---- Cartas (papel) ---- */
.fb-cartas {{ display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 24px; }}
@media (max-width: 860px) {{ .fb-cartas {{ grid-template-columns: 1fr; }} }}
.fb-carta-frag {{ background: repeating-linear-gradient(#FFFDF8, #FFFDF8 29px, #EFE5D3 30px); border: 1px solid var(--carton);
  border-radius: 6px; padding: 22px 22px 16px 22px; box-shadow: var(--sombra); font-family: var(--f-titulos);
  font-style: italic; font-size: 18px; line-height: 30px; color: var(--noche); }}
.fb-carta-frag small {{ display:block; font: 600 13px var(--f-texto); color: var(--tinta-suave); font-style: normal; margin-top: 8px; }}
.fb-gira-1 {{ transform: rotate(-2deg); }} .fb-gira-2 {{ transform: rotate(1.5deg); }} .fb-gira-3 {{ transform: rotate(-1deg); }}
@media (prefers-reduced-motion: reduce) {{ .fb-gira-1, .fb-gira-2, .fb-gira-3 {{ transform: none; }} }}

/* Área de la carta a los Reyes */
.st-key-papel_carta textarea {{ background: repeating-linear-gradient(#FFFDF8, #FFFDF8 31px, #EADFCB 32px) !important;
  line-height: 32px !important; font-family: var(--f-titulos) !important; font-size: 19px !important; color: var(--noche) !important;
  padding: 8px 16px !important; }}
.st-key-papel_carta [data-baseweb="textarea"] {{ border: 3px dashed var(--granada) !important; border-radius: 10px !important; outline: 6px solid #FFFDF8; }}

/* ---- Línea de tiempo ---- */
.fb-timeline {{ list-style: none; padding: 0; margin: 0; position: relative; }}
.fb-timeline::before {{ content:""; position:absolute; left: 15px; top: 6px; bottom: 6px; border-left: 3px solid var(--carton); }}
.fb-timeline li {{ position: relative; padding: 0 0 22px 48px; }}
.fb-timeline .fb-hito {{ position:absolute; left: 4px; top: 0; width: 26px; height: 26px; border-radius: 50%;
  background: var(--carton); display:flex; align-items:center; justify-content:center; font: 800 13px var(--f-texto); color: var(--noche); }}
.fb-timeline li.hecho .fb-hito {{ background: var(--pino); color: #fff; }}
.fb-timeline li.actual .fb-hito {{ background: var(--noche); }}
.fb-timeline li.pendiente {{ color: var(--tinta-suave); }}
.fb-timeline li strong {{ font-family: var(--f-texto); font-size: 17px; }}
.fb-timeline li span.fecha {{ display:block; font-size: 14px; color: var(--tinta-suave); }}

/* ---- Indicador de pasos 1-2-3 ---- */
.fb-progreso {{ display:flex; gap: 8px; margin: 8px 0 20px 0; flex-wrap: wrap; }}
.fb-progreso span {{ flex: 1 1 120px; border-radius: 999px; padding: 8px 14px; background: var(--papel); border: 1px solid var(--carton);
  font: 700 14px var(--f-texto); color: var(--tinta-suave); }}
.fb-progreso span.activo {{ background: var(--noche); color: var(--crema); border-color: var(--noche); }}
.fb-progreso span.hecho {{ background: var(--oro-suave); color: var(--noche); }}

/* ---- Rejilla de juguetes responsive ---- */
[class*="st-key-rejilla"] [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; gap: 20px; }}
[class*="st-key-rejilla"] [data-testid="stColumn"] {{ flex: 1 1 230px !important; min-width: 230px; }}
@media (max-width: 520px) {{ [class*="st-key-rejilla"] [data-testid="stColumn"] {{ min-width: 100%; }} }}

/* ---- Tarjetas en columnas: misma altura y botones alineados ---- */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{ height: 100%; }}
[data-testid="stColumn"] [data-testid="stElementContainer"]:has(.fb-etiqueta) {{ flex: 1 1 auto; display: flex; flex-direction: column; }}
[data-testid="stColumn"] [data-testid="stElementContainer"]:has(.fb-etiqueta) [data-testid="stMarkdown"],
[data-testid="stColumn"] [data-testid="stElementContainer"]:has(.fb-etiqueta) [data-testid="stMarkdown"] > div,
[data-testid="stColumn"] [data-testid="stElementContainer"]:has(.fb-etiqueta) [data-testid="stMarkdownContainer"] {{
  flex: 1 1 auto; display: flex; flex-direction: column; margin-bottom: 0 !important; }}
[data-testid="stColumn"] .fb-etiqueta {{ flex: 1 1 auto; height: auto; }}

/* ---- Puertas ---- */
.fb-puerta img {{ height: 120px; object-fit: contain; }}
.fb-puerta h3 {{ min-height: 2.6em; }}
.fb-puerta p {{ min-height: 3.2em; }}
[data-testid="stHeaderActionElements"] {{ display: none; }}

/* ---- Pie ---- */
.fb-pie {{ background: var(--noche-profunda); color: #D9D4CA; border-radius: 28px 28px 0 0; padding: 40px 40px 28px 40px;
  margin-top: 72px; font-family: var(--f-texto); }}
.fb-pie a {{ color: var(--oro-suave); text-decoration: none; margin-right: 18px; display:inline-block; min-height: 32px; }}
.fb-pie a:hover {{ text-decoration: underline; }}
.fb-pie .fb-pie-cols {{ display:grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 32px; }}
.fb-pie h4 {{ color: var(--oro) !important; font-family: var(--f-texto) !important; font-size: 13px !important;
  letter-spacing:.08em; text-transform: uppercase; margin: 0 0 10px 0; }}
.fb-pie p {{ color: #D9D4CA !important; font-size: 15px !important; margin: 0 0 8px 0; }}
.fb-pie .fb-pie-legal {{ border-top: 1px solid rgba(233,220,198,.2); margin-top: 24px; padding-top: 16px; font-size: 13px; color: #B9B4AA; }}
@media (max-width: 760px) {{ .fb-pie {{ padding: 28px 20px; }} .fb-pie .fb-pie-cols {{ grid-template-columns: 1fr; }} }}

/* ---- Varios ---- */
.fb-seccion {{ margin: 56px 0 16px 0; }}
.fb-seccion h2 {{ margin: 0 !important; padding: 0 !important; }}
.fb-seccion p.fb-sub {{ color: var(--tinta-suave); margin: 6px 0 0 0; }}
.fb-vacio {{ text-align:center; padding: 28px; background: var(--papel); border: 1px dashed var(--carton); border-radius: 18px; }}
.fb-vacio img {{ width: 160px; }}
.fb-confianza {{ display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 20px; }}
@media (max-width: 860px) {{ .fb-confianza {{ grid-template-columns: 1fr; }} }}
.fb-lista-si li::marker {{ color: var(--pino); }}
.fb-cifra-grande {{ font: 800 clamp(40px, 6vw, 64px)/1 var(--f-texto); color: var(--oro); font-variant-numeric: tabular-nums; }}
.fb-estrellas {{ display:inline-flex; gap: 2px; vertical-align: middle; }}
[data-testid="stExpander"] details {{ background: var(--papel); border-color: var(--carton) !important; border-radius: 14px !important; }}
[data-testid="stForm"] {{ background: var(--papel); border-color: var(--carton) !important; border-radius: 18px; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--carton) !important; }}
[data-testid="stImage"] img {{ border-radius: 12px; }}
img {{ max-width: 100%; }}
</style>
"""


def ola_svg(color: str = CARTON) -> str:
    """Separador ondulado tipo cinta de regalo."""
    return (
        '<svg class="fb-ola" viewBox="0 0 1200 22" preserveAspectRatio="none" aria-hidden="true">'
        f'<path d="M0 11 Q 50 0 100 11 T 200 11 T 300 11 T 400 11 T 500 11 T 600 11 T 700 11 T 800 11 T 900 11 '
        f'T 1000 11 T 1100 11 T 1200 11" fill="none" stroke="{color}" stroke-width="3"/></svg>'
    )
