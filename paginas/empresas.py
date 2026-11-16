"""Empresas: formas de colaborar, qué reciben, equivalencia y gradiente de compromiso."""
import re
from datetime import date, timedelta

import streamlit as st

from core import db, metrics, report, tracking
from core.components import euros, html, kpi, numero, seccion
from core.events import registrar

S = st.session_state
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

if not S.get("_ev_emp"):
    registrar("cta_ver_impacto", "empresa_financiadora")
    S["_ev_emp"] = True


@st.cache_data(ttl=60, show_spinner="Preparando el informe…")
def informe_ejemplo() -> bytes:
    camp = db.campanas()[0]
    return report.generar(camp["id"])


k = metrics.kpis()
with st.container(key="oscuro_emp_hero"):
    c1, c2 = st.columns([1.5, 1], vertical_alignment="center", gap="large")
    with c1:
        html('<p class="fb-antetitulo">Empresas</p><h1>Vuestra aportación, convertida en entregas que podéis demostrar</h1>'
             '<p style="font-size:19px">Cada aportación se traduce en entregas trazables: sabréis cuántos juguetes, a '
             'cuántos niños, en qué barrios y a qué coste.</p>')
    with c2:
        html(f'<p class="fb-antetitulo">Hoy</p><div class="fb-cifra-grande">{euros(k["coste_medio"])}</div>'
             '<p>hacen llegar un juguete revisado a un niño</p>'
             f'<p style="font-size:14px;opacity:.85">Coste medio por juguete entregado, calculado con los costes '
             f'reales registrados ({euros(k["coste_total"], 0)} ÷ {numero(k["entregados"])} entregas).</p>')
    b1, b2, _ = st.columns([1, 1.2, 1.3])
    if b1.button("Ver el impacto", type="primary", icon=":material/insights:", width="stretch"):
        registrar("cta_ver_impacto_dashboard", "empresa_financiadora")
        st.switch_page("paginas/impacto.py")
    with b2:
        st.download_button("Descargar informe de ejemplo", data=informe_ejemplo(), file_name="informe_impacto_ejemplo.pdf",
                           mime="application/pdf", type="secondary", icon=":material/download:", width="stretch",
                           on_click=registrar, args=("informe_ejemplo_descargado", "empresa_financiadora"))

seccion("Tres formas de colaborar", ante="Colaborar")
c1, c2, c3 = st.columns(3)
for col, (t, d) in zip([c1, c2, c3], [
        ("Aportación económica", "Financia la logística de una campaña solidaria: recogida, revisión de seguridad y "
         "entrega de GUBI. Es la forma que más niños alcanza."),
        ("Donación en especie", "Stock fuera de catálogo, excedentes o unidades con taras estéticas que no podéis vender. "
         "Lo recogemos en vuestras instalaciones."),
        ("Voluntariado corporativo", "Jornadas de clasificación y empaquetado con GUBI, o reparto en los puntos de "
         "encuentro durante la campaña de Reyes.")]):
    with col:
        html(f'<div class="fb-etiqueta fb-sobrio"><h3>{t}</h3><p>{d}</p></div>')
if st.button("Donar stock en especie", type="secondary", icon=":material/inventory_2:"):
    registrar("cta_ver_condiciones", "empresa_especie")
    st.switch_page("paginas/donar.py")

seccion("Qué recibe vuestra empresa", ante="Transparencia")
c1, c2 = st.columns([1.2, 1], gap="large")
with c1:
    st.markdown(
        "- **Dashboard de impacto** actualizado en tiempo real con vuestro código de campaña.\n"
        "- **Informe de impacto social** descargable en PDF, con cifras agregadas y sin datos personales.\n\n"
        "Para qué os sirve:\n"
        "- **Justificar internamente** el destino de la aportación, euro a euro.\n"
        "- **Comunicar resultados** en la memoria de sostenibilidad (pilar social del ESG) y en la memoria de RSC.\n"
        "- **Comprobar que el proyecto funciona** con datos verificables.\n"
        "- **Decidir si renováis** con información de necesidades pendientes.")
with c2:
    html('<div class="fb-franja-kpi" style="grid-template-columns:1fr 1fr">'
         + kpi(numero(k["entregados"]), "Juguetes entregados") + kpi(numero(k["ninos"]), "Niños alcanzados")
         + kpi(numero(k["rescatados"]), "Rescatados del desecho") + kpi(f"{k['dias_medios']:.1f} d".replace(".", ","),
                                                                        "De donación a entrega")
         + "</div>")

# --- Proponer una colaboración --------------------------------------------------------
seccion("Proponer una colaboración", "Contadnos qué tenéis en mente y os preparamos una campaña a medida.",
        "Siguiente paso")
with st.form("colaboracion"):
    c1, c2 = st.columns(2)
    empresa = c1.text_input("Empresa")
    contacto = c2.text_input("Persona de contacto")
    email = c1.text_input("Email")
    tipo = c2.selectbox("Tipo de colaboración", ["Aportación económica", "Donación en especie", "Voluntariado corporativo",
                                                 "Varias"])
    aport = c1.number_input("Aportación orientativa (€)", min_value=0, step=250, value=1000,
                            help="Orientativa: sirve para dimensionar la campaña.")
    zona = c2.selectbox("Zona", ["Bilbao (todos los barrios)", "Deusto", "Santutxu", "Rekalde", "Otxarkoaga"])
    fechas = st.date_input("Fechas de la campaña", value=(date.today(), date(date.today().year + 1, 1, 6)),
                           format="DD/MM/YYYY")
    mensaje = st.text_area("Comentarios (opcional)")
    enviar = st.form_submit_button("Proponer una colaboración", type="primary", icon=":material/handshake:")
if enviar:
    errores = []
    if not empresa.strip():
        errores.append("Indica el nombre de la empresa.")
    if not contacto.strip():
        errores.append("Indica la persona de contacto.")
    if not EMAIL_RE.match(email.strip()):
        errores.append("Indica un email válido.")
    if not isinstance(fechas, tuple) or len(fechas) != 2:
        errores.append("Indica la fecha de inicio y de fin.")
    for e in errores:
        st.error(e)
    if not errores:
        cid = db.insertar("colaboraciones", {"empresa": empresa.strip(), "contacto": contacto.strip(), "email": email.strip(),
                                             "tipo": tipo, "aportacion": aport, "zona": zona,
                                             "fechas": f"{fechas[0].isoformat()} / {fechas[1].isoformat()}",
                                             "mensaje": mensaje, "estado": "propuesta", "creado": db.ahora()})
        tracking.notificar(email.strip(), "Hemos recibido vuestra propuesta de colaboración",
                           f"Hola, {contacto.strip()}:\n\nGracias por proponer una colaboración ({tipo}). Os escribiremos "
                           "en 48 horas laborables con una propuesta de campaña solidaria y su objetivo de juguetes.\n\n"
                           "La Fábrica de Baltasares")
        registrar("colaboracion_propuesta", "empresa_financiadora", str(cid))
        S["colab"] = {"id": cid, "empresa": empresa.strip(), "aportacion": aport, "zona": zona, "fechas": fechas,
                      "email": email.strip(), "contacto": contacto.strip()}
        st.success("Propuesta recibida. Si ya lo tenéis decidido, podéis confirmar el compromiso abajo.")


@st.dialog("Confirmar el compromiso de aportación")
def confirmar_compromiso(c: dict) -> None:
    coste = metrics.coste_medio_global() or 10
    st.write(f"**{c['empresa']}** · {c['zona']}")
    aport = st.number_input("Aportación comprometida (€)", min_value=100, step=100, value=max(int(c["aportacion"]), 100))
    objetivo = st.number_input("Objetivo de juguetes entregados", min_value=10, step=10,
                               value=max(10, int(aport // coste)),
                               help=f"Sugerido con el coste medio actual ({euros(coste)} por juguete).")
    st.caption("Se registra como compromiso firmado, no como cobro: no hay pasarela de pago. El equipo os enviará "
               "el convenio de colaboración.")
    acepto = st.checkbox("Confirmo el compromiso en nombre de la empresa.")
    if st.button("Confirmar el compromiso", type="primary", width="stretch"):
        if not acepto:
            st.error("Marca la casilla de confirmación.")
            return
        emp_id = db.insertar("empresas", {"nombre": c["empresa"], "contacto": c["contacto"], "email": c["email"],
                                          "sector": "", "ficticia": 0})
        base = re.sub(r"[^A-Z]", "", c["empresa"].upper())[:8] or "CAMP"
        codigo = f"{base}-{date.today().year}"
        if db.campana_por_codigo(codigo):
            codigo = db.nuevo_codigo(base, "campanas")
        f1, f2 = c["fechas"]
        db.insertar("campanas", {"codigo": codigo, "nombre": f"Campaña solidaria · {c['empresa']}", "empresa_id": emp_id,
                                 "objetivo_juguetes": int(objetivo), "aportacion": float(aport),
                                 "fecha_inicio": f1.isoformat(), "fecha_fin": f2.isoformat(), "zona": c["zona"],
                                 "estado": "activa", "creado": db.ahora()})
        db.actualizar("colaboraciones", c["id"], {"estado": "comprometida"})
        tracking.notificar(c["email"], f"Compromiso confirmado · campaña {codigo}",
                           f"Gracias por vuestro compromiso de {euros(aport)} para {int(objetivo)} juguetes.\n"
                           f"Código de campaña para vuestro dashboard privado: {codigo}\n\nLa Fábrica de Baltasares")
        registrar("compromiso_confirmado", "empresa_financiadora", codigo)
        S["compromiso_ok"] = codigo
        S.pop("colab", None)
        st.rerun()


if S.get("colab"):
    if st.button("Confirmar el compromiso de aportación", type="primary", icon=":material/verified:"):
        confirmar_compromiso(S["colab"])
if S.get("compromiso_ok"):
    st.success(f"Compromiso registrado. Vuestro código de campaña es **{S['compromiso_ok']}**: úsalo abajo para "
               "abrir vuestro dashboard privado.", icon=":material/verified:")

# --- Acceso al dashboard privado -----------------------------------------------------
seccion("Acceso a vuestro dashboard", ante="Empresas colaboradoras")
with st.form("acceso_campana"):
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    codigo = c1.text_input("Código de campaña", placeholder="LANTEGI-2026", value=S.get("compromiso_ok", ""))
    ir = c2.form_submit_button("Abrir", type="primary", width="stretch")
if ir:
    camp = db.campana_por_codigo(codigo)
    if camp:
        S["campana_privada"] = camp["codigo"]
        registrar("dashboard_privado_abierto", "empresa_financiadora", camp["codigo"])
        st.switch_page("paginas/impacto.py", query_params={"campana": camp["codigo"]})
    else:
        st.error("No encontramos esa campaña. Revisa el código que os enviamos al confirmar el compromiso.")
st.caption("Códigos de demostración: LANTEGI-2026 y TXOKOA-2026.")
