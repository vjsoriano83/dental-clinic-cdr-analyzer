"""
kpis.py — Cálculo de KPIs de negocio
======================================
Este módulo toma el DataFrame deduplicado (una fila por llamada real)
y calcula métricas que un gerente de clínica dental puede usar para
tomar decisiones.

IMPORTANTE: los KPIs principales se calculan SOLO sobre llamadas
entrantes externas (direction == "inbound"). Las internas y salientes
se reportan aparte pero no afectan a la tasa de pérdida, porque
que una transferencia interna no se complete no es lo mismo que
perder un paciente.

Autor: Víctor Soriano Tárrega (@vjsoriano83)
"""

import pandas as pd
from collections import OrderedDict


def compute_general_kpis(df: pd.DataFrame) -> dict:
    """
    Calcula los KPIs generales de llamadas.

    Solo cuenta llamadas entrantes externas para los KPIs de negocio.
    Las internas y salientes se informan aparte como contexto.
    """

    # Desglose por dirección (todas las llamadas)
    direction_counts = df["direction"].value_counts().to_dict()

    # Filtramos: solo entrantes externas para los KPIs de negocio
    inbound = df[df["direction"] == "inbound"]

    total = len(inbound)
    answered = len(inbound[inbound["disposition"] == "ANSWERED"])
    voicemail = len(inbound[inbound["disposition"] == "VOICEMAIL"])
    not_answered = len(inbound[inbound["disposition"] == "NO ANSWER"])
    busy = len(inbound[inbound["disposition"] == "BUSY"])
    failed = len(inbound[inbound["disposition"] == "FAILED"])

    # Duración media solo de llamadas contestadas por persona (no buzón)
    answered_calls = inbound[inbound["disposition"] == "ANSWERED"]

    kpis = OrderedDict()

    # ── KPIs generales ──
    kpis["total_calls"] = total
    kpis["answered"] = answered
    kpis["voicemail"] = voicemail
    kpis["not_answered"] = not_answered
    kpis["busy"] = busy
    kpis["failed"] = failed

    # Tasa de contestación: % que alguien cogió (persona real, no buzón).
    # Por debajo del 80% hay un problema.
    kpis["answer_rate_pct"] = round(answered / total * 100, 1) if total > 0 else 0

    # Tasa de buzón de voz: % que fue al voicemail.
    # Alto = recepción no da abasto y las llamadas desbordan al buzón.
    kpis["voicemail_rate_pct"] = round(voicemail / total * 100, 1) if total > 0 else 0

    # Tasa de pérdida total: no contestadas + ocupado + fallidas (sin contar buzón).
    # Cada punto aquí es un paciente que no pudo hablar con nadie.
    kpis["miss_rate_pct"] = round((not_answered + busy + failed) / total * 100, 1) if total > 0 else 0

    # Duración media de conversación (solo contestadas por persona).
    # En una clínica dental, lo normal son 1-3 minutos.
    kpis["avg_duration_sec"] = round(answered_calls["billsec"].mean(), 1) if len(answered_calls) > 0 else 0
    kpis["avg_duration_min"] = round(kpis["avg_duration_sec"] / 60, 1)

    # Números únicos: ¿cuántos pacientes distintos llaman?
    kpis["unique_callers"] = inbound["src_clean"].nunique()

    # Media de llamadas por día
    days = inbound["date"].nunique()
    kpis["avg_calls_per_day"] = round(total / days, 1) if days > 0 else 0

    # Desglose por dirección (informativo)
    kpis["direction_breakdown"] = direction_counts
    kpis["total_all_directions"] = len(df)

    return kpis


def compute_hourly_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Llamadas por hora del día (solo entrantes externas).

    ¿Por qué importa?
    Permite saber a qué horas la clínica se colapsa. Si a las 10:00
    hay 3x más llamadas que a las 15:00 pero la misma recepcionista,
    ese es el problema.
    """

    inbound = df[df["direction"] == "inbound"]
    hourly = pd.crosstab(inbound["hour"], inbound["disposition"])

    for col in ["ANSWERED", "VOICEMAIL", "NO ANSWER", "BUSY", "FAILED"]:
        if col not in hourly.columns:
            hourly[col] = 0

    hourly["total"] = hourly.sum(axis=1)
    hourly["miss_rate_pct"] = round(
        (hourly["NO ANSWER"] + hourly["BUSY"] + hourly["FAILED"]) / hourly["total"] * 100, 1
    )

    return hourly


def compute_weekday_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Llamadas por día de la semana (solo entrantes externas).

    ¿Por qué importa?
    Si los lunes tienen el doble de llamadas que los viernes,
    quizá se necesita refuerzo al inicio de semana.
    """

    inbound = df[df["direction"] == "inbound"]
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    weekday = pd.crosstab(inbound["weekday"], inbound["disposition"])

    for col in ["ANSWERED", "VOICEMAIL", "NO ANSWER", "BUSY", "FAILED"]:
        if col not in weekday.columns:
            weekday[col] = 0

    weekday["total"] = weekday.sum(axis=1)
    weekday["miss_rate_pct"] = round(
        (weekday["NO ANSWER"] + weekday["BUSY"] + weekday["FAILED"]) / weekday["total"] * 100, 1
    )

    existing_days = [d for d in day_order if d in weekday.index]
    weekday = weekday.reindex(existing_days)

    return weekday


def compute_extension_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rendimiento por extensión (solo entrantes externas contestadas).

    Excluye buzón de voz — solo extensiones reales (personas).

    ¿Por qué importa?
    Muestra quién carga con el peso de las llamadas. Si una extensión
    contesta el 50% y las demás se reparten el resto, hay desequilibrio.
    """

    inbound = df[df["direction"] == "inbound"]

    # Solo contestadas por persona (no buzón de voz)
    answered = inbound[inbound["disposition"] == "ANSWERED"].copy()

    if len(answered) == 0:
        return pd.DataFrame()

    ext_stats = answered.groupby("answering_ext").agg(
        llamadas_contestadas=("disposition", "count"),
        duracion_media=("billsec", "mean"),
    ).round(1)

    ext_stats = ext_stats.sort_values("llamadas_contestadas", ascending=False)

    ext_stats["pct_del_total"] = round(
        ext_stats["llamadas_contestadas"] / ext_stats["llamadas_contestadas"].sum() * 100, 1
    )

    return ext_stats


def compute_quarterly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evolución trimestral (solo entrantes externas).

    ¿Por qué importa?
    Permite ver tendencias: ¿crece la demanda? ¿empeora el servicio
    en verano? ¿hay estacionalidad?
    """

    inbound = df[df["direction"] == "inbound"]

    quarterly = inbound.groupby("quarter").agg(
        total_llamadas=("disposition", "count"),
        contestadas=("disposition", lambda x: (x == "ANSWERED").sum()),
        buzon_voz=("disposition", lambda x: (x == "VOICEMAIL").sum()),
    )

    quarterly["no_contestadas"] = quarterly["total_llamadas"] - quarterly["contestadas"] - quarterly["buzon_voz"]
    quarterly["tasa_contestacion_pct"] = round(
        quarterly["contestadas"] / quarterly["total_llamadas"] * 100, 1
    )

    return quarterly


def compute_top_callers(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Los números que más llaman (solo entrantes externas).

    ¿Por qué importa?
    Puede revelar:
    - Pacientes frecuentes (fidelización)
    - Spam/telemarketing (filtrar)
    - Pacientes que llaman muchas veces sin que les cojan (problema grave)
    """

    inbound = df[df["direction"] == "inbound"]

    caller_stats = inbound.groupby("src_clean").agg(
        total_llamadas=("disposition", "count"),
        contestadas=("disposition", lambda x: (x == "ANSWERED").sum()),
        no_contestadas=("disposition", lambda x: (x.isin(["NO ANSWER", "BUSY", "FAILED"])).sum()),
    )

    caller_stats["tasa_contestacion_pct"] = round(
        caller_stats["contestadas"] / caller_stats["total_llamadas"] * 100, 1
    )

    caller_stats = caller_stats.sort_values("total_llamadas", ascending=False).head(top_n)

    return caller_stats


def compute_all_kpis(df: pd.DataFrame) -> dict:
    """
    Calcula TODOS los KPIs y los empaqueta en un diccionario.

    Función principal — se llama desde main.py.
    El diccionario resultante alimenta gráficos e informe IA.
    """

    print("📊 Calculando KPIs...")

    results = {
        "general": compute_general_kpis(df),
        "hourly": compute_hourly_distribution(df),
        "weekday": compute_weekday_distribution(df),
        "extension": compute_extension_performance(df),
        "quarterly": compute_quarterly_trend(df),
        "top_callers": compute_top_callers(df),
    }

    g = results["general"]
    print(f"   📞 Entrantes externas: {g['total_calls']:,} (de {g['total_all_directions']:,} totales)")
    print(f"   📊 Desglose: {g['direction_breakdown']}")
    print(f"   ✅ Contestadas (persona): {g['answer_rate_pct']}%")
    print(f"   📧 Buzón de voz: {g['voicemail_rate_pct']}%")
    print(f"   📵 No contestadas: {g['miss_rate_pct']}%")
    print(f"   ⏱️  Duración media: {g['avg_duration_min']} min")
    print(f"   👤 Llamantes únicos: {g['unique_callers']:,}")
    print(f"   📅 Media diaria: {g['avg_calls_per_day']} llamadas/día")

    return results


# ── Ejecución directa para pruebas ──
if __name__ == "__main__":
    from src.ingest import load_and_process

    calls = load_and_process()
    kpis = compute_all_kpis(calls)

    print(f"\n{'='*50}")
    print("Distribución por hora (top 5):")
    print(kpis["hourly"].sort_values("total", ascending=False).head())

    print(f"\nRendimiento por extensión:")
    print(kpis["extension"])