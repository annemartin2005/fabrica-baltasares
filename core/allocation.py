"""Reparto de stock a organizaciones con restricciones, cuotas y rondas de equidad."""
from __future__ import annotations

from collections import Counter

from core.db import FRANJAS, RESTRICCIONES


def encaja_en_franja(j: dict, franja: str) -> bool:
    """Un juguete sirve para una franja si cubre su edad central (prudente con los más pequeños)."""
    a, b = FRANJAS[franja]
    centro = (a + b) // 2
    return j["edad_min"] <= centro <= j["edad_max"]


def cumple_restricciones(j: dict, restricciones: list[str]) -> bool:
    return set(restricciones) <= set(j["restricciones"])


def repartir(ninos: dict[str, int], stock: list[dict], restricciones: list[str] | None = None,
             categorias_preferidas: list[str] | None = None, juguetes_por_nino: int = 1) -> dict:
    """Propone un reparto.

    ninos: {"0-2": 4, "3-5": 10, ...}. Devuelve asignaciones, cobertura, sin cubrir y conflictos.
    """
    restricciones = restricciones or []
    preferidas = categorias_preferidas or []
    ninos = {f: int(n) for f, n in ninos.items() if int(n) > 0}

    # 1. Filtrar stock por restricciones
    aptos = [j for j in stock if cumple_restricciones(j, restricciones)]
    descartados = len(stock) - len(aptos)

    # 2. Cuotas proporcionales al número de niños (sobre lo que se puede cubrir)
    total_ninos = sum(ninos.values())
    capacidad = min(total_ninos * juguetes_por_nino, len(aptos))
    cuotas = {f: round(capacidad * n / total_ninos) if total_ninos else 0 for f, n in ninos.items()}

    usados: set[int] = set()
    asignaciones: list[dict] = []
    por_franja: dict[str, list[dict]] = {f: [] for f in ninos}

    def elegir(franja: str) -> dict | None:
        ya = por_franja[franja]
        nombres = {a["nombre"] for a in ya}
        cats = Counter(a["categoria"] for a in ya)
        opciones = [j for j in aptos if j["id"] not in usados and encaja_en_franja(j, franja)]
        if not opciones:
            return None
        # 4. Prioriza categorías preferidas, evita duplicar tipo y reparte categorías
        opciones.sort(key=lambda j: (j["nombre"] in nombres, j["categoria"] not in preferidas,
                                     cats[j["categoria"]], j["id"]))
        return opciones[0]

    # 3. Rondas de equidad: primero un juguete por niño en todas las franjas, luego segundos juguetes
    # (el turno rotatorio por la franja más rezagada reparte el stock escaso en proporción a los niños)
    for ronda in range(1, juguetes_por_nino + 1):
        avanzando = True
        while avanzando:
            avanzando = False
            for franja in sorted(ninos, key=lambda f: (len(por_franja[f]) / ninos[f], f)):
                if len(por_franja[franja]) >= ninos[franja] * ronda:
                    continue
                j = elegir(franja)
                if j:
                    usados.add(j["id"])
                    por_franja[franja].append(j)
                    asignaciones.append({"franja": franja, "juguete_id": j["id"], "ronda": ronda,
                                         "nombre": j["nombre"], "categoria": j["categoria"]})
                    avanzando = True

    cobertura = {}
    conflictos = []
    for franja, n in ninos.items():
        cubiertos = min(n, len(por_franja[franja]))
        cobertura[franja] = {"ninos": n, "cubiertos": cubiertos, "juguetes": len(por_franja[franja])}
        if cubiertos < n:
            disponibles_sin_filtro = sum(1 for j in stock if encaja_en_franja(j, franja))
            disponibles_con_filtro = sum(1 for j in aptos if encaja_en_franja(j, franja))
            if restricciones and disponibles_con_filtro < disponibles_sin_filtro:
                motivo = (f"Faltan {n - cubiertos} juguetes para {franja} años que cumplan: "
                          + ", ".join(RESTRICCIONES[r].lower() for r in restricciones) + ".")
            else:
                motivo = f"Faltan {n - cubiertos} juguetes para {franja} años en el stock actual."
            conflictos.append({"franja": franja, "motivo": motivo})

    total_cubiertos = sum(c["cubiertos"] for c in cobertura.values())
    return {"asignaciones": asignaciones, "cobertura": cobertura, "cuotas": cuotas, "ninos_total": total_ninos,
            "cubiertos_total": total_cubiertos, "sin_cubrir": total_ninos - total_cubiertos,
            "conflictos": conflictos, "descartados_por_restricciones": descartados}


def recalcular_cobertura(prop: dict, ninos: dict[str, int]) -> dict:
    """Actualiza cobertura y totales tras las correcciones manuales de la entidad."""
    ninos = {f: int(n) for f, n in ninos.items() if int(n) > 0}
    for franja, n in ninos.items():
        juguetes = sum(1 for a in prop.get("asignaciones", []) if a["franja"] == franja)
        prop.setdefault("cobertura", {})[franja] = {"ninos": n, "cubiertos": min(n, juguetes), "juguetes": juguetes}
    prop["cubiertos_total"] = sum(c["cubiertos"] for c in prop["cobertura"].values())
    prop["ninos_total"] = sum(ninos.values())
    prop["sin_cubrir"] = prop["ninos_total"] - prop["cubiertos_total"]
    return prop


def stock_para(fecha_limite: str, necesidad_id: int | None = None) -> list[dict]:
    """Stock publicado menos lo ya propuesto a entidades con fecha límite más cercana (prioridad)."""
    from core import db

    bloqueados: set[int] = set()
    for nec in db.consulta("SELECT id, fecha_limite, propuesta FROM necesidades WHERE estado = 'propuesta'"):
        if nec["id"] != necesidad_id and (nec["fecha_limite"] or "9999") <= fecha_limite:
            prop = db.de_json(nec["propuesta"], {})
            bloqueados |= {a["juguete_id"] for a in prop.get("asignaciones", [])}
    return [j for j in db.juguetes_publicados() if j["id"] not in bloqueados]


def reparto_referencia(ninos: dict[str, int], stock: list[dict], juguetes_por_nino: int = 1) -> dict:
    """Reparto manual simplificado: por orden de llegada, franja a franja, sin equidad ni restricciones."""
    usados: set[int] = set()
    asignaciones = []
    for franja, n in ninos.items():
        for j in sorted(stock, key=lambda x: x["id"]):
            if sum(1 for a in asignaciones if a["franja"] == franja) >= n * juguetes_por_nino:
                break
            if j["id"] not in usados and encaja_en_franja(j, franja):
                usados.add(j["id"])
                asignaciones.append({"franja": franja, "juguete_id": j["id"], "nombre": j["nombre"],
                                     "categoria": j["categoria"]})
    cobertura = {f: min(n, sum(1 for a in asignaciones if a["franja"] == f)) for f, n in ninos.items()}
    return {"asignaciones": asignaciones, "cobertura": cobertura,
            "cubiertos_total": sum(cobertura.values()), "ninos_total": sum(ninos.values())}


def metricas_reparto(asignaciones: list[dict], stock_por_id: dict[int, dict], restricciones: list[str],
                     ninos: dict[str, int]) -> dict:
    """Duplicidades, incumplimientos y cobertura para comparar con la referencia."""
    dup = 0
    for franja in {a["franja"] for a in asignaciones}:
        nombres = Counter(a["nombre"] for a in asignaciones if a["franja"] == franja)
        dup += sum(c - 1 for c in nombres.values() if c > 1)
    incumple = sum(1 for a in asignaciones if not cumple_restricciones(stock_por_id[a["juguete_id"]], restricciones))
    franjas_con = {f for f in ninos if any(a["franja"] == f for a in asignaciones)}
    cubiertos = sum(min(n, sum(1 for a in asignaciones if a["franja"] == f)) for f, n in ninos.items())
    return {"duplicidades": dup, "incumplimientos": incumple, "franjas_atendidas": len(franjas_con),
            "cobertura": cubiertos / max(sum(ninos.values()), 1)}
