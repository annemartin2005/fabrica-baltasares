"""Donar: particular (3 pasos con etiquetado automático) o empresa (lote)."""
import re
import uuid
from datetime import date, timedelta

import streamlit as st

from core import ai, db, theme, tracking
from core.components import chips, html, modo_ia, progreso, texto_edad
from core.events import registrar

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
S = st.session_state
S.setdefault("don_paso", 1)
S.setdefault("don", {})

html('<p class="fb-antetitulo">Donar</p><h1>Dale una segunda vida a un juguete</h1>'
     '<p style="max-width:720px">Solo aceptamos juguetes en perfecto estado de uso: nuevos, fuera de catálogo o con '
     'taras estéticas. Sube unas fotos: las revisamos antes de publicarlo y tu juguete se queda en casa hasta que un '
     'niño lo elija. Entonces te avisamos y eliges si GUBI lo recoge en tu casa (gratis) o si lo dejas en un punto.</p>'
     f'<p class="fb-meta">Campaña de Reyes: donaciones del {tracking.CAMPANA["donaciones_desde"]} al '
     f'{tracking.CAMPANA["donaciones_hasta"]} · entregas hasta el {tracking.CAMPANA["entregas_hasta"]}.</p>')

tipo = st.segmented_control("¿Quién dona?", ["Particular", "Empresa (lote)"], default="Particular",
                            key="don_tipo", required=True)


# ---------------------------------------------------------------------------
def exito(codigo: str, texto: str, clave: str) -> None:
    S["ultimo_codigo"] = codigo
    html(f'<div class="fb-etiqueta" style="text-align:center;padding:36px">{theme.estrella_svg(44)}'
         f'<h2>¡Gracias! Tu donación está registrada</h2><p>{texto}</p>'
         f'<p class="fb-antetitulo" style="margin-top:16px">Tu código de seguimiento</p>'
         f'<div class="fb-cifra-grande" style="color:var(--noche)">{codigo}</div>'
         '<p class="fb-meta">Te hemos enviado un email de confirmación. Guarda el código para seguir el recorrido.</p></div>')
    c1, c2, _ = st.columns([1, 1, 1])
    if c1.button("Ver el seguimiento", type="primary", icon=":material/local_shipping:", key="ir_seg"):
        st.switch_page("paginas/seguimiento.py", query_params={"codigo": codigo})
    if c2.button("Hacer otra donación", type="secondary", key="otro"):
        S["don_paso"], S["don"] = 1, {}
        S.pop(clave, None)
        st.rerun()


# --- Empresa -------------------------------------------------------------------
if tipo == "Empresa (lote)":
    if not S.get("_ev_lote"):
        registrar("cta_ver_condiciones", "empresa_especie")
        S["_ev_lote"] = True
    if S.get("lote_exito"):
        exito(S["lote_exito"], "GUBI os contactará para confirmar la fecha de recogida del lote.", "lote_exito")
        st.stop()
    html('<div class="fb-etiqueta fb-sobrio"><h3>Condiciones para lotes de empresa</h3><p>Aceptamos stock fuera de '
         'catálogo, excedentes y unidades con taras estéticas (caja dañada, color defectuoso). No aceptamos productos '
         'retirados por seguridad ni con piezas sueltas. Los lotes no esperan a que un niño los elija: GUBI los '
         'recoge en vuestras instalaciones, los lleva a su local, revisa una muestra representativa y los publica. '
         'Os enviaremos el certificado de donación en especie.</p></div>')
    st.write("")
    with st.form("lote"):
        c1, c2 = st.columns(2)
        empresa = c1.text_input("Nombre de la empresa")
        contacto = c2.text_input("Persona de contacto")
        email = c1.text_input("Email de contacto")
        producto = c2.text_input("Tipo de producto", placeholder="Puzles infantiles de 48 piezas")
        unidades = c1.number_input("Número aproximado de unidades", min_value=1, max_value=5000, value=50, step=10)
        edad = c2.selectbox("Franja de edad", list(db.FRANJAS))
        motivo = c1.selectbox("Motivo", ["Fuera de catálogo", "Tara estética", "Excedente"])
        fecha = c2.date_input("Fecha preferida de recogida", value=date.today() + timedelta(days=7),
                              min_value=date.today(), format="DD/MM/YYYY")
        seguro = st.checkbox("Confirmo que el lote cumple los criterios de seguridad (sin piezas sueltas, pilas de "
                             "botón accesibles ni bordes cortantes).")
        enviar = st.form_submit_button("Agendar recogida", type="primary", icon=":material/event:")
    if enviar:
        registrar("cta_indicar_lote", "empresa_especie")
        errores = []
        if not empresa.strip():
            errores.append("Indica el nombre de la empresa.")
        if not contacto.strip():
            errores.append("Indica la persona de contacto.")
        if not EMAIL_RE.match(email.strip()):
            errores.append("Indica un email válido.")
        if not producto.strip():
            errores.append("Indica el tipo de producto.")
        if not seguro:
            errores.append("Confirma los criterios de seguridad.")
        for e in errores:
            st.error(e)
        if not errores:
            r = tracking.crear_donacion_empresa({"empresa": empresa.strip(), "contacto": contacto.strip(),
                                                 "email": email.strip(), "producto": producto.strip(),
                                                 "unidades": int(unidades), "edad": edad, "motivo": motivo,
                                                 "fecha": fecha.strftime("%d/%m/%Y")})
            registrar("lote_registrado", "empresa_especie", r["codigo"])
            S["lote_exito"] = r["codigo"]
            st.rerun()
    st.stop()

# --- Particular -----------------------------------------------------------------
if S.get("don_exito"):
    exito(S["don_exito"], "Revisaremos las fotos en 24-48 h y lo publicaremos en el catálogo. Guárdalo en casa: "
          "cuando un niño lo elija te avisaremos para que elijas recogida gratuita en casa o dejarlo en un punto.",
          "don_exito")
    st.stop()

if not S.get("_ev_subir"):
    registrar("cta_subir_juguete", "donante")
    S["_ev_subir"] = True

progreso(["Tu juguete", "Etiquetado", "Contacto"], S["don_paso"])
d = S["don"]

if S["don_paso"] == 1:
    st.subheader("1. Tu juguete")
    fotos = st.file_uploader("Fotos del juguete (de 1 a 3)", type=["jpg", "jpeg", "png", "webp"],
                             accept_multiple_files=True, key="fotos",
                             help="Las revisamos antes de publicar el juguete: que se vean bien el juguete y su estado.")
    nombre = st.text_input("Nombre del juguete", value=d.get("nombre", ""), placeholder="Garaje de madera con 4 coches")
    descripcion = st.text_area("Descripción", value=d.get("descripcion", ""), height=110,
                               placeholder="Qué incluye, para qué edad es, si tiene pilas o sonido, cómo está la caja…")
    estados = db.ESTADOS_FISICOS
    estado = st.radio("Estado", estados, index=estados.index(d["estado_fisico"]) if d.get("estado_fisico") else 0,
                      horizontal=True)
    seguro = st.checkbox("Confirmo que el juguete está completo, sin piezas sueltas, sin pilas de botón accesibles, "
                         "sin bordes cortantes y sin roturas.", value=d.get("seguro", False))
    if st.button("Analizar mi juguete", type="primary", icon=":material/auto_awesome:"):
        errores = []
        if not fotos:
            errores.append("Sube al menos una foto: la necesitamos para la revisión online.")
        elif len(fotos) > 3:
            errores.append("Sube como máximo 3 fotos.")
        if len(nombre.strip()) < 3:
            errores.append("Indica el nombre del juguete.")
        if len(descripcion.strip()) < 10:
            errores.append("Describe el juguete con algo más de detalle (mínimo 10 caracteres).")
        if not seguro:
            errores.append("Debes confirmar los criterios de seguridad para continuar.")
        for e in errores:
            st.error(e)
        if not errores:
            rutas = []
            for f in (fotos or [])[:3]:
                ext = f.name.rsplit(".", 1)[-1].lower()
                destino = db.UPLOADS / f"{uuid.uuid4().hex}.{ext}"
                destino.write_bytes(f.getvalue())
                rutas.append(str(destino.relative_to(db.RAIZ)).replace("\\", "/"))
            imagen = fotos[0].getvalue() if fotos else None
            tipo_img = fotos[0].type if fotos else "image/jpeg"
            with st.spinner("Analizando tu juguete…"):
                etiquetas = ai.etiquetar_juguete(nombre, descripcion, imagen, tipo_img)
            d.update({"nombre": nombre.strip(), "descripcion": descripcion.strip(), "estado_fisico": estado,
                      "seguro": True, "fotos": rutas, "etiquetas": etiquetas})
            registrar("juguete_analizado", "donante")
            S["don_paso"] = 2
            st.rerun()

elif S["don_paso"] == 2:
    st.subheader("2. Etiquetado automático")
    et = d["etiquetas"]
    modo_ia(et["modo"])
    st.write("Esta es nuestra propuesta. Corrígela si algo no encaja.")
    c1, c2 = st.columns([1, 1.3], gap="large")
    with c1:
        from core.components import tarjeta_juguete
        vista = {"nombre": d["nombre"], "categoria": et["categoria"], "edad_min": et["edad_min"],
                 "edad_max": et["edad_max"], "estado_fisico": d["estado_fisico"], "fotos": d["fotos"]}
        html(tarjeta_juguete(vista, chips(et["intereses"])))
    with c2:
        cats = list(db.CATEGORIAS)
        categoria = st.selectbox("Categoría", cats, index=cats.index(et["categoria"]),
                                 format_func=lambda c: db.CATEGORIAS[c])
        edades = st.slider("Franja de edad", 0, 16, (min(et["edad_min"], 16), min(et["edad_max"], 16)))
        intereses = st.multiselect("Intereses", list(ai.INTERESES), default=et["intereses"])
        restr = st.multiselect("Cumple estas condiciones", list(db.RESTRICCIONES), default=et["restricciones_cumplidas"],
                               format_func=lambda r: db.RESTRICCIONES[r],
                               help="GUBI lo comprobará en la revisión física, cuando el juguete llegue a su local.")
    b1, b2, _ = st.columns([1, 1, 2])
    if b1.button("Atrás", type="secondary"):
        S["don_paso"] = 1
        st.rerun()
    if b2.button("Continuar", type="primary"):
        if not intereses:
            st.error("Elige al menos un interés para poder emparejarlo bien.")
        else:
            edad_max = 99 if edades[1] >= 16 and categoria == "juego_mesa" else edades[1]
            d["final"] = {"categoria": categoria, "edad_min": edades[0], "edad_max": edad_max,
                          "intereses": intereses, "restricciones": restr}
            S["don_paso"] = 3
            st.rerun()

else:
    st.subheader("3. Contacto")
    st.write("No tienes que llevarlo a ningún sitio todavía. Cuando un niño elija tu juguete te avisaremos por email "
             "(y por WhatsApp si nos dejas tu móvil) y tendrás 3 días para elegir si GUBI lo recoge en tu casa "
             "(gratis) o si lo dejas en un punto de recogida.")
    pts = db.puntos()
    c1, c2 = st.columns(2)
    email = c1.text_input("Email de contacto", value=d.get("email", ""), placeholder="tu@email.com")
    telefono = c2.text_input("Móvil para avisos por WhatsApp (opcional)", value=d.get("telefono", ""),
                             placeholder="600 000 000")
    barrio = c1.selectbox("Barrio más cercano", pts, format_func=lambda p: p["barrio"],
                          help="Nos ayuda a organizar la recogida y a mostrar el juguete en el catálogo.")
    privacidad = st.checkbox("Acepto que usemos mi email y mi móvil solo para gestionar esta donación. No se "
                             "comparten con terceros salvo GUBI para la logística.")
    b1, b2, _ = st.columns([1, 1.4, 1.6])
    if b1.button("Atrás", type="secondary"):
        S["don_paso"] = 2
        st.rerun()
    if b2.button("Enviar a revisión", type="primary", icon=":material/check:"):
        errores = []
        tel = re.sub(r"[^0-9+]", "", telefono)
        if not EMAIL_RE.match(email.strip()):
            errores.append("Indica un email válido para enviarte el código.")
        if telefono.strip() and len(tel) < 9:
            errores.append("Revisa el móvil (al menos 9 cifras) o déjalo vacío.")
        if not privacidad:
            errores.append("Necesitamos tu consentimiento de privacidad para registrar la donación.")
        for e in errores:
            st.error(e)
        if not errores:
            f = d["final"]
            juguete = {"nombre": d["nombre"], "descripcion": d["descripcion"], "estado_fisico": d["estado_fisico"],
                       **f}
            r = tracking.crear_donacion_particular(juguete, email.strip(), d["fotos"], barrio_id=barrio["id"],
                                                   telefono=tel)
            registrar("donacion_registrada", "donante", r["codigo"])
            S["don_exito"] = r["codigo"]
            S["don"], S["don_paso"] = {}, 1
            st.rerun()

    st.caption(f"Resumen: {d['nombre']} · {db.CATEGORIAS[d['final']['categoria']]} · "
               f"{texto_edad(d['final']['edad_min'], d['final']['edad_max'])}")
