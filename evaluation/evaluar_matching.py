"""Evaluación del emparejamiento (carta → juguetes) y del reparto a organizaciones frente a una referencia.

Uso:  python -m evaluation.evaluar_matching
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import ai, allocation, db, matching  # noqa: E402

# (id, descripción, edad, carta, comprobación esperada)
CASOS = [
    ("habitual", "Habitual", 6, "Tengo 6 años y me encantan los dinosaurios y pintar", {"intereses": ["dinosaurios", "dibujo"]}),
    ("edad_3", "Cambio de condiciones (3 años)", 3, "Tengo 3 años y me encantan los dinosaurios y pintar",
     {"intereses": ["dinosaurios", "dibujo"], "cambia_respecto": "habitual"}),
    ("telescopio", "Restricción difícil (sin stock)", 8, "Quiero un telescopio", {"objeto_falta": "telescopio",
                                                                                     "intereses": ["espacio", "ciencia", "exploración"]}),
    ("faltas", "Carta con faltas", 7, "kiero un dino y un balon", {"intereses": ["dinosaurios", "fútbol"]}),
    ("rechazo", "Con rechazo explícito", 5, "Me gustan los animales pero no me gustan los peluches",
     {"intereses": ["animales"], "sin_interes": "peluches"}),
    ("bebe", "Bebé", 1, "Para mi bebé, algo con texturas y sonajero", {"intereses": ["sensorial"]}),
    ("musica", "Música", 7, "Me encanta cantar y tocar la guitarra", {"intereses": ["música"]}),
    ("adolescente", "Adolescente", 13, "Me gustan los juegos de mesa con amigos y leer novelas", {"intereses": ["juegos de mesa", "lectura"]}),
    ("coches", "Vehículos", 4, "quiero coches y un camion de bomberos", {"intereses": ["coches"]}),
    ("ciencia", "Ciencia", 10, "Me gustan los experimentos y los volcanes", {"intereses": ["ciencia"]}),
    ("ambigua", "Ambigua", 6, "lo que sea, me porto bien", {"intereses": []}),
    ("disfraz", "Disfraces", 5, "Quiero disfrazarme de bombero", {"intereses": ["disfraces", "oficios"]}),
]


def _valido(j: dict, edad: int, rechazos: list[str]) -> bool:
    return j["edad_min"] <= edad <= j["edad_max"] and not (set(j["intereses"]) & set(rechazos))


def evaluar() -> dict:
    stock = db.juguetes_publicados()
    casos, propuestas_por_caso = [], {}
    cub_sis = cub_ref = inc_sis = inc_ref = total_props = total_ref = 0
    superados = 0
    for cid, nombre, edad, texto, esperado in CASOS:
        carta = ai.extraer_carta(ai.anonimizar(texto), edad)
        carta["edad"] = edad
        res = matching.proponer(carta, stock, 3)
        props = [p["juguete"] for p in res["propuestas"]]
        propuestas_por_caso[cid] = [j["id"] for j in props]
        ref = matching.asignacion_referencia(edad, stock)
        objetivo = set(esperado["intereses"]) or set(carta["intereses"])
        cubre = any(set(j["intereses"]) & objetivo for j in props) if objetivo else bool(props)
        cubre_ref = any(set(j["intereses"]) & objetivo for j in ref) if objetivo else bool(ref)
        incumple = sum(1 for j in props if not _valido(j, edad, carta["rechazos"]))
        incumple_ref = sum(1 for j in ref if not _valido(j, edad, carta["rechazos"]))
        ok = cubre and incumple == 0
        if "objeto_falta" in esperado:
            ok = ok and esperado["objeto_falta"] in res["objetos_faltan"] and bool(res["avisos"])
        if "sin_interes" in esperado:
            ok = ok and esperado["sin_interes"] in carta["rechazos"] and all(
                esperado["sin_interes"] not in j["intereses"] for j in props)
        if "cambia_respecto" in esperado:
            ok = ok and propuestas_por_caso[cid] != propuestas_por_caso[esperado["cambia_respecto"]]
            ok = ok and all("3 años" in p["explicacion"] for p in res["propuestas"])
        superados += ok
        cub_sis += cubre
        cub_ref += cubre_ref
        inc_sis += incumple
        inc_ref += incumple_ref
        total_props += len(props)
        total_ref += len(ref)
        casos.append({"caso": nombre, "edad": edad, "carta": texto, "intereses detectados": ", ".join(carta["intereses"]),
                      "modo": carta["modo"], "propuesta": " | ".join(j["nombre"] for j in props),
                      "aviso": " ".join(res["avisos"])[:140], "referencia aleatoria": " | ".join(j["nombre"] for j in ref),
                      "cubre interés": "sí" if cubre else "no", "ref. cubre": "sí" if cubre_ref else "no",
                      "incumplimientos": incumple, "resultado": "✓ superado" if ok else "✕ revisar"})

    # Reparto: hospital con «sin piezas pequeñas» y un colegio, frente al reparto manual
    stock_id = {j["id"]: j for j in stock}
    reparto = []
    for nombre, ninos, restr in [
        ("Hospital · sin piezas pequeñas", {"0-2": 4, "3-5": 6, "6-8": 5, "9-12": 3}, ["sin_piezas_pequenas"]),
        ("Hospital · fácil de desinfectar y sin sonido", {"0-2": 3, "3-5": 5, "6-8": 4}, ["facil_desinfectar", "sin_sonido"]),
        ("Colegio · sin restricciones", {"3-5": 8, "6-8": 10, "9-12": 6}, []),
    ]:
        sis = allocation.repartir(ninos, stock, restr)
        ref = allocation.reparto_referencia(ninos, stock)
        ms = allocation.metricas_reparto(sis["asignaciones"], stock_id, restr, ninos)
        mr = allocation.metricas_reparto(ref["asignaciones"], stock_id, restr, ninos)
        reparto.append({"caso": nombre, "cobertura sistema": f"{ms['cobertura']:.0%}", "cobertura manual": f"{mr['cobertura']:.0%}",
                        "incumplimientos sistema": ms["incumplimientos"], "incumplimientos manual": mr["incumplimientos"],
                        "duplicados sistema": ms["duplicidades"], "duplicados manual": mr["duplicidades"],
                        "franjas atendidas sistema": ms["franjas_atendidas"], "franjas atendidas manual": mr["franjas_atendidas"]})

    n = len(CASOS)
    return {"casos": casos, "reparto": reparto, "resumen": {
        "total": n, "superados": superados, "cobertura_sistema": 100 * cub_sis / n, "cobertura_referencia": 100 * cub_ref / n,
        "incumplimientos_sistema": 100 * inc_sis / max(total_props, 1),
        "incumplimientos_referencia": 100 * inc_ref / max(total_ref, 1)}}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    db.inicializar()
    r = evaluar()
    for c in r["casos"]:
        print(f"{c['resultado']:12} {c['caso']:34} → {c['propuesta']}")
        if c["aviso"]:
            print(f"{'':14}aviso: {c['aviso']}")
    print("\nResumen:", {k: round(v, 1) if isinstance(v, float) else v for k, v in r["resumen"].items()})
    print("\nReparto a organizaciones:")
    for f in r["reparto"]:
        print(" ", f)
