"""Máquina de estados de donaciones y pedidos, historial y bandeja de salida de emails.

Recorrido de una donación de particular (el juguete se queda en casa del donante hasta que alguien lo elige):
  registrada → revisión online de las fotos → publicada → match (emparejada) → el donante elige en 3 días
  recogida en casa o dejarlo en un punto → GUBI lo lleva a su local (recibida) → revisión física (revisada)
  → entregada.  Si no supera la revisión física, o el donante no responde, el niño recibe otro juguete parecido.

Los lotes de empresa siguen el recorrido clásico: GUBI los recoge y revisa antes de publicarlos.
"""
from __future__ import annotations

import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage

from core import db

# --- Datos fijos de la campaña y del local de GUBI (ficticios) -------------
ALMACEN = {"nombre": "Local de GUBI · Zorrotzaurre",
           "direccion": "Ribera de Deusto 72, pabellón 3, 48014 Bilbao (dirección ficticia)",
           "horario": "L-V 9:00-18:00"}
CAMPANA = {"donaciones_desde": "1 de noviembre", "donaciones_hasta": "30 de diciembre",
           "entregas_hasta": "5 de enero"}
PLAZO_ELECCION_DIAS = 3

# --- Estados ---------------------------------------------------------------
ESTADOS_DONACION: dict[str, str] = {
    "registrada": "Registrada",
    "publicada": "Publicada en el catálogo",
    "rechazada_online": "No publicada (revisión online)",
    "emparejada": "Un niño lo ha elegido",
    "recogida_programada": "Recogida en casa programada",
    "llevar_a_punto": "Pendiente de dejar en el punto",
    "recibida": "En el local de GUBI",
    "revisada": "Revisión física superada",
    "asignada": "Asignada",
    "entregada": "Entregada",
    "rechazada": "No superó la revisión física",
    "retirada": "Match anulado (sin respuesta)",
}
RUTA_DONACION = ["registrada", "publicada", "emparejada", "recogida_programada", "recibida", "revisada", "entregada"]
RUTA_LOTE = ["registrada", "recogida_programada", "recibida", "revisada", "publicada", "asignada", "entregada"]

TRANSICIONES_PARTICULAR: dict[str, list[str]] = {
    "registrada": ["publicada", "rechazada_online"],          # revisión online
    "publicada": ["emparejada"],                              # automática al reservar
    "emparejada": ["recogida_programada", "llevar_a_punto", "retirada", "publicada"],
    "recogida_programada": ["recibida", "publicada"],
    "llevar_a_punto": ["recibida", "publicada"],
    "recibida": ["revisada", "rechazada"],                    # revisión física
    "revisada": ["entregada"],
    "entregada": [], "rechazada": [], "rechazada_online": [], "retirada": [],
}
TRANSICIONES_LOTE: dict[str, list[str]] = {
    "registrada": ["recogida_programada", "recibida"],
    "recogida_programada": ["recibida"],
    "recibida": ["revisada", "rechazada"],
    "revisada": ["publicada"],
    "publicada": ["asignada"],
    "asignada": ["entregada", "publicada"],
    "entregada": [], "rechazada": [],
}
# Transiciones que el equipo puede pulsar a mano en Operaciones (las demás tienen su pantalla o son automáticas)
MANUALES_DONACION = {("registrada", "recogida_programada"), ("registrada", "recibida"),
                     ("recogida_programada", "recibida"), ("llevar_a_punto", "recibida"), ("revisada", "publicada")}

ESTADOS_PEDIDO: dict[str, str] = {
    "solicitado": "Reservado",
    "en_recogida": "GUBI recoge el juguete",
    "revisado": "Revisión física superada",
    "preparado": "Preparado",
    "en_camino": "En camino",
    "listo_punto": "Listo en el punto",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
    "sustituido": "Sustituido por otro juguete",
}
RUTA_PEDIDO = ["solicitado", "en_recogida", "revisado", "preparado", "en_camino", "entregado"]
TRANSICIONES_PEDIDO: dict[str, list[str]] = {
    "solicitado": ["en_recogida", "revisado", "cancelado", "sustituido"],
    "en_recogida": ["revisado", "cancelado", "sustituido"],
    "revisado": ["preparado", "cancelado"],
    "preparado": ["en_camino", "listo_punto", "cancelado"],
    "en_camino": ["entregado", "cancelado"],
    "listo_punto": ["entregado", "cancelado"],
    "entregado": [], "cancelado": [], "sustituido": [],
}
# Estados del pedido que provoca la donación (no se pulsan en el panel)
AUTOMATICOS_PEDIDO = {"en_recogida", "revisado", "sustituido"}
ACTIVOS_PEDIDO = ("solicitado", "en_recogida", "revisado", "preparado", "en_camino", "listo_punto")

SIGUIENTE_PASO = {
    "registrada": "Revisaremos las fotos y la descripción en 24-48 h. Si todo está bien, lo publicaremos en el catálogo.",
    "publicada": "Tu juguete sigue en tu casa. Cuando un niño lo elija te avisaremos por email o WhatsApp.",
    "rechazada_online": "No lo hemos publicado. Te contamos el motivo arriba.",
    "emparejada": f"Elige en {PLAZO_ELECCION_DIAS} días si GUBI lo recoge en tu casa (gratis) o si lo dejas en un punto.",
    "recogida_programada": "GUBI pasará a recogerlo en la franja que elegiste y lo llevará a su local.",
    "llevar_a_punto": "Déjalo en el punto elegido en su horario. GUBI lo llevará a su local.",
    "recibida": "Está en el local de GUBI. Ahora pasará la revisión física (seguridad, piezas y estado).",
    "revisada": "Ha superado la revisión física. GUBI lo prepara para entregarlo.",
    "asignada": "Ya tiene destino: GUBI lo está preparando para la entrega.",
    "entregada": "¡Listo! Gracias por darle una segunda vida.",
    "rechazada": "No ha superado la revisión física. El niño recibirá otro juguete parecido.",
    "retirada": "Como no recibimos respuesta en 3 días, el niño recibirá otro juguete parecido.",
    "solicitado": "Antes de entregarlo, GUBI lo recogerá del donante y lo revisará físicamente en su local.",
    "en_recogida": "GUBI está recogiendo el juguete y lo revisará en su local antes de prepararlo.",
    "revisado": "Ha superado la revisión física. GUBI lo preparará para la entrega.",
    "preparado": "Saldrá hacia el domicilio o quedará listo en el punto de encuentro.",
    "en_camino": "GUBI lo entregará en la franja indicada.",
    "listo_punto": "Puedes pasar a recogerlo en el punto de encuentro en su horario.",
    "entregado": "Entregado. ¡Que lo disfrute!",
    "cancelado": "El pedido se ha cancelado y el juguete vuelve a estar disponible.",
    "sustituido": "Este juguete no ha podido entregarse; te hemos asignado otro parecido.",
}
SIGUIENTE_PASO_LOTE = {
    "registrada": "GUBI os contactará para confirmar la recogida del lote.",
    "recibida": "El lote está en el local de GUBI. Ahora pasará la revisión física.",
    "revisada": "Ha superado la revisión. Lo publicaremos en el catálogo.",
    "publicada": "Las unidades están en el catálogo esperando a su niño o entidad.",
    "rechazada": "El lote no ha superado la revisión. Os contamos el motivo arriba.",
}


class TransicionInvalida(ValueError):
    pass


def ruta_donacion(tipo: str) -> list[str]:
    return list(RUTA_LOTE if tipo == "empresa" else RUTA_DONACION)


def transiciones_donacion(don: dict) -> list[str]:
    tabla = TRANSICIONES_LOTE if don["tipo"] == "empresa" else TRANSICIONES_PARTICULAR
    return tabla.get(don["estado"], [])


def siguiente_paso(estado: str, tipo: str = "particular") -> str:
    if tipo == "empresa" and estado in SIGUIENTE_PASO_LOTE:
        return SIGUIENTE_PASO_LOTE[estado]
    return SIGUIENTE_PASO.get(estado, "")


# --- Notificaciones --------------------------------------------------------
def _config_smtp() -> dict | None:
    try:
        import streamlit as st

        cfg = st.secrets.get("smtp")
        if cfg and cfg.get("host") and cfg.get("usuario"):
            return dict(cfg)
    except Exception:  # noqa: BLE001 - sin secrets o fuera de Streamlit
        return None
    return None


def notificar(destinatario: str | None, asunto: str, cuerpo: str, objeto: str = "") -> int:
    """Encola siempre el email en la bandeja de salida; lo envía por SMTP solo si hay credenciales."""
    destinatario = destinatario or "equipo@fabricadebaltasares.example"
    estado = "En bandeja (SMTP no configurado)"
    cfg = _config_smtp()
    if cfg:
        try:
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = asunto, cfg.get("remitente", cfg["usuario"]), destinatario
            msg.set_content(cuerpo)
            with smtplib.SMTP(cfg["host"], int(cfg.get("puerto", 587)), timeout=10) as s:
                s.starttls()
                s.login(cfg["usuario"], cfg["contrasena"])
                s.send_message(msg)
            estado = "Enviado"
        except Exception as e:  # noqa: BLE001
            estado = f"Error de envío: {type(e).__name__}"
    return db.insertar("notificaciones", {"destinatario": destinatario, "asunto": asunto, "cuerpo": cuerpo,
                                          "estado": estado, "objeto": objeto, "creado": db.ahora()})


def _avisar_donante(don: dict, asunto: str, cuerpo: str) -> None:
    """Email al donante y, si dejó teléfono, también un WhatsApp (simulado: queda en la bandeja de salida)."""
    if don.get("email"):
        notificar(don["email"], asunto, cuerpo, don["codigo"])
    if don.get("telefono"):
        db.insertar("notificaciones", {"destinatario": f"WhatsApp {don['telefono']}", "asunto": asunto,
                                       "cuerpo": cuerpo, "estado": "WhatsApp simulado (no se envía)",
                                       "objeto": don["codigo"], "creado": db.ahora()})


def _historial(objeto: str, objeto_id: int, estado: str, nota: str = "", fecha: str | None = None) -> None:
    db.insertar("historial", {"objeto": objeto, "objeto_id": objeto_id, "estado": estado,
                              "fecha": fecha or db.ahora(), "nota": nota})


def historial(objeto: str, objeto_id: int) -> list[dict]:
    return db.consulta("SELECT * FROM historial WHERE objeto = ? AND objeto_id = ? ORDER BY fecha, id",
                       (objeto, objeto_id))


def _donacion(don_id: int | None) -> dict | None:
    return db.uno("SELECT * FROM donaciones WHERE id = ?", (don_id,)) if don_id else None


def fecha_corta(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y a las %H:%M")
    except ValueError:
        return iso


# --- Donaciones ------------------------------------------------------------
def crear_donacion_particular(juguete: dict, email: str, fotos: list[str], barrio_id: int = 1,
                              telefono: str = "") -> dict:
    """Crea la donación y el juguete pendientes de la revisión online. El juguete se queda en casa del donante."""
    codigo = db.nuevo_codigo("FB-DON", "donaciones")
    don_id = db.insertar("donaciones", {
        "codigo": codigo, "tipo": "particular", "email": email, "telefono": telefono or None,
        "punto_id": barrio_id, "estado": "registrada", "creado": db.ahora()})
    db.insertar("juguetes", {
        "nombre": juguete["nombre"], "descripcion": juguete["descripcion"], "categoria": juguete["categoria"],
        "edad_min": juguete["edad_min"], "edad_max": juguete["edad_max"],
        "intereses": db.a_json(juguete["intereses"]), "restricciones": db.a_json(juguete["restricciones"]),
        "estado_fisico": juguete["estado_fisico"], "punto_id": barrio_id or 1,
        "peso_kg": juguete.get("peso_kg", 0.6), "fotos": db.a_json(fotos), "estado": "en_revision",
        "donacion_id": don_id, "creado": db.ahora()})
    _historial("donacion", don_id, "registrada", "Donación registrada desde la web")
    _avisar_donante(db.uno("SELECT * FROM donaciones WHERE id = ?", (don_id,)),
                    f"Hemos registrado tu donación {codigo}",
                    f"¡Gracias! Hemos registrado tu juguete «{juguete['nombre']}».\n\nCódigo de seguimiento: {codigo}\n"
                    "Revisaremos las fotos en 24-48 h y, si todo está bien, lo publicaremos en el catálogo.\n"
                    "No tienes que llevarlo a ningún sitio: cuando un niño lo elija te avisaremos para que decidas si "
                    "GUBI lo recoge en tu casa (gratis) o si lo dejas en un punto de recogida.\n\n"
                    "La Fábrica de Baltasares · Logística: GUBI")
    return {"id": don_id, "codigo": codigo}


def crear_donacion_empresa(datos: dict) -> dict:
    codigo = db.nuevo_codigo("FB-DON", "donaciones")
    don_id = db.insertar("donaciones", {
        "codigo": codigo, "tipo": "empresa", "email": datos["email"], "entrega_modo": "recogida_empresa",
        "empresa_nombre": datos["empresa"], "contacto": datos["contacto"], "producto": datos["producto"],
        "unidades": datos["unidades"], "edad_texto": datos["edad"], "motivo": datos["motivo"],
        "fecha_preferida": datos["fecha"], "estado": "registrada", "creado": db.ahora()})
    _historial("donacion", don_id, "registrada", f"Lote de empresa: {datos['unidades']} uds.")
    notificar(datos["email"], f"Lote registrado {codigo}",
              f"Hola, {datos['contacto']}:\n\nHemos registrado vuestro lote de «{datos['producto']}» "
              f"({datos['unidades']} unidades aprox.).\nCódigo de seguimiento: {codigo}\nGUBI os contactará para "
              f"confirmar la recogida en torno al {datos['fecha']} y lo revisará en su local antes de publicarlo.\n\n"
              "Gracias por colaborar.", codigo)
    return {"id": don_id, "codigo": codigo}


MENSAJES_DONANTE = {
    "publicada": "Tu juguete ha superado la revisión online y ya está publicado en el catálogo. Sigue en tu casa: "
                 "te avisaremos cuando un niño lo elija.",
    "recogida_programada": "Hemos programado con GUBI la recogida de tu juguete en tu casa.",
    "llevar_a_punto": "Perfecto: puedes dejar tu juguete en el punto elegido en su horario.",
    "recibida": "Tu juguete ya está en el local de GUBI. Ahora pasará la revisión física.",
    "revisada": "Tu juguete ha superado la revisión física. ¡Pronto llegará a su nuevo dueño!",
    "asignada": "¡Vuestro juguete ya tiene destino! GUBI lo está preparando.",
    "entregada": "Tu juguete ya tiene nuevo dueño. Gracias por darle una segunda vida.",
}


def cambiar_estado_donacion(don_id: int, nuevo: str, nota: str = "", manual: bool = False,
                            mensaje: str | None = None) -> None:
    don = _donacion(don_id)
    if not don:
        raise TransicionInvalida("La donación no existe.")
    actual = don["estado"]
    if nuevo not in transiciones_donacion(don):
        raise TransicionInvalida(f"No se puede pasar de «{ESTADOS_DONACION[actual]}» a «{ESTADOS_DONACION[nuevo]}».")
    if manual and (actual, nuevo) not in MANUALES_DONACION:
        raise TransicionInvalida("Este cambio lo hace el sistema automáticamente.")
    cambios = {"estado": nuevo}
    if nuevo in ("rechazada", "rechazada_online"):
        cambios["motivo_rechazo"] = nota
    db.actualizar("donaciones", don_id, cambios)
    _historial("donacion", don_id, nuevo, nota)
    if nuevo == "publicada":
        db.ejecutar("UPDATE juguetes SET estado = 'publicado' WHERE donacion_id = ? AND estado = 'en_revision'", (don_id,))
    if nuevo in ("rechazada", "rechazada_online"):
        db.ejecutar("UPDATE juguetes SET estado = 'rechazado' WHERE donacion_id = ?", (don_id,))
    if nuevo == "retirada":
        db.ejecutar("UPDATE juguetes SET estado = 'retirado' WHERE donacion_id = ?", (don_id,))
    if mensaje is None:
        if nuevo == "rechazada_online":
            mensaje = f"Hemos revisado las fotos de tu juguete y no podemos publicarlo. Motivo: {nota or 'no indicado'}."
        elif nuevo == "rechazada":
            mensaje = (f"Lo sentimos, tu juguete no ha superado la revisión física en el local de GUBI. "
                       f"Motivo: {nota or 'no indicado'}.")
        else:
            mensaje = MENSAJES_DONANTE.get(nuevo, "")
    if mensaje:
        _avisar_donante(don, f"{don['codigo']}: {ESTADOS_DONACION[nuevo]}",
                        f"{mensaje}\n\nCódigo: {don['codigo']}\nLa Fábrica de Baltasares")


def revisar_online(don_id: int, aprobar: bool, motivo: str = "", etiquetas: dict | None = None) -> None:
    """Primera revisión: el equipo mira las fotos y la descripción antes de publicar el juguete."""
    if aprobar and etiquetas:
        _actualizar_etiquetas(don_id, etiquetas)
    if aprobar:
        cambiar_estado_donacion(don_id, "publicada", motivo or "Revisión online de las fotos superada")
    else:
        cambiar_estado_donacion(don_id, "rechazada_online", motivo)


def _actualizar_etiquetas(don_id: int, e: dict) -> None:
    db.ejecutar("UPDATE juguetes SET categoria = ?, edad_min = ?, edad_max = ?, intereses = ?, restricciones = ? "
                "WHERE donacion_id = ?", (e["categoria"], e["edad_min"], e["edad_max"], db.a_json(e["intereses"]),
                                          db.a_json(e["restricciones"]), don_id))


def pedido_activo_de_donacion(don_id: int) -> dict | None:
    marcas = ",".join("?" for _ in ACTIVOS_PEDIDO)
    return db.uno(f"SELECT p.* FROM pedidos p JOIN juguetes j ON j.id = p.juguete_id WHERE j.donacion_id = ? "
                  f"AND p.estado IN ({marcas}) ORDER BY p.id DESC", (don_id, *ACTIVOS_PEDIDO))


def _emparejar(don: dict) -> None:
    """Match: avisa al donante, que tiene 3 días para elegir recogida en casa o punto."""
    plazo = (datetime.now() + timedelta(days=PLAZO_ELECCION_DIAS)).isoformat(timespec="seconds")
    db.actualizar("donaciones", don["id"], {"plazo_eleccion": plazo})
    j = db.uno("SELECT nombre FROM juguetes WHERE donacion_id = ?", (don["id"],))
    cambiar_estado_donacion(
        don["id"], "emparejada", "Un niño ha elegido el juguete",
        mensaje=(f"¡Buenas noticias! Un niño ha elegido tu juguete «{j['nombre'] if j else ''}».\n\n"
                 f"Tienes hasta el {fecha_corta(plazo)} para elegir cómo nos lo das:\n"
                 "· Que GUBI lo recoja en tu casa (gratis), o\n· Dejarlo en uno de los puntos de recogida.\n\n"
                 f"Entra en «Seguimiento» con tu código {don['codigo']} y elige la opción que prefieras. "
                 "Si no recibimos respuesta en ese plazo, asignaremos al niño otro juguete parecido."))


def elegir_entrega(don_id: int, entrega: dict) -> None:
    """El donante elige, tras el match, recogida en casa (gratis) o dejarlo en un punto."""
    don = _donacion(don_id)
    if not don or don["estado"] != "emparejada":
        raise TransicionInvalida("Esta donación no está esperando tu elección.")
    domicilio = entrega["modo"] == "domicilio"
    db.actualizar("donaciones", don_id, {"entrega_modo": entrega["modo"], "punto_id": entrega.get("punto_id"),
                                         "direccion": entrega.get("direccion") if domicilio else None,
                                         "franja_horaria": entrega.get("franja") if domicilio else None})
    if domicilio:
        cambiar_estado_donacion(don_id, "recogida_programada", f"Recogida en casa · {entrega.get('franja', '')}",
                                mensaje=f"Hemos programado con GUBI la recogida gratuita de tu juguete en tu casa "
                                        f"({entrega.get('franja', '')}). Después lo llevaremos a su local para la "
                                        "revisión física.")
    else:
        punto = db.uno("SELECT * FROM puntos WHERE id = ?", (entrega.get("punto_id"),))
        cambiar_estado_donacion(don_id, "llevar_a_punto", f"Lo dejará en {punto['nombre'] if punto else 'un punto'}",
                                mensaje=f"Perfecto: puedes dejar tu juguete en {punto['nombre']} ({punto['horario']}). "
                                        "GUBI lo llevará después a su local para la revisión física." if punto else None)
    ped = pedido_activo_de_donacion(don_id)
    if ped and ped["estado"] == "solicitado":
        cambiar_estado_pedido(ped["id"], "en_recogida", "El donante ha elegido cómo entregarlo")


def revisar_fisica(don_id: int, aprobar: bool, motivo: str = "", etiquetas: dict | None = None,
                   unidades: int | None = None) -> dict | None:
    """Segunda revisión, en el local de GUBI. Si falla y había un niño esperando, se le asigna otro parecido."""
    don = _donacion(don_id)
    if not don:
        raise TransicionInvalida("La donación no existe.")
    if not aprobar:
        cambiar_estado_donacion(don_id, "rechazada", motivo)
        ped = pedido_activo_de_donacion(don_id)
        return sustituir_pedido(ped["id"], f"no ha superado la revisión física ({motivo.lower()})") if ped else None
    if don["tipo"] == "empresa" and unidades:
        e = etiquetas or {}
        for _ in range(min(int(unidades), 60)):
            db.insertar("juguetes", {
                "nombre": e.get("nombre", don["producto"]), "descripcion": e.get("descripcion", don["producto"]),
                "categoria": e["categoria"], "edad_min": e["edad_min"], "edad_max": e["edad_max"],
                "intereses": db.a_json(e["intereses"]), "restricciones": db.a_json(e["restricciones"]),
                "estado_fisico": "Fuera de catálogo" if "catálogo" in (don["motivo"] or "") else "Tara estética",
                "punto_id": 1, "peso_kg": e.get("peso_kg", 0.5), "fotos": "[]", "estado": "en_revision",
                "donacion_id": don_id, "creado": db.ahora()})
    elif etiquetas:
        _actualizar_etiquetas(don_id, etiquetas)
    cambiar_estado_donacion(don_id, "revisada", motivo or "Revisión física de GUBI superada")
    ped = pedido_activo_de_donacion(don_id)
    if ped and ped["estado"] in ("solicitado", "en_recogida"):
        cambiar_estado_pedido(ped["id"], "revisado", "Revisión física superada en el local de GUBI")
    return None


def aceptar_revision(don_id: int, etiquetas: dict | None = None, unidades: int | None = None, nota: str = "") -> None:
    """Compatibilidad: revisión física superada."""
    revisar_fisica(don_id, True, nota, etiquetas, unidades)


def anular_match(don_id: int, nota: str = "Sin respuesta del donante en 3 días") -> dict | None:
    """El donante no eligió a tiempo: se retira su juguete y el niño recibe otro parecido."""
    cambiar_estado_donacion(don_id, "retirada", nota,
                            mensaje="Como no hemos recibido tu respuesta en 3 días, hemos anulado la reserva de tu "
                                    "juguete y el niño recibirá otro parecido. Si aún quieres donarlo, puedes volver "
                                    "a subirlo cuando quieras.")
    ped = pedido_activo_de_donacion(don_id)
    return sustituir_pedido(ped["id"], "no ha podido recogerse porque el donante no respondió a tiempo") if ped else None


def caducar_matches() -> int:
    """Anula los matches cuyo plazo de 3 días ha vencido. Se llama al cargar la web."""
    vencidas = db.consulta("SELECT id FROM donaciones WHERE estado = 'emparejada' AND plazo_eleccion IS NOT NULL "
                           "AND plazo_eleccion < ?", (db.ahora(),))
    for d in vencidas:
        try:
            anular_match(d["id"])
        except TransicionInvalida:
            pass
    return len(vencidas)


def sincronizar_donacion(don_id: int | None) -> None:
    """Lotes de empresa: deriva asignada/entregada/publicada a partir de sus juguetes."""
    don = _donacion(don_id)
    if not don or don["tipo"] != "empresa" or don["estado"] not in ("publicada", "asignada"):
        return
    estados = [f["estado"] for f in db.consulta("SELECT estado FROM juguetes WHERE donacion_id = ?", (don_id,))]
    if estados and all(e == "entregado" for e in estados):
        objetivo = "entregada"
    elif any(e in ("reservado", "entregado") for e in estados):
        objetivo = "asignada"
    else:
        objetivo = "publicada"
    if objetivo == don["estado"]:
        return
    if objetivo == "entregada" and don["estado"] == "publicada":
        cambiar_estado_donacion(don_id, "asignada")
    cambiar_estado_donacion(don_id, objetivo)


# --- Pedidos ---------------------------------------------------------------
def crear_pedido(juguete_id: int, destino: str, *, entidad_id: int | None = None, organizacion_id: int | None = None,
                 necesidad_id: int | None = None, carta_id: int | None = None, nino_ref: str | None = None,
                 familia_ref: str | None = None, edad: int | None = None, franja: str | None = None,
                 modo_entrega: str = "punto", punto_id: int | None = None, email: str | None = None,
                 nota: str = "") -> dict:
    """Reserva el juguete (si sigue disponible), crea el pedido y, si el juguete sigue en casa del donante, le avisa."""
    with db.conexion() as con:
        cur = con.execute("UPDATE juguetes SET estado = 'reservado' WHERE id = ? AND estado = 'publicado'", (juguete_id,))
        if cur.rowcount == 0:
            raise TransicionInvalida("Este juguete acaba de ser reservado por otra persona.")
    j = db.juguete(juguete_id)
    punto = db.uno("SELECT * FROM puntos WHERE id = ?", (punto_id or j["punto_id"],))
    codigo = db.nuevo_codigo("FB-PED", "pedidos")
    ped_id = db.insertar("pedidos", {
        "codigo": codigo, "juguete_id": juguete_id, "destino": destino, "entidad_id": entidad_id,
        "organizacion_id": organizacion_id, "necesidad_id": necesidad_id, "carta_id": carta_id, "nino_ref": nino_ref,
        "familia_ref": familia_ref, "edad": edad,
        "franja": franja or (db.franja_de_edad(edad) if edad is not None else None),
        "modo_entrega": modo_entrega, "punto_id": punto["id"] if punto else None,
        "barrio": punto["barrio"] if punto else None, "email": email, "estado": "solicitado",
        "campana_id": db.campana_para_asignar(), "creado": db.ahora()})
    db.actualizar("juguetes", juguete_id, {"campana_id": db.uno("SELECT campana_id FROM pedidos WHERE id = ?",
                                                                (ped_id,))["campana_id"]})
    _historial("pedido", ped_id, "solicitado", nota or f"Pedido creado ({destino})")

    # ¿En qué punto está el juguete físicamente?
    don = _donacion(j["donacion_id"])
    ya_revisado = not don or don["tipo"] == "empresa" or don["estado"] == "revisada"
    if don and don["tipo"] == "empresa":
        sincronizar_donacion(don["id"])
    elif don and don["estado"] == "publicada":
        _emparejar(don)
    elif don and don["estado"] in ("recogida_programada", "llevar_a_punto", "recibida"):
        db.actualizar("pedidos", ped_id, {"estado": "en_recogida"})
        _historial("pedido", ped_id, "en_recogida", "El juguete ya está de camino al local de GUBI")
    if ya_revisado:
        db.actualizar("pedidos", ped_id, {"estado": "revisado"})
        _historial("pedido", ped_id, "revisado", "El juguete ya ha pasado la revisión física en el local de GUBI")

    entrega = ("en tu domicilio" if modo_entrega == "domicilio" else f"en el punto {punto['nombre']}") if punto else ""
    antes = ("" if ya_revisado else "Antes de entregarlo, GUBI lo recogerá del donante y lo revisará físicamente "
             "en su local. Si no superase la revisión, te asignaremos otro juguete parecido.\n")
    notificar(email, f"Pedido {codigo} registrado",
              f"Hemos reservado «{j['nombre']}».\nCódigo de seguimiento: {codigo}\nEntrega prevista {entrega}, "
              f"antes del {CAMPANA['entregas_hasta']}.\n{antes}Te avisaremos en cada paso.\n\n"
              "La Fábrica de Baltasares · Logística: GUBI", codigo)
    return {"id": ped_id, "codigo": codigo}


def cambiar_estado_pedido(ped_id: int, nuevo: str, nota: str = "", aviso: str | None = None) -> None:
    ped = db.uno("SELECT * FROM pedidos WHERE id = ?", (ped_id,))
    if not ped:
        raise TransicionInvalida("El pedido no existe.")
    actual = ped["estado"]
    if nuevo not in TRANSICIONES_PEDIDO.get(actual, []):
        raise TransicionInvalida(f"No se puede pasar de «{ESTADOS_PEDIDO[actual]}» a «{ESTADOS_PEDIDO[nuevo]}».")
    db.actualizar("pedidos", ped_id, {"estado": nuevo})
    _historial("pedido", ped_id, nuevo, nota)
    j = db.juguete(ped["juguete_id"])
    don = _donacion(j["donacion_id"])
    if nuevo == "entregado":
        db.actualizar("juguetes", j["id"], {"estado": "entregado"})
        if don and don["tipo"] == "particular" and don["estado"] == "revisada":
            cambiar_estado_donacion(don["id"], "entregada", "Entregado a su nuevo dueño")
    elif nuevo == "cancelado":
        db.actualizar("juguetes", j["id"], {"estado": "publicado", "campana_id": None})
        if don and don["tipo"] == "particular" and don["estado"] in ("emparejada", "recogida_programada",
                                                                      "llevar_a_punto"):
            cambiar_estado_donacion(don["id"], "publicada", "Pedido cancelado: vuelve al catálogo",
                                    mensaje="La reserva de tu juguete se ha cancelado. Sigue publicado en el catálogo "
                                            "y te avisaremos si otro niño lo elige.")
    if don and don["tipo"] == "empresa":
        sincronizar_donacion(don["id"])
    notificar(ped["email"], f"{ped['codigo']}: {ESTADOS_PEDIDO[nuevo]}",
              aviso or (f"Tu pedido de «{j['nombre']}» está ahora: {ESTADOS_PEDIDO[nuevo]}.\n{SIGUIENTE_PASO[nuevo]}"
                        f"\n\nCódigo: {ped['codigo']}\nLa Fábrica de Baltasares"), ped["codigo"])


def _buscar_parecido(ped: dict, original: dict) -> dict | None:
    """Juguete publicado más parecido al que no se ha podido entregar (misma edad, intereses y restricciones)."""
    from core import matching

    if ped["edad"] is not None:
        edad = int(ped["edad"])
    else:
        edad = db.FRANJAS.get(ped["franja"] or "", (6, 8))[0]
    carta = db.uno("SELECT * FROM cartas WHERE id = ?", (ped["carta_id"],)) if ped["carta_id"] else None
    intereses = list(dict.fromkeys(original["intereses"] + (db.de_json(carta["intereses"]) if carta else [])))
    stock = db.juguetes_publicados()
    if ped["necesidad_id"]:
        nec = db.uno("SELECT restricciones FROM necesidades WHERE id = ?", (ped["necesidad_id"],))
        requeridas = set(db.de_json(nec["restricciones"])) if nec else set()
        stock = [s for s in stock if requeridas <= set(s["restricciones"])]
    res = matching.proponer({"edad": edad, "intereses": intereses, "categorias_preferidas": [original["categoria"]],
                             "rechazos": db.de_json(carta["rechazos"]) if carta else []},
                            stock, n=1, excluir={original["id"]})
    return res["propuestas"][0]["juguete"] if res["propuestas"] else None


def sustituir_pedido(ped_id: int, motivo: str) -> dict | None:
    """El juguete reservado no puede entregarse: se cierra el pedido y se reserva otro parecido para el mismo niño."""
    ped = db.uno("SELECT * FROM pedidos WHERE id = ?", (ped_id,))
    original = db.juguete(ped["juguete_id"])
    nuevo_j = _buscar_parecido(ped, original)
    nuevo = None
    if nuevo_j:
        try:
            nuevo = crear_pedido(nuevo_j["id"], ped["destino"], entidad_id=ped["entidad_id"],
                                 organizacion_id=ped["organizacion_id"], necesidad_id=ped["necesidad_id"],
                                 carta_id=ped["carta_id"], nino_ref=ped["nino_ref"], familia_ref=ped["familia_ref"],
                                 edad=ped["edad"], franja=ped["franja"], modo_entrega=ped["modo_entrega"],
                                 punto_id=ped["punto_id"], email=ped["email"],
                                 nota=f"Sustituye al pedido {ped['codigo']}")
        except TransicionInvalida:
            nuevo = None
    if nuevo:
        texto = (f"Lo sentimos: «{original['nombre']}» {motivo}.\n\nPara que el niño no se quede sin regalo le hemos "
                 f"asignado un juguete parecido: «{nuevo_j['nombre']}».\nNuevo código de seguimiento: "
                 f"{nuevo['codigo']}\n\nLa Fábrica de Baltasares")
        nota = f"Sustituido por {nuevo['codigo']} · {nuevo_j['nombre']}"
    else:
        texto = (f"Lo sentimos: «{original['nombre']}» {motivo}.\n\nAhora mismo no tenemos un juguete parecido "
                 "disponible. Seguimos buscando y os avisaremos en cuanto llegue uno.\n\nLa Fábrica de Baltasares")
        nota = "Sin sustituto disponible por ahora: queda en necesidades pendientes"
        if ped["entidad_id"]:
            db.insertar("avisos", {"entidad_id": ped["entidad_id"], "edad": ped["edad"],
                                   "interes": (original["intereses"] or ["cualquiera"])[0],
                                   "objeto": original["nombre"], "estado": "pendiente", "creado": db.ahora()})
    cambiar_estado_pedido(ped_id, "sustituido", nota, aviso=texto)
    return nuevo


def buscar_por_codigo(codigo: str) -> dict | None:
    """Devuelve {'tipo', 'registro', 'historial'} para FB-DON-… o FB-PED-…"""
    codigo = (codigo or "").strip().upper()
    if codigo.startswith("FB-DON"):
        r = db.uno("SELECT * FROM donaciones WHERE codigo = ?", (codigo,))
        return {"tipo": "donacion", "registro": r, "historial": historial("donacion", r["id"])} if r else None
    if codigo.startswith("FB-PED"):
        r = db.uno("SELECT * FROM pedidos WHERE codigo = ?", (codigo,))
        return {"tipo": "pedido", "registro": r, "historial": historial("pedido", r["id"])} if r else None
    return None
