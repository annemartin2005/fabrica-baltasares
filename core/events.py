"""Registro de eventos del embudo (CTA y pasos completados) con el origen de la visita."""
from __future__ import annotations

import uuid

from core import db

# Embudos por público: orden de los eventos para calcular n/N entre pasos
EMBUDOS: dict[str, list[str]] = {
    "donante": ["cta_ver_como_funciona", "cta_subir_juguete", "juguete_analizado", "donacion_registrada"],
    "empresa_especie": ["cta_ver_condiciones", "cta_indicar_lote", "lote_registrado"],
    "familia": ["cta_ver_catalogo", "carta_enviada", "propuesta_vista", "juguete_elegido", "pedido_confirmado"],
    "organizacion": ["cta_ver_servicio", "necesidades_enviadas", "reparto_propuesto", "reparto_aprobado"],
    "empresa_financiadora": ["cta_ver_impacto", "informe_ejemplo_descargado", "colaboracion_propuesta",
                             "compromiso_confirmado"],
}


def _sesion_y_src() -> tuple[str, str]:
    try:
        import streamlit as st

        if "sesion_id" not in st.session_state:
            st.session_state["sesion_id"] = uuid.uuid4().hex[:12]
        return st.session_state["sesion_id"], st.session_state.get("src", "directo")
    except Exception:  # noqa: BLE001 - fuera de Streamlit (tests, scripts)
        return "script", "script"


def registrar(evento: str, publico: str, objeto: str = "", sesion: str | None = None, src: str | None = None,
              ts: str | None = None) -> None:
    s, o = _sesion_y_src()
    db.insertar("eventos", {"ts": ts or db.ahora(), "sesion": sesion or s, "src": src or o, "publico": publico,
                            "evento": evento, "objeto": objeto})
