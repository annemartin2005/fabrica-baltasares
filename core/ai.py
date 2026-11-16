"""Extracción de cartas y etiquetado de juguetes.

Con ANTHROPIC_API_KEY se usa la API de Anthropic; si no hay clave o la llamada falla,
se usa un extractor por reglas con diccionario de sinónimos en español. La demo nunca
depende de la IA.
"""
from __future__ import annotations

import base64
import json
import os
import re
import unicodedata
from typing import Any

from core.db import CATEGORIAS, RESTRICCIONES

# --- Vocabulario cerrado de intereses (40) y sus sinónimos -----------------
# Los patrones se aplican sobre texto normalizado (minúsculas, sin tildes).
INTERESES: dict[str, list[str]] = {
    "dinosaurios": [r"dino\w*", r"tiranosaur\w*", r"t-?rex", r"diplodoc\w*", r"triceratop\w*", r"dinosarios?"],
    "coches": [r"coche\w*", r"cochecit\w*", r"carro\w*", r"camion\w*", r"excavador\w*", r"tractor\w*", r"garaje\w*", r"moto\w*"],
    "trenes": [r"tren\w*", r"locomotor\w*", r"vias? de tren"],
    "aviones": [r"avion\w*", r"avioneta\w*", r"helicopter\w*", r"aeropuert\w*"],
    "barcos": [r"barco\w*", r"barquit\w*", r"submarin\w*", r"velero\w*"],
    "espacio": [r"espacio", r"espacial\w*", r"cohete\w*", r"planeta\w*", r"astronaut\w*", r"estrellas", r"luna", r"galaxia\w*", r"telescopi\w*", r"sistema solar"],
    "animales": [r"animal\w*", r"perr\w*", r"gat[oa]s?", r"gatit\w*", r"caball\w*", r"leon\w*", r"elefant\w*", r"jirafa\w*", r"oso\b", r"osos\b", r"osit\w*", r"conej\w*", r"unicorni\w*"],
    "granja": [r"granja\w*", r"vaca\w*", r"oveja\w*", r"cerdit\w*", r"gallina\w*"],
    "mar": [r"\bmar\b", r"tiburon\w*", r"ballena\w*", r"delfin\w*", r"pez\b", r"peces", r"pulpo\w*", r"playa\w*"],
    "naturaleza": [r"naturaleza", r"bicho\w*", r"insecto\w*", r"mariposa\w*", r"planta\w*", r"flor\b", r"flores", r"jardin\w*", r"arbol\w*"],
    "música": [r"music\w*", r"cancion\w*", r"cantar", r"guitarra\w*", r"piano\w*", r"tambor\w*", r"xilofon\w*", r"flauta\w*", r"bateria musical", r"instrument\w*"],
    "baile": [r"baila\w*", r"baile\w*", r"danza\w*", r"ballet"],
    "dibujo": [r"dibuj\w*", r"pinta\w*", r"pintur\w*", r"colorea\w*", r"rotulador\w*", r"lapices", r"ceras", r"acuarela\w*", r"pizarra\w*"],
    "manualidades": [r"manualidad\w*", r"plastilina\w*", r"pulsera\w*", r"abalorio\w*", r"recortar", r"pegatina\w*", r"arcilla", r"slime"],
    "cocina": [r"cocin\w*", r"cocinit\w*", r"comidita\w*", r"chef", r"pastel\w*", r"tarta\w*"],
    "fútbol": [r"futbol\w*", r"balon\w*", r"pelota de futbol", r"porteri\w*", r"gol\b", r"goles"],
    "baloncesto": [r"baloncesto", r"canasta\w*", r"basket"],
    "deporte": [r"deporte\w*", r"pelota\w*", r"patin\w*", r"patinete\w*", r"comba\w*", r"raqueta\w*", r"cometa\w*", r"correr", r"monopatin\w*", r"skate"],
    "bicicleta": [r"bici\w*", r"triciclo\w*"],
    "construcción": [r"construc\w*", r"bloque\w*", r"piezas para montar", r"montar", r"ladrillo\w*", r"torre\w*", r"encaj\w*"],
    "muñecos": [r"muñec\w*", r"munec\w*", r"figura\w*", r"casita\w*", r"casa de munecas"],
    "peluches": [r"peluch\w*", r"blandit\w*", r"achuchable\w*"],
    "ciencia": [r"ciencia\w*", r"cientific\w*", r"experiment\w*", r"microscopi\w*", r"quimic\w*", r"laboratori\w*", r"iman\w*", r"lupa\w*"],
    "lectura": [r"libro\w*", r"cuento\w*", r"leer", r"lectura", r"historias", r"comic\w*", r"tebeo\w*"],
    "disfraces": [r"disfra\w*", r"vestirme de", r"capa\w*", r"careta\w*", r"antifaz\w*"],
    "puzles": [r"puzzl\w*", r"puzl\w*", r"rompecabeza\w*"],
    "juegos de mesa": [r"juegos? de mesa", r"parchis", r"oca\b", r"domino\w*", r"cartas", r"baraja\w*", r"ajedrez", r"tablero\w*"],
    "magia": [r"magia", r"magic\w*", r"mago\w*", r"truco\w*"],
    "robots": [r"robot\w*", r"programar", r"programacion"],
    "fantasía": [r"princes\w*", r"hada\w*", r"dragon\w*", r"castillo\w*", r"sirena\w*", r"brujas?", r"fantasia"],
    "superhéroes": [r"superheroe\w*", r"super heroe\w*", r"heroe\w*", r"poderes"],
    "piratas": [r"pirata\w*", r"tesoro\w*"],
    "caballeros": [r"caballero\w*", r"espada\w*", r"escudo\w*", r"armadura\w*", r"vikingo\w*"],
    "oficios": [r"medic\w*", r"doctor\w*", r"bombero\w*", r"policia\w*", r"veterinari\w*", r"herramienta\w*", r"maletin\w*", r"tienda\w*", r"supermercado\w*"],
    "números": [r"numero\w*", r"contar", r"matematica\w*", r"sumar", r"letras", r"abecedario"],
    "bebés": [r"bebe\w*", r"carrito\w*", r"biberon\w*", r"cuidar"],
    "sensorial": [r"sensorial\w*", r"textura\w*", r"sonajer\w*", r"mordedor\w*", r"luces"],
    "agua": [r"agua", r"piscina\w*", r"banera\w*", r"nadar"],
    "marionetas": [r"marioneta\w*", r"titere\w*", r"teatro\w*", r"guiñol", r"guinol"],
    "exploración": [r"explora\w*", r"aventura\w*", r"brujula\w*", r"mapa\w*", r"prismatico\w*", r"detective\w*"],
}

# Intereses -> categorías de juguete que suelen encajar
INTERES_A_CATEGORIAS: dict[str, list[str]] = {
    "dinosaurios": ["muneco", "puzle"], "coches": ["vehiculo"], "trenes": ["vehiculo"], "aviones": ["vehiculo"],
    "barcos": ["vehiculo"], "espacio": ["ciencia"], "animales": ["peluche", "muneco"], "granja": ["muneco"],
    "mar": ["muneco"], "naturaleza": ["ciencia"], "música": ["musica"], "baile": ["musica"],
    "dibujo": ["manualidades"], "manualidades": ["manualidades"], "cocina": ["muneco"], "fútbol": ["deporte"],
    "baloncesto": ["deporte"], "deporte": ["deporte"], "bicicleta": ["deporte"], "construcción": ["construccion"],
    "muñecos": ["muneco"], "peluches": ["peluche"], "ciencia": ["ciencia"], "lectura": ["libro"],
    "disfraces": ["disfraz"], "puzles": ["puzle"], "juegos de mesa": ["juego_mesa"], "magia": ["juego_mesa"],
    "robots": ["ciencia", "construccion"], "fantasía": ["muneco", "disfraz"], "superhéroes": ["muneco", "disfraz"],
    "piratas": ["muneco", "disfraz"], "caballeros": ["muneco", "disfraz"], "oficios": ["disfraz", "muneco"],
    "números": ["puzle", "juego_mesa"], "bebés": ["muneco"], "sensorial": ["bebe"], "agua": ["deporte"],
    "marionetas": ["muneco"], "exploración": ["ciencia"],
}

# Intereses afines (para relajar sin perder el sentido de la carta)
AFINES: dict[str, list[str]] = {
    "espacio": ["ciencia", "exploración", "robots"], "ciencia": ["espacio", "exploración", "naturaleza"],
    "dinosaurios": ["animales", "exploración", "naturaleza"], "coches": ["trenes", "aviones", "construcción"],
    "trenes": ["coches", "construcción"], "aviones": ["coches", "espacio"], "barcos": ["mar", "piratas"],
    "fútbol": ["deporte", "baloncesto"], "baloncesto": ["deporte", "fútbol"], "deporte": ["fútbol", "bicicleta"],
    "bicicleta": ["deporte"], "dibujo": ["manualidades"], "manualidades": ["dibujo"], "música": ["baile"],
    "baile": ["música", "disfraces"], "animales": ["peluches", "granja", "naturaleza"], "peluches": ["animales"],
    "muñecos": ["bebés", "fantasía"], "bebés": ["muñecos"], "lectura": ["fantasía", "exploración"],
    "puzles": ["juegos de mesa", "números"], "juegos de mesa": ["puzles", "magia"], "robots": ["ciencia", "construcción"],
    "construcción": ["robots", "coches"], "disfraces": ["superhéroes", "fantasía", "piratas"],
    "superhéroes": ["disfraces"], "piratas": ["barcos", "disfraces"], "caballeros": ["fantasía", "disfraces"],
    "fantasía": ["muñecos", "disfraces"], "cocina": ["oficios"], "oficios": ["cocina", "disfraces"],
    "mar": ["animales", "barcos"], "granja": ["animales"], "naturaleza": ["ciencia", "animales"],
    "magia": ["juegos de mesa"], "números": ["puzles"], "sensorial": ["bebés"], "agua": ["mar"],
    "marionetas": ["muñecos", "lectura"], "exploración": ["ciencia", "naturaleza"],
}

# Objetos concretos que un niño puede pedir: si no hay ninguno en stock hay que decirlo
OBJETOS: dict[str, tuple[str, str]] = {
    r"telescopi\w*": ("telescopio", "espacio"), r"microscopi\w*": ("microscopio", "ciencia"),
    r"bicicleta\w*|\bbici\b|\bbicis\b": ("bicicleta", "bicicleta"), r"patinete\w*": ("patinete", "deporte"),
    r"guitarra\w*": ("guitarra", "música"), r"piano\w*": ("piano", "música"), r"tambor\w*": ("tambor", "música"),
    r"cocinit\w*": ("cocinita", "cocina"), r"pizarra\w*": ("pizarra", "dibujo"), r"casa de munecas": ("casa de muñecas", "muñecos"),
    r"dron\w*": ("dron", "robots"), r"cometa\w*": ("cometa", "deporte"), r"monopatin\w*|skate": ("monopatín", "deporte"),
    r"consola\w*|videojuego\w*|tablet\w*|movil\w*": ("aparato electrónico", ""),
}

PALABRAS_OBJETO = {"telescopio": ["telescopio"], "microscopio": ["microscopio"], "bicicleta": ["bicicleta", "bici"],
                   "patinete": ["patinete"], "guitarra": ["guitarra"], "piano": ["piano", "teclado"],
                   "tambor": ["tambor", "bateria"], "cocinita": ["cocinita", "cocina"], "pizarra": ["pizarra"],
                   "casa de muñecas": ["casa de munecas"], "dron": ["dron"], "cometa": ["cometa"],
                   "monopatín": ["monopatin"], "aparato electrónico": []}

NEGACIONES = r"\b(?:no\s+(?:me\s+)?(?:gusta|gustan|quiero|mola|molan)|nada\s+de|odio|no\s+(?:me\s+)?traig\w*|ni\s+hablar\s+de)\b"
CORTES = r"\b(?:pero|sino|aunque|me gusta|me gustan|quiero|me encanta\w*)\b|[.,;:!?]"

CATEGORIA_PALABRAS: dict[str, list[str]] = {
    "peluche": [r"peluch\w*", r"osit\w*", r"blandit\w*"],
    "construccion": [r"bloque\w*", r"construc\w*", r"piezas para montar", r"ladrillo\w*", r"encajable\w*", r"magnetic\w*"],
    "muneco": [r"muñec\w*", r"munec\w*", r"figura\w*", r"dinosaurio\w*", r"cocinit\w*", r"casita\w*", r"granja\w*", r"marioneta\w*", r"titere\w*"],
    "vehiculo": [r"coche\w*", r"camion\w*", r"tren\w*", r"avion\w*", r"garaje\w*", r"barco\w*", r"tractor\w*", r"excavador\w*"],
    "juego_mesa": [r"juego de mesa", r"parchis", r"domino\w*", r"cartas", r"tablero", r"memory", r"oca\b", r"magia"],
    "puzle": [r"puzl\w*", r"puzzl\w*", r"rompecabeza\w*"],
    "libro": [r"libro\w*", r"cuento\w*", r"album ilustrado", r"comic\w*"],
    "musica": [r"xilofon\w*", r"guitarra\w*", r"piano\w*", r"tambor\w*", r"instrument\w*", r"maraca\w*", r"musical\w*"],
    "deporte": [r"balon\w*", r"pelota\w*", r"patin\w*", r"comba\w*", r"raqueta\w*", r"canasta\w*", r"porteria\w*", r"cometa\w*", r"frisbee"],
    "manualidades": [r"manualidad\w*", r"plastilina\w*", r"pintura\w*", r"rotulador\w*", r"acuarela\w*", r"abalorio\w*", r"pizarra\w*", r"dibujo\w*"],
    "bebe": [r"bebe\w*", r"sonajer\w*", r"mordedor\w*", r"sensorial\w*", r"meses", r"apilable\w*", r"gimnasio"],
    "disfraz": [r"disfra\w*", r"capa\w*", r"antifaz\w*", r"careta\w*"],
    "ciencia": [r"ciencia\w*", r"experiment\w*", r"microscop\w*", r"lupa\w*", r"planetari\w*", r"cohete\w*", r"iman\w*", r"robot\w*", r"proyector de estrellas"],
}

EDAD_POR_CATEGORIA = {
    "peluche": (0, 8), "construccion": (4, 12), "muneco": (3, 10), "vehiculo": (3, 8), "juego_mesa": (6, 99),
    "puzle": (4, 12), "libro": (3, 10), "musica": (2, 8), "deporte": (5, 14), "manualidades": (5, 12),
    "bebe": (0, 2), "disfraz": (3, 10), "ciencia": (7, 14),
}

NOMBRES_COMUNES = {
    "lucas", "hugo", "martin", "daniel", "pablo", "alejandro", "mateo", "leo", "manuel", "alvaro", "mario", "diego",
    "javier", "adrian", "marcos", "david", "jon", "unai", "ander", "mikel", "asier", "iker", "aitor", "gorka", "eneko",
    "markel", "oier", "julen", "ibai", "aimar", "lucia", "sofia", "martina", "maria", "julia", "paula", "valeria",
    "emma", "daniela", "carla", "alba", "noa", "sara", "carmen", "laura", "ane", "nahia", "irati", "june", "uxue",
    "maialen", "ainhoa", "leire", "naroa", "amaia", "nora", "olivia", "chloe", "mohamed", "ahmed", "fatima", "aya",
    "yasmin", "omar", "adam", "ali", "ana", "juan", "jose", "pedro", "luis", "rosa", "elena", "miguel", "carlos",
}
NO_SON_NOMBRES = {
    "reyes", "magos", "melchor", "gaspar", "baltasar", "navidad", "queridos", "querido", "querida", "bilbao",
    "dios", "papa", "mama", "abuela", "abuelo", "hola", "gracias", "feliz", "yo", "me", "tengo", "quiero", "mi",
    "un", "una", "el", "la", "los", "las", "este", "esta", "por", "para", "y", "con", "de", "en", "que", "si",
}


def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn" or c == "̃")
    texto = unicodedata.normalize("NFC", texto).replace("ñ", "n")
    return texto


def _coincide(patrones: list[str], texto: str) -> bool:
    return any(re.search(rf"\b(?:{p})", texto) for p in patrones)


def _intereses_en(texto_norm: str) -> list[str]:
    # «Reyes Magos» y «Baltasar» son el destinatario de la carta, no un interés (magia)
    texto_norm = re.sub(r"\b(?:reyes|rey)\s+magos?\b|\bmagos de oriente\b", " ", texto_norm)
    return [i for i, pats in INTERESES.items() if _coincide(pats, texto_norm)]


def _rechazos_en(texto_norm: str) -> list[str]:
    rechazos: list[str] = []
    for m in re.finditer(NEGACIONES, texto_norm):
        resto = texto_norm[m.end():]
        corte = re.search(CORTES, resto)
        ventana = resto[: corte.start()] if corte else resto[:60]
        rechazos += [i for i in _intereses_en(ventana) if i not in rechazos]
    return rechazos


# --- Anonimización ---------------------------------------------------------
def anonimizar(texto: str) -> str:
    """Elimina emails, teléfonos, direcciones y nombres propios detectados."""
    if not texto:
        return ""
    t = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", texto)
    t = re.sub(r"(?:\+?34[\s-]?)?(?:\d[\s.-]?){8}\d", "[teléfono]", t)
    t = re.sub(r"(?i)\b(?:calle|c/|avenida|avda\.?|plaza|pza\.?|paseo|camino|travesía|travesia|barrio|portal|piso)\s+"
               r"[^\n,.;]{1,40}?(?:\s+n?º?\s*\d+[\w º/-]*)?(?=[,.;\n]|$)", "[dirección]", t)
    t = re.sub(r"(?i)\b(me llamo|mi nombre es|se llama)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)",
               lambda m: f"{m.group(1)} [nombre]", t)

    def _tras_presentacion(m: re.Match) -> str:
        palabra = m.group(2)
        es_nombre = palabra[0].isupper() or normalizar(palabra) in NOMBRES_COMUNES
        if es_nombre and normalizar(palabra) not in NO_SON_NOMBRES:
            return f"{m.group(1)} [nombre]"
        return m.group(0)

    t = re.sub(r"(?i)\b(soy|mi hermano|mi hermana|mi prima|mi primo)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)", _tras_presentacion, t)
    t = re.sub(r"(?i)\b(firmado|firma|un beso de|besos de|atentamente)[:,]?\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)",
               lambda m: f"{m.group(1)} [nombre]", t)

    def _sustituir(m: re.Match) -> str:
        palabra = m.group(0)
        n = normalizar(palabra)
        if n in NO_SON_NOMBRES:
            return palabra
        if n in NOMBRES_COMUNES:
            return "[nombre]"
        return palabra

    t = re.sub(r"\b[A-Za-zÁÉÍÓÚÑáéíóúñ]+\b", _sustituir, t)

    # Palabras con mayúscula en mitad de frase que no son vocabulario conocido
    def _mayus(m: re.Match) -> str:
        previo, palabra = m.group(1), m.group(2)
        n = normalizar(palabra)
        if n in NO_SON_NOMBRES or _intereses_en(n) or n in {normalizar(c) for c in CATEGORIAS.values()}:
            return m.group(0)
        return f"{previo}[nombre]"

    t = re.sub(r"([a-záéíóúñ,]\s+)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})\b", _mayus, t)
    return t


# --- IA (opcional) ---------------------------------------------------------
def ia_disponible() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _llamar_ia(sistema: str, usuario: str, imagen: bytes | None = None, tipo_imagen: str = "image/jpeg") -> dict | None:
    """Devuelve el JSON de la respuesta o None si no hay IA o falla."""
    if not ia_disponible():
        return None
    try:
        import anthropic

        cliente = anthropic.Anthropic(timeout=20.0, max_retries=1)
        contenido: list[dict[str, Any]] = []
        if imagen:
            contenido.append({"type": "image", "source": {"type": "base64", "media_type": tipo_imagen,
                                                          "data": base64.b64encode(imagen).decode()}})
        contenido.append({"type": "text", "text": usuario})
        respuesta = cliente.messages.create(
            model=os.environ.get("FABRICA_IA_MODELO", "claude-haiku-5-5"),
            max_tokens=700,
            system=sistema,
            messages=[{"role": "user", "content": contenido}],
        )
        texto = "".join(b.text for b in respuesta.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", texto, re.S)
        return json.loads(m.group(0)) if m else None
    except Exception:  # noqa: BLE001 - cualquier fallo de IA activa el respaldo
        return None


def _filtrar(lista: Any, vocabulario) -> list[str]:
    if not isinstance(lista, list):
        return []
    validos = set(vocabulario)
    return [x for x in dict.fromkeys(str(v).strip().lower() for v in lista) if x in validos]


# --- API pública -----------------------------------------------------------
def categorias_de(intereses: list[str]) -> list[str]:
    cats: list[str] = []
    for i in intereses:
        for c in INTERES_A_CATEGORIAS.get(i, []):
            if c not in cats:
                cats.append(c)
    return cats


def _extraer_reglas(texto: str, edad: int | None) -> dict:
    t = normalizar(texto)
    rechazos = _rechazos_en(t)
    intereses = [i for i in _intereses_en(t) if i not in rechazos]
    objetos = []
    for patron, (nombre, interes) in OBJETOS.items():
        if re.search(rf"\b(?:{patron})", t) and nombre not in objetos:
            objetos.append(nombre)
            if interes and interes not in intereses and interes not in rechazos:
                intereses.append(interes)
    if edad is None:
        m = re.search(r"tengo\s+(\d{1,2})\s+anos", t)
        edad = int(m.group(1)) if m else None
    return {"edad": edad, "intereses": intereses, "categorias_preferidas": categorias_de(intereses),
            "rechazos": rechazos, "objetos": objetos, "modo": "reglas"}


def extraer_carta(texto: str, edad: int | None) -> dict:
    """Interpreta una carta: edad, intereses (vocabulario cerrado), categorías, rechazos y objetos concretos."""
    base = _extraer_reglas(texto, edad)
    sistema = (
        "Eres un asistente que interpreta cartas a los Reyes Magos escritas por niños en español para un banco de "
        "juguetes solidario. Devuelve SOLO un JSON con las claves: intereses (lista), rechazos (lista), objetos "
        "(lista de objetos concretos pedidos, en singular). Usa únicamente estos intereses: "
        + ", ".join(INTERESES) + ". Ten en cuenta faltas de ortografía y diminutivos."
    )
    datos = _llamar_ia(sistema, f"Edad: {edad}. Carta: {texto}")
    if not datos:
        return base
    intereses = _filtrar(datos.get("intereses"), INTERESES)
    rechazos = _filtrar(datos.get("rechazos"), INTERESES)
    intereses = [i for i in intereses if i not in rechazos]
    objetos = [o for o in base["objetos"]]
    for o in datos.get("objetos", []) if isinstance(datos.get("objetos"), list) else []:
        o = str(o).lower().strip()
        if o in PALABRAS_OBJETO and o not in objetos:
            objetos.append(o)
    if not intereses:
        return base
    return {"edad": base["edad"], "intereses": intereses, "categorias_preferidas": categorias_de(intereses),
            "rechazos": rechazos, "objetos": objetos, "modo": "ia"}


def _edad_de_texto(t: str) -> tuple[int, int] | None:
    m = re.search(r"(\d{1,2})\s*(?:-|a|y)\s*(\d{1,2})\s*anos", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(?:\+|mas de|a partir de|desde)\s*(\d{1,2})\s*anos", t) or re.search(r"(\d{1,2})\s*\+", t)
    if m:
        a = int(m.group(1))
        return a, min(a + 8, 99)
    if re.search(r"\d+\s*meses|recien nacid|bebe", t):
        return 0, 2
    return None


def _etiquetar_reglas(nombre: str, descripcion: str) -> dict:
    t = normalizar(f"{nombre}. {descripcion}")
    puntos = {c: sum(1 for p in pats if re.search(rf"\b(?:{p})", t)) for c, pats in CATEGORIA_PALABRAS.items()}
    # el nombre pesa más que la descripción
    tn = normalizar(nombre)
    for c, pats in CATEGORIA_PALABRAS.items():
        puntos[c] += 2 * sum(1 for p in pats if re.search(rf"\b(?:{p})", tn))
    categoria = max(puntos, key=puntos.get) if max(puntos.values()) > 0 else "juego_mesa"
    edades = _edad_de_texto(t) or EDAD_POR_CATEGORIA[categoria]
    intereses = _intereses_en(t)[:5]
    if not intereses:
        intereses = [i for i, cats in INTERES_A_CATEGORIAS.items() if categoria in cats][:2]
    restricciones = []
    electronico = re.search(r"\bpilas?\b|bateri\w*|electronic\w*|\bluz\b|luces|\busb\b|recargable", t)
    sonido = re.search(r"sonido\w*|music\w*|suena|melodia\w*|ruido\w*|sonajer\w*|xilofon\w*|tambor\w*|maraca\w*", t)
    pequenas = re.search(r"piezas pequen\w*|canica\w*|abalorio\w*|cuenta\w*|imanes pequen\w*|\d{3,}\s*piezas", t)
    if not electronico:
        restricciones.append("sin_pilas")
    if not sonido and categoria != "musica":
        restricciones.append("sin_sonido")
    if (edades[0] <= 3 or re.search(r"piezas grandes|sin piezas pequen", t)) and not pequenas:
        restricciones.append("sin_piezas_pequenas")
    if re.search(r"plastico|silicona|lavable|madera|goma", t) and categoria not in ("peluche", "libro", "disfraz"):
        restricciones.append("facil_desinfectar")
    if categoria in ("libro", "juego_mesa", "puzle", "musica", "bebe", "manualidades") or "adaptad" in t:
        restricciones.append("movilidad_reducida")
    if categoria == "bebe" or re.search(r"sensorial|textura\w*", t):
        restricciones.append("sensorial")
    return {"categoria": categoria, "edad_min": int(edades[0]), "edad_max": int(edades[1]),
            "intereses": intereses, "restricciones_cumplidas": restricciones, "modo": "reglas"}


def etiquetar_juguete(nombre: str, descripcion: str, imagen: bytes | None = None,
                      tipo_imagen: str = "image/jpeg") -> dict:
    """Propone categoría, edades, intereses y restricciones que cumple un juguete."""
    base = _etiquetar_reglas(nombre, descripcion)
    sistema = (
        "Etiquetas juguetes donados para un banco de juguetes solidario. Devuelve SOLO un JSON con: categoria (una de: "
        + ", ".join(CATEGORIAS) + "), edad_min, edad_max (enteros), intereses (de esta lista: " + ", ".join(INTERESES)
        + "), restricciones_cumplidas (de: " + ", ".join(RESTRICCIONES) + "). Sé prudente con la seguridad: marca "
        "sin_piezas_pequenas solo si es evidente."
    )
    datos = _llamar_ia(sistema, f"Nombre: {nombre}\nDescripción: {descripcion}", imagen, tipo_imagen)
    if not datos or datos.get("categoria") not in CATEGORIAS:
        return base
    try:
        edad_min, edad_max = int(datos.get("edad_min", base["edad_min"])), int(datos.get("edad_max", base["edad_max"]))
    except (TypeError, ValueError):
        edad_min, edad_max = base["edad_min"], base["edad_max"]
    if not 0 <= edad_min <= edad_max <= 99:
        edad_min, edad_max = base["edad_min"], base["edad_max"]
    return {"categoria": datos["categoria"], "edad_min": edad_min, "edad_max": edad_max,
            "intereses": _filtrar(datos.get("intereses"), INTERESES)[:5] or base["intereses"],
            "restricciones_cumplidas": _filtrar(datos.get("restricciones_cumplidas"), RESTRICCIONES),
            "modo": "ia"}
