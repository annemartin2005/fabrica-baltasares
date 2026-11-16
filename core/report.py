"""Informe de impacto social en PDF (fpdf2 + gráficos de matplotlib). Solo datos agregados."""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from fpdf import FPDF  # noqa: E402
from fpdf.enums import XPos, YPos  # noqa: E402

from core import db, metrics, theme  # noqa: E402
from core.components import euros, numero  # noqa: E402


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _fuentes() -> dict[str, Path]:
    """Fraunces/Nunito si están en assets/fonts; si no, DejaVu (incluida con matplotlib)."""
    propias = db.RAIZ / "assets" / "fonts"
    mpl = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    candidatos = {
        "titulo": [propias / "Fraunces-Bold.ttf", mpl / "DejaVuSerif-Bold.ttf"],
        "texto": [propias / "Nunito-Regular.ttf", mpl / "DejaVuSans.ttf"],
        "negrita": [propias / "Nunito-Bold.ttf", mpl / "DejaVuSans-Bold.ttf"],
        "cursiva": [propias / "Fraunces-Italic.ttf", mpl / "DejaVuSerif-Italic.ttf"],
    }
    return {k: next(p for p in v if p.exists()) for k, v in candidatos.items()}


class Informe(FPDF):
    def __init__(self, titulo: str) -> None:
        super().__init__(format="A4")
        self.titulo = titulo
        f = _fuentes()
        self.add_font("Titulo", "", str(f["titulo"]))
        self.add_font("Texto", "", str(f["texto"]))
        self.add_font("Texto", "B", str(f["negrita"]))
        self.add_font("Cita", "", str(f["cursiva"]))
        self.set_auto_page_break(True, margin=20)
        self.set_margins(18, 18, 18)

    def estrella(self, x: float, y: float, r: float, color: str = theme.ORO) -> None:
        self.set_fill_color(*_hex(color))
        k = r * 0.22
        pts = [(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)]
        self.polygon(pts, style="F")

    def header(self) -> None:
        self.set_fill_color(*_hex(theme.NOCHE))
        self.rect(0, 0, 210, 24, style="F")
        self.estrella(22, 12, 5)
        self.set_xy(31, 6)
        self.set_text_color(*_hex(theme.ORO_SUAVE))
        self.set_font("Texto", "B", 8)
        self.cell(0, 5, "LA FÁBRICA DE BALTASARES", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(31)
        self.set_text_color(255, 255, 255)
        self.set_font("Titulo", "", 13)
        self.cell(0, 8, self.titulo)
        self.set_y(32)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Texto", "", 8)
        self.set_text_color(*_hex(theme.TINTA_SUAVE))
        self.cell(0, 6, f"Informe de impacto social · Datos agregados, sin datos personales · Página {self.page_no()}",
                  align="C")

    def h2(self, texto: str) -> None:
        self.ln(3)
        self.set_font("Titulo", "", 15)
        self.set_text_color(*_hex(theme.NOCHE))
        self.cell(0, 9, texto, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*_hex(theme.ORO))
        self.set_line_width(0.8)
        self.line(self.l_margin, self.get_y(), self.l_margin + 18, self.get_y())
        self.ln(3)

    def parrafo(self, texto: str, tam: float = 10.5) -> None:
        self.set_font("Texto", "", tam)
        self.set_text_color(*_hex(theme.TINTA))
        self.multi_cell(0, 5.6, texto, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def kpis(self, items: list[tuple[str, str]]) -> None:
        ancho = (210 - 36 - 3 * 4) / 4
        y = self.get_y()
        for i, (valor, etiqueta) in enumerate(items):
            fila, col = divmod(i, 4)
            x = self.l_margin + col * (ancho + 4)
            yy = y + fila * 26
            self.set_fill_color(*_hex(theme.CREMA))
            self.set_draw_color(*_hex(theme.CARTON))
            self.set_line_width(0.3)
            self.rect(x, yy, ancho, 22, style="DF", round_corners=True, corner_radius=3)
            self.set_xy(x + 3, yy + 3)
            self.set_font("Texto", "B", 16)
            self.set_text_color(*_hex(theme.NOCHE))
            self.cell(ancho - 6, 8, valor)
            self.set_xy(x + 3, yy + 12)
            self.set_font("Texto", "", 7.5)
            self.set_text_color(*_hex(theme.TINTA_SUAVE))
            self.multi_cell(ancho - 6, 3.6, etiqueta.upper(), align="L")
        self.set_y(y + 26 * ((len(items) - 1) // 4 + 1) + 2)

    def imagen(self, fig, alto: float = 62) -> None:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", transparent=False, facecolor="white")
        plt.close(fig)
        buf.seek(0)
        if self.get_y() + alto > 277:
            self.add_page()
        self.image(buf, x=self.l_margin, w=174, h=alto, keep_aspect_ratio=True)
        self.ln(2)


def _estilo_mpl() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": theme.CARTON, "axes.labelcolor": theme.TINTA_SUAVE,
                         "xtick.color": theme.TINTA_SUAVE, "ytick.color": theme.TINTA_SUAVE})


def _graf_barras(etiquetas, valores, color=theme.NOCHE, titulo="", horizontal=False):
    fig, ax = plt.subplots(figsize=(8, 2.9))
    if horizontal:
        ax.barh(etiquetas, valores, color=color)
        ax.invert_yaxis()
        ax.grid(axis="x", color=theme.CARTON, alpha=.6)
    else:
        ax.bar(etiquetas, valores, color=color, width=.6)
        ax.grid(axis="y", color=theme.CARTON, alpha=.6)
    ax.set_axisbelow(True)
    ax.set_title(titulo, loc="left", color=theme.NOCHE, fontsize=11, fontweight="bold")
    return fig


def generar(campana_id: int | None = None) -> bytes:
    _estilo_mpl()
    camp = db.uno("SELECT c.*, e.nombre AS empresa FROM campanas c LEFT JOIN empresas e ON e.id = c.empresa_id "
                  "WHERE c.id = ?", (campana_id,)) if campana_id else None
    titulo = f"Informe de impacto social · {camp['nombre']}" if camp else "Informe de impacto social · Todas las campañas"
    k = metrics.kpis(campana_id)
    pdf = Informe(titulo)
    pdf.add_page()

    # Resumen
    pdf.h2("Resumen")
    if camp:
        av = metrics.avance_campana(camp)
        pdf.parrafo(f"{camp['empresa']} se comprometió a financiar la logística de la campaña «{camp['nombre']}» "
                    f"({camp['zona']}) con una aportación de {euros(camp['aportacion'], 0)} y un objetivo de "
                    f"{av['objetivo']} juguetes entregados entre el {camp['fecha_inicio']} y el {camp['fecha_fin']}. "
                    f"A fecha de {date.today().strftime('%d/%m/%Y')} se han entregado {av['entregados']} juguetes: "
                    f"un {str(av['porcentaje']).replace('.', ',')} % del objetivo.")
        pdf.set_fill_color(*_hex(theme.CARTON))
        pdf.rect(pdf.l_margin, pdf.get_y(), 174, 5, style="F", round_corners=True, corner_radius=2.5)
        pdf.set_fill_color(*_hex(theme.PINO))
        pdf.rect(pdf.l_margin, pdf.get_y(), max(4, 174 * min(av["porcentaje"], 100) / 100), 5, style="F",
                 round_corners=True, corner_radius=2.5)
        pdf.ln(9)
    else:
        pdf.parrafo("Resultados agregados de todas las campañas activas de La Fábrica de Baltasares en Bilbao.")
    pdf.parrafo("Datos de demostración: este informe se genera con los datos ficticios del prototipo académico.", 8.5)

    # Resultados
    pdf.h2("Resultados")
    pdf.kpis([(numero(k["entregados"]), "Juguetes entregados"), (numero(k["ninos"]), "Niños alcanzados"),
              (numero(k["familias"]), "Familias atendidas"), (numero(k["entidades"]), "Entidades atendidas"),
              (numero(k["barrios"]), "Barrios"), (f"{str(k['dias_medios']).replace('.', ',')} d", "Días de donación a entrega"),
              (euros(k["coste_medio"]), "Coste medio por juguete"), (numero(k["donados"]), "Juguetes asignados" if camp else "Juguetes donados")])
    sem = metrics.entregas_por_semana(campana_id)
    if not sem.empty:
        pdf.imagen(_graf_barras([d.strftime("%d/%m") for d in sem["semana"]], sem["entregas"], theme.NOCHE,
                                "Entregas por semana"), 56)
    fr = metrics.distribucion("franja", campana_id)
    br = metrics.distribucion("barrio", campana_id)
    if not fr.empty:
        orden = [f for f in db.FRANJAS if f in set(fr["franja"])]
        fr = fr.set_index("franja").loc[orden].reset_index()
        pdf.imagen(_graf_barras([f"{f} años" for f in fr["franja"]], fr["entregas"], theme.ORO, "Entregas por franja de edad"), 52)
    if not br.empty:
        pdf.imagen(_graf_barras(br["barrio"], br["entregas"], theme.PINO, "Entregas por barrio", horizontal=True), 46)

    # Destino de la aportación
    pdf.h2("Destino de vuestra aportación")
    dest = metrics.destino_aportaciones(campana_id)
    total = dest["importe"].sum() if not dest.empty else 0
    pdf.parrafo(f"Coste total registrado: {euros(total)}. Coste medio por juguete entregado: {euros(k['coste_medio'])} "
                "(suma de costes de recogida, entrega, revisión y gestión ÷ juguetes entregados).")
    for _, f in dest.iterrows():
        pct = 100 * f["importe"] / total if total else 0
        pdf.set_font("Texto", "", 10)
        pdf.set_text_color(*_hex(theme.TINTA))
        pdf.cell(70, 6.5, f["destino"])
        pdf.set_fill_color(*_hex(theme.ORO))
        y = pdf.get_y() + 1.5
        pdf.rect(pdf.l_margin + 70, y, max(1, 70 * pct / 100), 3.5, style="F")
        pdf.set_x(pdf.l_margin + 144)
        pdf.cell(30, 6.5, f"{euros(f['importe'])} · {pct:.0f} %".replace(".", ","), align="R",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Impacto ambiental
    pdf.h2("Impacto ambiental")
    pdf.parrafo(f"{numero(k['rescatados'])} juguetes entregados eran stock fuera de catálogo, con taras estéticas o "
                f"excedentes que no se podían vender: unos {str(k['kg_rescatados']).replace('.', ',')} kg de producto "
                "rescatados del desecho y reutilizados (peso estimado por tipo de juguete).")

    # Necesidades pendientes
    pdf.h2("Necesidades pendientes")
    nec = metrics.necesidades_pendientes().sort_values("presion", ascending=False)
    pdf.parrafo("Franjas con más demanda en relación con el stock disponible (argumento para ampliar la colaboración):")
    for _, f in nec.head(3).iterrows():
        pdf.parrafo(f"•  {f['franja']} años: {f['stock']} juguetes disponibles frente a {f['demanda_21d']} pedidos en las "
                    f"últimas tres semanas, {f['avisos']} avisos en espera y {f['ninos_sin_cubrir_org']} niños de "
                    "entidades aún sin cubrir.", 10)

    # Voz del proyecto
    pdf.h2("Voz del proyecto")
    for f in metrics.fragmentos_cartas(3):
        if pdf.get_y() > 255:
            pdf.add_page()
        pdf.set_font("Cita", "", 11)
        pdf.set_text_color(*_hex(theme.NOCHE))
        pdf.multi_cell(0, 6, f"«{f['texto_anon']}»", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Texto", "", 8.5)
        pdf.set_text_color(*_hex(theme.TINTA_SUAVE))
        pdf.cell(0, 5, f"Carta anonimizada · niño de {f['edad']} años", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    # Cifras para la comunicación
    pdf.h2("Cifras para vuestra comunicación")
    quien = camp["empresa"].replace(" (empresa ficticia)", "") if camp else "Las empresas colaboradoras"
    frases = [
        f"{quien} ha hecho posible que {numero(k['entregados'])} juguetes revisados lleguen a {numero(k['ninos'])} niños "
        f"de {numero(k['familias'])} familias y {numero(k['entidades'])} entidades sociales de Bilbao.",
        f"Cada {euros(k['coste_medio'])} aportados se han traducido en un juguete entregado y trazable.",
        f"Se han rescatado del desecho {numero(k['rescatados'])} juguetes (≈ {str(k['kg_rescatados']).replace('.', ',')} kg).",
        f"El tiempo medio entre la donación y la entrega ha sido de {str(k['dias_medios']).replace('.', ',')} días.",
    ]
    for fr_ in frases:
        pdf.parrafo(f"•  {fr_}", 10)

    # Nota metodológica
    pdf.h2("Nota metodológica")
    pdf.parrafo(
        "Juguetes entregados: pedidos en estado «Entregado». Niños alcanzados: niños distintos en pedidos familiares "
        "(referencia anónima) más juguetes entregados a entidades (un juguete por niño). Familias: solicitudes "
        "familiares distintas. Entidades: entidades derivadoras y organizaciones receptoras distintas. Coste medio: "
        "costes registrados por el equipo ÷ juguetes entregados. Tiempo medio: desde el registro de la donación hasta "
        "la entrega. Rescatados: entregados con estado «Fuera de catálogo» o «Tara estética», o donados por empresas. "
        "Todas las cifras son agregadas; el informe no contiene datos personales y las cartas se anonimizan antes "
        "de guardarse.", 8.5)
    return bytes(pdf.output())
