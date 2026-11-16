"""Cálculos del dashboard de impacto y del informe (una única fuente de verdad)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from core import db
from core.events import EMBUDOS

RESCATADOS = ("Fuera de catálogo", "Tara estética")


def _filtro(campana_id: int | None, alias: str = "p") -> tuple[str, list]:
    return (f" AND {alias}.campana_id = ?", [campana_id]) if campana_id else ("", [])


def entregas(campana_id: int | None = None) -> pd.DataFrame:
    """Pedidos entregados con su fecha de entrega, juguete y donación."""
    f, params = _filtro(campana_id)
    filas = db.consulta(
        "SELECT p.*, j.nombre AS juguete, j.categoria, j.estado_fisico, j.peso_kg, j.fotos, d.creado AS donado, "
        "d.tipo AS tipo_donacion, (SELECT MAX(h.fecha) FROM historial h WHERE h.objeto='pedido' AND "
        "h.objeto_id=p.id AND h.estado='entregado') AS entregado_en FROM pedidos p "
        "JOIN juguetes j ON j.id = p.juguete_id LEFT JOIN donaciones d ON d.id = j.donacion_id "
        "WHERE p.estado = 'entregado'" + f, params)
    df = pd.DataFrame(filas)
    if df.empty:
        return pd.DataFrame(columns=["id", "destino", "nino_ref", "familia_ref", "entidad_id", "organizacion_id",
                                     "franja", "barrio", "categoria", "estado_fisico", "peso_kg", "donado",
                                     "entregado_en", "tipo_donacion", "juguete", "fotos", "campana_id"])
    df["entregado_en"] = pd.to_datetime(df["entregado_en"])
    df["donado"] = pd.to_datetime(df["donado"])
    return df


def costes(campana_id: int | None = None) -> pd.DataFrame:
    f, params = (" WHERE campana_id = ?", [campana_id]) if campana_id else ("", [])
    return pd.DataFrame(db.consulta("SELECT * FROM costes" + f, params),
                        columns=["id", "campana_id", "concepto", "importe", "fecha", "nota"])


def kpis(campana_id: int | None = None) -> dict:
    ent = entregas(campana_id)
    cst = costes(campana_id)
    n_ent = len(ent)
    fam = ent[ent["destino"] == "familia"]
    org = ent[ent["destino"] == "organizacion"]
    ninos = fam["nino_ref"].nunique() + len(org)
    familias = fam["familia_ref"].fillna(fam["nino_ref"]).nunique()
    entidades = fam["entidad_id"].dropna().nunique() + org["organizacion_id"].dropna().nunique()
    total_coste = float(cst["importe"].sum()) if not cst.empty else 0.0
    coste_medio = total_coste / n_ent if n_ent else 0.0
    dias = (ent["entregado_en"] - ent["donado"]).dt.total_seconds() / 86400 if n_ent else pd.Series(dtype=float)
    rescatados = ent[ent["estado_fisico"].isin(RESCATADOS) | (ent["tipo_donacion"] == "empresa")]
    if campana_id:
        donados = db.uno("SELECT COUNT(*) n FROM juguetes WHERE campana_id = ?", (campana_id,))["n"]
    else:
        donados = db.uno("SELECT COUNT(*) n FROM juguetes")["n"]
    return {
        "donados": int(donados), "entregados": n_ent, "ninos": int(ninos), "familias": int(familias),
        "entidades": int(entidades), "coste_total": round(total_coste, 2), "coste_medio": round(coste_medio, 2),
        "dias_medios": round(float(dias.mean()), 1) if len(dias.dropna()) else 0.0,
        "rescatados": len(rescatados), "kg_rescatados": round(float(rescatados["peso_kg"].sum()), 1),
        "barrios": int(ent["barrio"].nunique()) if n_ent else 0,
    }


def coste_medio_global() -> float:
    return kpis()["coste_medio"]


def entregas_por_semana(campana_id: int | None = None) -> pd.DataFrame:
    ent = entregas(campana_id)
    if ent.empty:
        return pd.DataFrame(columns=["semana", "entregas"])
    s = ent.assign(semana=ent["entregado_en"].dt.to_period("W-SUN").dt.start_time)
    return s.groupby("semana").size().reset_index(name="entregas")


def distribucion(campo: str, campana_id: int | None = None) -> pd.DataFrame:
    ent = entregas(campana_id)
    if ent.empty:
        return pd.DataFrame(columns=[campo, "entregas"])
    return ent.groupby(campo).size().reset_index(name="entregas").sort_values("entregas", ascending=False)


def embudo_donacion() -> pd.DataFrame:
    """Donaciones que han alcanzado cada etapa (registrada → entregada), acumulando las anteriores.

    Sirve para particulares (publicar → match → revisión física) y para lotes (revisión → publicar → match).
    """
    etapas = [("Registradas", None), ("Publicadas", {"publicada"}), ("Elegidas por un niño", {"emparejada", "asignada"}),
              ("Revisión física superada", {"revisada"}), ("Entregadas", {"entregada"})]
    vistos: dict[int, set[str]] = {}
    for h in db.consulta("SELECT objeto_id, estado FROM historial WHERE objeto = 'donacion'"):
        vistos.setdefault(h["objeto_id"], set()).add(h["estado"])
    total = db.uno("SELECT COUNT(*) n FROM donaciones")["n"]
    filas, requeridos = [], []
    for nombre, estados in etapas:
        if estados is None:
            n = total
        else:
            requeridos.append(estados)
            n = sum(1 for est in vistos.values() if all(est & r for r in requeridos))
        filas.append({"etapa": nombre, "donaciones": n})
    return pd.DataFrame(filas)


def destino_aportaciones(campana_id: int | None = None) -> pd.DataFrame:
    cst = costes(campana_id)
    if cst.empty:
        return pd.DataFrame(columns=["destino", "importe"])
    grupos = {"Recogida": "Logística (GUBI)", "Entrega": "Logística (GUBI)", "Revisión": "Revisión de seguridad",
              "Gestión": "Gestión del proyecto"}
    cst["destino"] = cst["concepto"].map(grupos).fillna("Otros")
    return cst.groupby("destino")["importe"].sum().round(2).reset_index().sort_values("importe", ascending=False)


def volumen_puntos() -> pd.DataFrame:
    filas = db.consulta(
        "SELECT pt.*, (SELECT COUNT(*) FROM donaciones d WHERE d.punto_id = pt.id) AS donaciones, "
        "(SELECT COUNT(*) FROM pedidos p WHERE p.punto_id = pt.id AND p.estado != 'cancelado') AS pedidos "
        "FROM puntos pt")
    df = pd.DataFrame(filas)
    df["volumen"] = df["donaciones"] + df["pedidos"]
    return df


def necesidades_pendientes() -> pd.DataFrame:
    """Por franja: demanda reciente frente a stock publicado, más avisos sin cubrir."""
    filas = []
    for franja, (a, b) in db.FRANJAS.items():
        centro = (a + b) // 2
        stock = db.uno("SELECT COUNT(*) n FROM juguetes WHERE estado='publicado' AND edad_min <= ? AND edad_max >= ?",
                       (centro, centro))["n"]
        demanda = db.uno("SELECT COUNT(*) n FROM pedidos WHERE franja = ? AND creado >= date('now','-21 day')",
                         (franja,))["n"]
        avisos = db.uno("SELECT COUNT(*) n FROM avisos WHERE estado='pendiente' AND edad BETWEEN ? AND ?", (a, b))["n"]
        pendientes_org = 0
        for nec in db.consulta("SELECT propuesta FROM necesidades WHERE estado IN ('propuesta','aprobada')"):
            prop = db.de_json(nec["propuesta"], {})
            cob = prop.get("cobertura", {}).get(franja)
            if cob:
                pendientes_org += cob["ninos"] - cob["cubiertos"]
        filas.append({"franja": franja, "stock": stock, "demanda_21d": demanda, "avisos": avisos,
                      "ninos_sin_cubrir_org": pendientes_org})
    df = pd.DataFrame(filas)
    df["presion"] = (df["demanda_21d"] + df["avisos"] + df["ninos_sin_cubrir_org"]) / df["stock"].clip(lower=1)
    return df


def intereses_sin_stock() -> list[dict]:
    return db.consulta("SELECT interes, objeto, COUNT(*) n FROM avisos WHERE estado='pendiente' "
                       "GROUP BY interes, objeto ORDER BY n DESC")


def galeria(limite: int = 8, campana_id: int | None = None) -> list[dict]:
    ent = entregas(campana_id)
    if ent.empty:
        return []
    return ent.sort_values("entregado_en", ascending=False).head(limite).to_dict("records")


def fragmentos_cartas(limite: int = 3) -> list[dict]:
    return db.consulta("SELECT edad, texto_anon FROM cartas WHERE length(texto_anon) BETWEEN 30 AND 160 "
                       "ORDER BY id LIMIT ?", (limite,))


def avance_campana(campana: dict) -> dict:
    k = kpis(campana["id"])
    objetivo = campana["objetivo_juguetes"] or 1
    return {"objetivo": objetivo, "entregados": k["entregados"], "porcentaje": round(100 * k["entregados"] / objetivo, 1),
            "aportacion": campana["aportacion"], "coste_ejecutado": k["coste_total"]}


def embudo_eventos() -> pd.DataFrame:
    """Sesiones únicas por origen y paso, con conversión n/N respecto al paso anterior."""
    ev = pd.DataFrame(db.consulta("SELECT sesion, src, publico, evento FROM eventos"))
    if ev.empty:
        return pd.DataFrame(columns=["publico", "paso", "evento", "src", "sesiones", "n/N"])
    filas = []
    for publico, pasos in EMBUDOS.items():
        sub = ev[ev["publico"] == publico]
        for src in ["(todos)"] + sorted(sub["src"].dropna().unique().tolist()):
            datos = sub if src == "(todos)" else sub[sub["src"] == src]
            previo = None
            for i, paso in enumerate(pasos, 1):
                n = datos[datos["evento"] == paso]["sesion"].nunique()
                ratio = f"{n}/{previo}" + (f" ({100 * n / previo:.0f} %)" if previo else "") if previo is not None else "—"
                filas.append({"publico": publico, "src": src, "paso": i, "evento": paso, "sesiones": n, "n/N": ratio})
                previo = n
    return pd.DataFrame(filas)


def ultima_actualizacion() -> datetime:
    return datetime.now()
