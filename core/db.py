"""Acceso a SQLite: esquema, conexión y consultas con nombre."""
from __future__ import annotations

import json
import os
import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
UPLOADS = DATA / "uploads"

# Vocabulario cerrado de categorías (clave -> etiqueta visible)
CATEGORIAS: dict[str, str] = {
    "peluche": "Peluche",
    "construccion": "Construcción",
    "muneco": "Muñeco o figura",
    "vehiculo": "Vehículo",
    "juego_mesa": "Juego de mesa",
    "puzle": "Puzle",
    "libro": "Libro",
    "musica": "Música",
    "deporte": "Deporte y aire libre",
    "manualidades": "Manualidades",
    "bebe": "Bebé y sensorial",
    "disfraz": "Disfraz",
    "ciencia": "Ciencia y descubrimiento",
}

ESTADOS_FISICOS = ["Nuevo con caja", "Nuevo sin caja", "Fuera de catálogo", "Tara estética"]

RESTRICCIONES: dict[str, str] = {
    "sin_piezas_pequenas": "Sin piezas pequeñas",
    "facil_desinfectar": "Fácil de desinfectar",
    "sin_sonido": "Sin sonido",
    "sin_pilas": "Sin pilas",
    "movilidad_reducida": "Adaptado a movilidad reducida",
    "sensorial": "Sensorial",
}

LIMITE_POR_NINO = int(os.environ.get("FABRICA_LIMITE_NINO", "2"))

FRANJAS: dict[str, tuple[int, int]] = {
    "0-2": (0, 2), "3-5": (3, 5), "6-8": (6, 8), "9-12": (9, 12), "13+": (13, 17),
}


def franja_de_edad(edad: int) -> str:
    for nombre, (a, b) in FRANJAS.items():
        if a <= edad <= b:
            return nombre
    return "13+"


def ruta_db() -> Path:
    return Path(os.environ.get("FABRICA_DB", DATA / "fabrica.db"))


ESQUEMA = """
CREATE TABLE IF NOT EXISTS puntos (
  id INTEGER PRIMARY KEY, nombre TEXT, barrio TEXT, direccion TEXT, horario TEXT, lat REAL, lon REAL);
CREATE TABLE IF NOT EXISTS entidades (
  id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, nombre TEXT, tipo TEXT, email TEXT);
CREATE TABLE IF NOT EXISTS organizaciones (
  id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, nombre TEXT, tipo TEXT, contacto TEXT, email TEXT, barrio TEXT);
CREATE TABLE IF NOT EXISTS empresas (
  id INTEGER PRIMARY KEY, nombre TEXT, contacto TEXT, email TEXT, sector TEXT, ficticia INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS campanas (
  id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, nombre TEXT, empresa_id INTEGER, objetivo_juguetes INTEGER,
  aportacion REAL, fecha_inicio TEXT, fecha_fin TEXT, zona TEXT, estado TEXT, creado TEXT);
CREATE TABLE IF NOT EXISTS donaciones (
  id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, tipo TEXT, email TEXT, entrega_modo TEXT, punto_id INTEGER,
  direccion TEXT, franja_horaria TEXT, empresa_nombre TEXT, contacto TEXT, producto TEXT, unidades INTEGER,
  edad_texto TEXT, motivo TEXT, fecha_preferida TEXT, estado TEXT, motivo_rechazo TEXT, campana_id INTEGER,
  telefono TEXT, plazo_eleccion TEXT, demo INTEGER DEFAULT 0, creado TEXT);
CREATE TABLE IF NOT EXISTS juguetes (
  id INTEGER PRIMARY KEY, nombre TEXT, descripcion TEXT, categoria TEXT, edad_min INTEGER, edad_max INTEGER,
  intereses TEXT, restricciones TEXT, estado_fisico TEXT, punto_id INTEGER, peso_kg REAL, fotos TEXT,
  estado TEXT, donacion_id INTEGER, campana_id INTEGER, demo INTEGER DEFAULT 0, creado TEXT);
CREATE TABLE IF NOT EXISTS cartas (
  id INTEGER PRIMARY KEY, entidad_id INTEGER, nino_ref TEXT, edad INTEGER, texto_anon TEXT, intereses TEXT,
  categorias TEXT, rechazos TEXT, objetos TEXT, modo TEXT, demo INTEGER DEFAULT 0, creado TEXT);
CREATE TABLE IF NOT EXISTS pedidos (
  id INTEGER PRIMARY KEY, codigo TEXT UNIQUE, juguete_id INTEGER, destino TEXT, entidad_id INTEGER,
  organizacion_id INTEGER, necesidad_id INTEGER, carta_id INTEGER, nino_ref TEXT, familia_ref TEXT, edad INTEGER, franja TEXT,
  modo_entrega TEXT, punto_id INTEGER, barrio TEXT, email TEXT, estado TEXT, campana_id INTEGER,
  demo INTEGER DEFAULT 0, creado TEXT);
CREATE TABLE IF NOT EXISTS historial (
  id INTEGER PRIMARY KEY, objeto TEXT, objeto_id INTEGER, estado TEXT, fecha TEXT, nota TEXT);
CREATE TABLE IF NOT EXISTS notificaciones (
  id INTEGER PRIMARY KEY, destinatario TEXT, asunto TEXT, cuerpo TEXT, estado TEXT, objeto TEXT, creado TEXT);
CREATE TABLE IF NOT EXISTS costes (
  id INTEGER PRIMARY KEY, campana_id INTEGER, concepto TEXT, importe REAL, fecha TEXT, nota TEXT);
CREATE TABLE IF NOT EXISTS eventos (
  id INTEGER PRIMARY KEY, ts TEXT, sesion TEXT, src TEXT, publico TEXT, evento TEXT, objeto TEXT);
CREATE TABLE IF NOT EXISTS necesidades (
  id INTEGER PRIMARY KEY, organizacion_id INTEGER, nombre_entidad TEXT, tipo TEXT, contacto TEXT, email TEXT,
  codigo TEXT, ninos TEXT, categorias TEXT, restricciones TEXT, juguetes_por_nino INTEGER, fecha_limite TEXT,
  entrega TEXT, propuesta TEXT, estado TEXT, demo INTEGER DEFAULT 0, creado TEXT);
CREATE TABLE IF NOT EXISTS correcciones (
  id INTEGER PRIMARY KEY, necesidad_id INTEGER, juguete_id INTEGER, sustituto_id INTEGER, franja TEXT,
  accion TEXT, motivo TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS colaboraciones (
  id INTEGER PRIMARY KEY, empresa TEXT, contacto TEXT, email TEXT, tipo TEXT, aportacion REAL, zona TEXT,
  fechas TEXT, mensaje TEXT, estado TEXT, creado TEXT);
CREATE TABLE IF NOT EXISTS avisos (
  id INTEGER PRIMARY KEY, entidad_id INTEGER, edad INTEGER, interes TEXT, objeto TEXT, estado TEXT, creado TEXT);
CREATE TABLE IF NOT EXISTS contactos (
  id INTEGER PRIMARY KEY, origen TEXT, nombre TEXT, email TEXT, mensaje TEXT, creado TEXT);
"""


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


_CON_LOTE: sqlite3.Connection | None = None


@contextmanager
def lote() -> Iterator[None]:
    """Agrupa muchas escrituras en una sola transacción (carga de la semilla)."""
    global _CON_LOTE
    ruta = ruta_db()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _CON_LOTE = sqlite3.connect(ruta, timeout=15)
    _CON_LOTE.row_factory = sqlite3.Row
    try:
        yield
        _CON_LOTE.commit()
    finally:
        _CON_LOTE.close()
        _CON_LOTE = None


@contextmanager
def conexion() -> Iterator[sqlite3.Connection]:
    if _CON_LOTE is not None:
        yield _CON_LOTE
        return
    ruta = ruta_db()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta, timeout=15)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def consulta(sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
    with conexion() as con:
        return [dict(f) for f in con.execute(sql, params).fetchall()]


def uno(sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
    filas = consulta(sql, params)
    return filas[0] if filas else None


def ejecutar(sql: str, params: tuple | list = ()) -> int:
    with conexion() as con:
        cur = con.execute(sql, params)
        return cur.lastrowid


def insertar(tabla: str, datos: dict[str, Any]) -> int:
    cols = ", ".join(datos)
    marcas = ", ".join("?" for _ in datos)
    return ejecutar(f"INSERT INTO {tabla} ({cols}) VALUES ({marcas})", list(datos.values()))


def actualizar(tabla: str, id_: int, datos: dict[str, Any]) -> None:
    sets = ", ".join(f"{k} = ?" for k in datos)
    ejecutar(f"UPDATE {tabla} SET {sets} WHERE id = ?", [*datos.values(), id_])


def inicializar(forzar: bool = False) -> None:
    """Crea el esquema y carga la semilla si la base no existe (o si se fuerza)."""
    ruta = ruta_db()
    if not forzar and ruta.exists():
        # Base creada con el recorrido antiguo (revisión antes de publicar): se regenera la demo con el nuevo.
        with conexion() as con:
            columnas = {f[1] for f in con.execute("PRAGMA table_info(donaciones)").fetchall()}
        forzar = bool(columnas) and "plazo_eleccion" not in columnas
    if forzar and ruta.exists():
        ruta.unlink()
    nueva = not ruta.exists()
    UPLOADS.mkdir(parents=True, exist_ok=True)
    with conexion() as con:
        con.executescript(ESQUEMA)
    if nueva:
        from core import seed
        with lote():
            seed.cargar()


# --- Utilidades JSON -------------------------------------------------------
def a_json(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False)


def de_json(texto: str | None, defecto: Any = None) -> Any:
    if not texto:
        return [] if defecto is None else defecto
    try:
        return json.loads(texto)
    except (ValueError, TypeError):
        return [] if defecto is None else defecto


def nuevo_codigo(prefijo: str, tabla: str) -> str:
    """Código legible y único, p. ej. FB-DON-4827."""
    rnd = random.SystemRandom()
    while True:
        codigo = f"{prefijo}-{rnd.randint(1000, 9999)}"
        if not uno(f"SELECT id FROM {tabla} WHERE codigo = ?", (codigo,)):
            return codigo


# --- Consultas de dominio --------------------------------------------------
def juguete(id_: int) -> dict | None:
    j = uno("SELECT j.*, p.nombre AS punto_nombre, p.barrio AS barrio FROM juguetes j "
            "LEFT JOIN puntos p ON p.id = j.punto_id WHERE j.id = ?", (id_,))
    return _expandir_juguete(j) if j else None


def _expandir_juguete(j: dict) -> dict:
    j["intereses"] = de_json(j.get("intereses"))
    j["restricciones"] = de_json(j.get("restricciones"))
    j["fotos"] = de_json(j.get("fotos"))
    return j


def juguetes_publicados() -> list[dict]:
    """Stock disponible: publicados y no reservados."""
    filas = consulta("SELECT j.*, p.nombre AS punto_nombre, p.barrio AS barrio FROM juguetes j "
                     "LEFT JOIN puntos p ON p.id = j.punto_id WHERE j.estado = 'publicado' ORDER BY j.id")
    return [_expandir_juguete(f) for f in filas]


def puntos() -> list[dict]:
    return consulta("SELECT * FROM puntos ORDER BY id")


def entidad_por_codigo(codigo: str) -> dict | None:
    if not codigo:
        return None
    return uno("SELECT * FROM entidades WHERE UPPER(codigo) = UPPER(?)", (codigo.strip(),))


def organizacion_por_codigo(codigo: str) -> dict | None:
    if not codigo:
        return None
    return uno("SELECT * FROM organizaciones WHERE UPPER(codigo) = UPPER(?)", (codigo.strip(),))


def campana_por_codigo(codigo: str) -> dict | None:
    if not codigo:
        return None
    return uno("SELECT c.*, e.nombre AS empresa FROM campanas c LEFT JOIN empresas e ON e.id = c.empresa_id "
               "WHERE UPPER(c.codigo) = UPPER(?)", (codigo.strip(),))


def campanas() -> list[dict]:
    return consulta("SELECT c.*, e.nombre AS empresa FROM campanas c LEFT JOIN empresas e ON e.id = c.empresa_id "
                    "ORDER BY c.id")


def campana_para_asignar() -> int | None:
    """Campaña activa con menor avance relativo: así las entregas nuevas se reparten entre campañas."""
    filas = consulta(
        "SELECT c.id, c.objetivo_juguetes, (SELECT COUNT(*) FROM pedidos p WHERE p.campana_id = c.id "
        "AND p.estado != 'cancelado') AS n FROM campanas c WHERE c.estado = 'activa'")
    if not filas:
        return None
    filas.sort(key=lambda f: (f["n"] / max(f["objetivo_juguetes"] or 1, 1), f["id"]))
    return filas[0]["id"]


def juguetes_reservados_por_nino(nino_ref: str) -> int:
    fila = uno("SELECT COUNT(*) AS n FROM pedidos WHERE nino_ref = ? AND estado != 'cancelado'", (nino_ref,))
    return int(fila["n"]) if fila else 0
