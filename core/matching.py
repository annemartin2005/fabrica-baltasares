"""Emparejamiento carta → juguetes: filtros duros, puntuación, diversidad y explicación."""
from __future__ import annotations

import random

from core.ai import AFINES, OBJETOS, PALABRAS_OBJETO, categorias_de, normalizar
from core.db import CATEGORIAS

OBJETOS_FEMENINOS = {"guitarra", "bicicleta", "cocinita", "pizarra", "casa de muñecas", "cometa"}

PESO_ESTADO = {"Nuevo con caja": 1.0, "Nuevo sin caja": 0.85, "Fuera de catálogo": 0.8, "Tara estética": 0.6}


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def edad_valida(j: dict, edad: int) -> bool:
    return j["edad_min"] <= edad <= j["edad_max"]


def _rechazado(j: dict, rechazos: list[str]) -> bool:
    if not rechazos:
        return False
    if set(j["intereses"]) & set(rechazos):
        return True
    return j["categoria"] in categorias_de(rechazos) and j["categoria"] in ("peluche", "disfraz", "libro", "puzle")


def puntuar(j: dict, intereses: list[str], categorias: list[str]) -> dict:
    s_int = jaccard(intereses, j["intereses"])
    s_cat = 1.0 if j["categoria"] in categorias else 0.0
    s_est = PESO_ESTADO.get(j["estado_fisico"], 0.7)
    return {"total": round(0.6 * s_int + 0.25 * s_cat + 0.15 * s_est, 4),
            "intereses": s_int, "categoria": s_cat, "estado": s_est}


def estrellas(puntuacion: float) -> int:
    """Convierte la puntuación 0-1 en 1-5 estrellas."""
    return max(1, min(5, round(puntuacion * 5 + 0.5)))


def _explicar(j: dict, edad: int, intereses: list[str], categorias: list[str], relajado: str | None) -> str:
    comunes = [i for i in intereses if i in j["intereses"]]
    partes = []
    if comunes:
        if len(comunes) == 1:
            frase = _con_articulo(comunes[0])
            verbo = "gustan" if frase.startswith(("los ", "las ")) else "gusta"
            partes.append(f"Le {verbo} {frase}")
        else:
            partes.append("Le gustan " + _lista([_con_articulo(c) for c in comunes]))
    elif relajado == "intereses":
        afines = [a for i in intereses for a in AFINES.get(i, []) if a in j["intereses"]]
        if afines:
            partes.append(f"Está relacionado con lo que pide ({afines[0]})")
        elif j["categoria"] in categorias:
            partes.append(f"Es de un tipo de juguete que suele gustar con esos intereses ({CATEGORIAS[j['categoria']].lower()})")
    elif j["categoria"] in categorias:
        partes.append(f"Encaja con el tipo de juguete que pide ({CATEGORIAS[j['categoria']].lower()})")
    partes.append(f"es adecuado para sus {edad} años")
    if j["estado_fisico"] in ("Nuevo con caja", "Nuevo sin caja"):
        partes.append("está nuevo")
    texto = ", ".join(partes[:-1]) + (" y " if len(partes) > 1 else "") + partes[-1]
    return texto[0].upper() + texto[1:] + "."


def _con_articulo(interes: str) -> str:
    sin_articulo = {"música", "fútbol", "baloncesto", "deporte", "dibujo", "cocina", "magia", "construcción",
                    "ciencia", "lectura", "baile", "naturaleza", "fantasía", "espacio", "agua", "mar", "exploración",
                    "bicicleta"}
    if interes in sin_articulo:
        return {"dibujo": "dibujar", "cocina": "cocinar", "lectura": "leer", "baile": "bailar",
                "construcción": "construir", "exploración": "explorar", "espacio": "el espacio", "mar": "el mar",
                "bicicleta": "la bici", "agua": "el agua", "fantasía": "la fantasía", "naturaleza": "la naturaleza"
                }.get(interes, "la " + interes if interes in ("música", "ciencia", "magia") else
                      ("el " + interes if interes in ("fútbol", "baloncesto", "deporte") else interes))
    femeninos = {"muñecos": "los muñecos", "puzles": "los puzles", "manualidades": "las manualidades",
                 "granja": "la granja", "marionetas": "las marionetas"}
    return femeninos.get(interes, "los " + interes)


def _lista(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def _diversificar(ordenados: list[dict], n: int) -> list[dict]:
    """Elige n sin repetir nombre y evitando que todas sean de la misma categoría si hay alternativa."""
    elegidos: list[dict] = []
    nombres: set[str] = set()
    for c in ordenados:
        if len(elegidos) >= n:
            break
        if c["juguete"]["nombre"] in nombres:
            continue
        cats = [e["juguete"]["categoria"] for e in elegidos]
        if len(elegidos) == n - 1 and cats and len(set(cats)) == 1 and c["juguete"]["categoria"] == cats[0]:
            alternativa = next((o for o in ordenados if o not in elegidos and o["juguete"]["categoria"] != cats[0]
                                and o["juguete"]["nombre"] not in nombres), None)
            if alternativa:
                c = alternativa
        elegidos.append(c)
        nombres.add(c["juguete"]["nombre"])
    return elegidos


def objetos_no_disponibles(objetos: list[str], stock: list[dict], edad: int) -> list[str]:
    faltan = []
    for o in objetos:
        palabras = PALABRAS_OBJETO.get(o, [o])
        hay = any(any(p in normalizar(j["nombre"] + " " + (j.get("descripcion") or "")) for p in palabras)
                  and edad_valida(j, edad) for j in stock) if palabras else False
        if not hay:
            faltan.append(o)
    return faltan


def proponer(carta: dict, stock: list[dict], n: int = 3, excluir: set[int] | None = None) -> dict:
    """Devuelve propuestas explicadas y avisos (relajación o falta de encaje).

    carta: dict con edad, intereses, categorias_preferidas, rechazos y objetos.
    """
    edad = int(carta["edad"])
    intereses = carta.get("intereses", [])
    categorias = carta.get("categorias_preferidas", []) or categorias_de(intereses)
    rechazos = carta.get("rechazos", [])
    excluir = excluir or set()

    # 1. Filtros duros: publicado (stock), edad, rechazos
    base = [j for j in stock if j["id"] not in excluir and j.get("estado", "publicado") == "publicado"
            and edad_valida(j, edad) and not _rechazado(j, rechazos)]

    avisos: list[str] = []
    faltan = objetos_no_disponibles(carta.get("objetos", []), stock, edad)
    for o in faltan:
        if o == "aparato electrónico":
            avisos.append("No recogemos aparatos electrónicos (consolas, tablets o móviles); te proponemos juguetes "
                          "para su edad.")
        else:
            interes_obj = next((i for nombre, i in OBJETOS.values() if nombre == o and i), None)
            temas = [interes_obj, *AFINES.get(interes_obj, [])[:1]] if interes_obj else intereses[:2]
            texto_temas = _lista(temas) if temas else "otros juguetes"
            ninguno = "ninguna" if o in OBJETOS_FEMENINOS else "ningún"
            avisos.append(f"Ahora no tenemos {ninguno} {o}; te proponemos alternativas de {texto_temas} para su edad.")

    # 2. Niveles de encaje: exacto (intereses) → afines o categoría → solo edad (la edad nunca se relaja)
    afines = {a for i in intereses for a in AFINES.get(i, [])} - set(intereses)
    if intereses:
        nivel0 = [j for j in base if set(j["intereses"]) & set(intereses)]
        nivel1 = [j for j in base if j not in nivel0 and (set(j["intereses"]) & afines or j["categoria"] in categorias)]
        nivel2 = [j for j in base if j not in nivel0 and j not in nivel1]
        niveles = [(nivel0, None), (nivel1, "intereses"), (nivel2, "categoria")]
    else:
        niveles = [([], None), ([], "intereses"), (base, "sin_intereses")]
    relajado = next((r for lista, r in niveles if lista), "categoria")

    # 3. Puntuación y elección por niveles: se completa hasta n con el nivel siguiente si hace falta
    elegidos: list[dict] = []
    total_candidatos = 0
    for lista, nivel in niveles:
        puntuados = []
        for j in lista:
            p = puntuar(j, intereses, categorias)
            if nivel == "intereses":
                p["total"] = round(p["total"] + 0.3 * jaccard(list(afines), j["intereses"]), 4)
            puntuados.append({"juguete": j, "puntuacion": p, "nivel": nivel})
        puntuados.sort(key=lambda c: (-c["puntuacion"]["total"], c["juguete"]["id"]))
        total_candidatos += len(puntuados)
        if len(elegidos) < n:
            nombres = {e["juguete"]["nombre"] for e in elegidos}
            nuevos = _diversificar([c for c in puntuados if c["juguete"]["nombre"] not in nombres], n - len(elegidos))
            elegidos += nuevos
    for e in elegidos:
        e["explicacion"] = _explicar(e["juguete"], edad, intereses, categorias, e["nivel"])
        factor = 1.0 if e["nivel"] is None else 0.8
        e["estrellas"] = estrellas(e["puntuacion"]["total"] * factor)

    if not base:
        avisos.append(f"Ahora mismo no tenemos juguetes publicados para {edad} años. Puedes apuntarte a «Avisadme "
                      "si llega» y os escribiremos en cuanto entre uno.")
    elif relajado == "intereses":
        avisos.append("No tenemos ahora ningún juguete de " + _lista(intereses) +
                      " para su edad; te proponemos los más parecidos.")
    elif relajado == "categoria":
        avisos.append("No hemos encontrado nada relacionado con " + _lista(intereses) +
                      "; te proponemos juguetes variados para su edad.")
    return {"propuestas": elegidos, "avisos": avisos, "relajado": relajado, "sin_encaje": bool(faltan) or
            relajado in ("intereses", "categoria") or not base, "objetos_faltan": faltan,
            "total_candidatos": total_candidatos}


def asignacion_referencia(edad: int, stock: list[dict], semilla: int = 42, n: int = 3) -> list[dict]:
    """Referencia de comparación: juguetes aleatorios de la edad correcta (semilla fija)."""
    aptos = [j for j in stock if edad_valida(j, edad)]
    rnd = random.Random(semilla + edad)
    return rnd.sample(aptos, min(n, len(aptos)))
