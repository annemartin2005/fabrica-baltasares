"""Componentes HTML de marca: tarjetas etiqueta, chips, badges, KPIs, línea de tiempo."""
from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from core import theme
from core.db import CATEGORIAS, DATA, RAIZ

ICONOS_ESTADO = {"pendiente": "○", "proceso": "◐", "completado": "✓", "error": "✕"}


def html(contenido: str) -> None:
    st.markdown(contenido, unsafe_allow_html=True)


def boton_cta(etiqueta: str, destino: str, evento: str, publico: str, *, key: str, tipo: str = "primary",
              icono: str | None = None, ancho: bool = False) -> None:
    """Botón que registra el CTA como evento y navega a la página destino."""
    from core.events import registrar

    if st.button(etiqueta, key=key, type=tipo, icon=icono, width="stretch" if ancho else "content"):
        registrar(evento, publico)
        st.switch_page(destino)


def antetitulo(texto: str) -> str:
    return f'<p class="fb-antetitulo">{escape(texto)}</p>'


def seccion(titulo: str, sub: str = "", ante: str = "") -> None:
    html(f'<div class="fb-seccion">{antetitulo(ante) if ante else ""}<h2>{escape(titulo)}</h2>'
         f'{f"<p class=fb-sub>{escape(sub)}</p>" if sub else ""}</div>')


def chip(texto: str, variante: str = "") -> str:
    return f'<span class="fb-chip {variante}">{escape(str(texto))}</span>'


def chips(textos: list[str], variante: str = "") -> str:
    return "".join(chip(t, variante) for t in textos)


def badge(texto: str, tipo: str = "pendiente") -> str:
    return (f'<span class="fb-badge fb-badge-{tipo}"><span aria-hidden="true">{ICONOS_ESTADO.get(tipo, "•")}</span>'
            f'{escape(texto)}</span>')


def etiqueta_demo() -> str:
    return '<span class="fb-demo">Datos de demostración</span>'


def modo_ia(modo: str) -> None:
    texto = "Interpretado con IA" if modo == "ia" else "Interpretado con reglas"
    html(f'<p class="fb-modo">✦ {texto}</p>')


def estrellas(n: int, total: int = 5) -> str:
    piezas = "".join(theme.estrella_svg(18, theme.ORO if i < n else theme.CARTON) for i in range(total))
    return f'<span class="fb-estrellas" role="img" aria-label="Encaje: {n} de {total} estrellas">{piezas}</span>'


def ilustracion(categoria: str) -> str:
    cat = categoria if categoria in CATEGORIAS else "juego_mesa"
    return theme.svg_data_uri(f"illustrations/{cat}.svg")


def imagen_juguete(j: dict) -> tuple[str, str]:
    """(src, alt): primera foto si existe, si no la ilustración de su categoría."""
    for foto in j.get("fotos") or []:
        ruta = RAIZ / foto if not Path(foto).is_absolute() else Path(foto)
        if ruta.exists() and str(ruta.resolve()).startswith(str(DATA.resolve())):
            return theme.imagen_data_uri(ruta), f"Foto de {j['nombre']}"
    return ilustracion(j.get("categoria", "")), f"Ilustración de la categoría {CATEGORIAS.get(j.get('categoria'), '')}"


def texto_edad(emin: int, emax: int) -> str:
    if emax >= 99:
        return f"+{emin} años"
    if emax <= 1:
        return "0-1 años"
    return f"{emin}-{emax} años"


def tarjeta_juguete(j: dict, extra: str = "", sobria: bool = False) -> str:
    src, alt = imagen_juguete(j)
    meta = []
    if j.get("estado_fisico"):
        meta.append(escape(j["estado_fisico"]))
    if j.get("punto_nombre"):
        meta.append("📍 " + escape(j["punto_nombre"].split("·")[0].strip()))
    return (
        f'<div class="fb-etiqueta{" fb-sobrio" if sobria else ""}">'
        f'<img class="fb-ilus" src="{src}" alt="{escape(alt)}">'
        f'<h3>{escape(j["nombre"])}</h3>'
        f'<div>{chip(texto_edad(j["edad_min"], j["edad_max"]))}{chip(CATEGORIAS.get(j["categoria"], j["categoria"]), "fb-chip-carton")}</div>'
        f'<p class="fb-meta">{" · ".join(meta)}</p>{extra}</div>'
    )


def kpi(valor: str, etiqueta: str, nota: str = "") -> str:
    return (f'<div class="fb-kpi"><div class="fb-kpi-valor">{escape(str(valor))}</div>'
            f'<div class="fb-kpi-etiqueta">{escape(etiqueta)}</div>'
            f'{f"<div class=fb-kpi-nota>{escape(nota)}</div>" if nota else ""}</div>')


def vacio(texto: str, categoria: str = "juego_mesa", siguiente: str = "") -> None:
    html(f'<div class="fb-vacio"><img src="{ilustracion(categoria)}" alt="" aria-hidden="true">'
         f'<p><strong>{escape(texto)}</strong></p>{f"<p>{escape(siguiente)}</p>" if siguiente else ""}</div>')


def progreso(pasos: list[str], actual: int) -> None:
    piezas = []
    for i, p in enumerate(pasos, 1):
        clase = "activo" if i == actual else ("hecho" if i < actual else "")
        marca = "✓ " if i < actual else f"{i}. "
        actual_aria = ' aria-current="step"' if i == actual else ""
        piezas.append(f'<span class="{clase}"{actual_aria}>{marca}{escape(p)}</span>')
    html(f'<div class="fb-progreso" role="list" aria-label="Progreso">{"".join(piezas)}</div>')


def linea_tiempo(hitos: list[dict]) -> None:
    """hitos: [{'titulo', 'fecha', 'estado': hecho|actual|pendiente, 'nota'}]"""
    items = []
    for i, h in enumerate(hitos, 1):
        icono = "✓" if h["estado"] == "hecho" else (theme.estrella_svg(16) if h["estado"] == "actual" else str(i))
        fecha = f'<span class="fecha">{escape(h["fecha"])}</span>' if h.get("fecha") else ""
        nota = f'<span class="fecha">{escape(h["nota"])}</span>' if h.get("nota") else ""
        etiqueta = " (estado actual)" if h["estado"] == "actual" else ""
        items.append(f'<li class="{h["estado"]}"><span class="fb-hito" aria-hidden="true">{icono}</span>'
                     f'<strong>{escape(h["titulo"])}</strong><span class="visually-hidden">{etiqueta}</span>{fecha}{nota}</li>')
    html(f'<ol class="fb-timeline">{"".join(items)}</ol>')


def fecha_legible(iso: str | None) -> str:
    if not iso:
        return ""
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    try:
        d = iso[:16].replace("T", " ")
        y, m, rest = d.split("-", 2)
        dia, hora = (rest.split(" ") + [""])[:2]
        return f"{int(dia)} {meses[int(m) - 1]} {y}" + (f", {hora}" if hora else "")
    except (ValueError, IndexError):
        return iso


def euros(valor: float, decimales: int = 2) -> str:
    texto = f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto} €"


def numero(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")
