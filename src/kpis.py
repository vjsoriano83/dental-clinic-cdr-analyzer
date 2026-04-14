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
    Calcula los KPIs generales del portfolio de llamadas.

    Parámetros:
        df: DataFrame deduplicado (salida de ingest.load_and_process)

    Retorna:
        Un diccionario con todos los KPIs calculados.
        Lo usaremos para:
          1. Mostrarlo por pantalla
          2. Pasárselo a Claude para el informe con IA
          3. Alimentar los gráficos
    """

    # ── Desglose por dirección ──
    direction_counts = df["direction"].value_counts().to_dict()

    # Para los KPIs de negocio, nos centramos en llamadas ENTRANTES EXTERNAS.
    # Las internas y salientes no son "llamadas perdidas" en el sentido de negocio.
    inbound = df[df["direction"] == "inbound"]

    total = len(inbound)
    answered = len(inbound[inbound["disposition"] == "ANSWERED"])
    not_answered = len(inbound[inbound["disposition"] == "NO ANSWER"])
    busy = len(inbound[inbound["disposition"] == "BUSY"])
    failed = len(inbound[inbound["disposition"] == "FAILED"])

    # Solo llamadas contestadas para calcular duración media
    answered_calls = inbound[inbound["disposition"] == "ANSWERED"]

    kpis = OrderedDict()

    # ── KPIs generales ──
    kpis["total_calls"] = total
    kpis["answered"] = answered
    kpis["not_answered"] = not_answered
    kpis["busy"] = busy
    kpis["failed"] = failed

    # Tasa de contestación: % de llamadas que alguien cogió.
    # Es el KPI más importante. Por debajo del 80% hay un problema.
    kpis["answer_rate_pct"] = round(answered / total * 100, 1) if total > 0 else 0

    # Tasa de pérdida: lo contrario. Cada punto aquí es un paciente
    # potencial que no pudo hablar con la clínica.
    kpis["miss_rate_pct"] = round((not_answered + busy + failed) / total * 100, 1) if total > 0 else 0

    # Duración media de conversación (solo llamadas contestadas).
    # En una clínica dental, lo normal son 1-3 minutos (pedir cita,
    # confirmar, preguntar dirección...). Si es mucho más largo,
    # puede indicar que recepción está haciendo tareas que no le tocan.
    kpis["avg_duration_sec"] = round(answered_calls["billsec"].mean(), 1) if len(answered_calls) > 0 else 0
    kpis["avg_duration_min"] = round(kpis["avg_duration_sec"] / 60, 1)

    # Números únicos: ¿cuántos pacientes/personas distintas llaman?
    kpis["unique_callers"] = inbound["src_clean"].nunique()

    # Llamadas por día (media): da una idea del volumen diario
    # que tiene que manejar recepción.
    days = inbound["date"].nunique()
    kpis["avg_calls_per_day"] = round(total / days, 1) if days > 0 else 0

    # Desglose total por dirección (informativo)
    kpis["direction_breakdown"] = direction_counts
    kpis["total_all_directions"] = len(df)

    return kpis


def compute_hourly_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula cuántas llamadas hay por hora del día, separando
    contestadas y no contestadas.

    Solo llamadas entrantes externas — las que importan para el negocio.

    ¿Por qué importa?
    Permite saber a qué horas la clínica se colapsa. Si a las 10:00
    hay 3x más llamadas que a las 15:00 pero la misma recepcionista,
    ese es el problema.
    """

    inbound = df[df["direction"] == "inbound"]

    # pd.crosstab() crea una tabla cruzada: filas = horas, columnas = disposición
    hourly = pd.crosstab(inbound["hour"], inbound["disposition"])

    # Nos aseguramos de que las columnas existan aunque no haya datos
    for col in ["ANSWERED", "NO ANSWER", "BUSY", "FAILED"]:
        if col not in hourly.columns:
            hourly[col] = 0

    # Añadimos una columna de total y otra de tasa de pérdida por hora
    hourly["total"] = hourly.sum(axis=1)
    hourly["miss_rate_pct"] = round(
        (hourly["NO ANSWER"] + hourly["BUSY"] + hourly["FAILED"]) / hourly["total"] * 100, 1
    )

    return hourly


def compute_weekday_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el volumen de llamadas por día de la semana.

    Solo llamadas entrantes externas.

    ¿Por qué importa?
    Si los lunes tienen el doble de llamadas que los viernes,
    quizá se necesita refuerzo de personal al inicio de semana.
    """

    inbound = df[df["direction"] == "inbound"]

    # Orden correcto de los días (por defecto pandas los ordena alfabéticamente)
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    weekday = pd.crosstab(inbound["weekday"], inbound["disposition"])

    for col in ["ANSWERED", "NO ANSWER", "BUSY", "FAILED"]:
        if col not in weekday.columns:
            weekday[col] = 0

    weekday["total"] = weekday.sum(axis=1)
    weekday["miss_rate_pct"] = round(
        (weekday["NO ANSWER"] + weekday["BUSY"] + weekday["FAILED"]) / weekday["total"] * 100, 1
    )

    # Reordenamos los días correctamente
    existing_days = [d for d in day_order if d in weekday.index]
    weekday = weekday.reindex(existing_days)

    return weekday


def compute_extension_performance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula cuántas llamadas contestó cada extensión.

    Solo llamadas entrantes externas contestadas.

    ¿Por qué importa?
    Muestra qué extensiones (= qué personas) están cargando
    con el peso de las llamadas. Si una extensión contesta el 60%
    y las demás se reparten el 40%, hay un desequilibrio.
    """

    inbound = df[df["direction"] == "inbound"]

    # Solo llamadas contestadas (tienen answering_ext)
    answered = inbound[inbound["disposition"] == "ANSWERED"].copy()

    if len(answered) == 0:
        return pd.DataFrame()

    ext_stats = answered.groupby("answering_ext").agg(
        calls_answered=("disposition", "count"),
        avg_duration=("billsec", "mean"),
    ).round(1)

    ext_stats = ext_stats.sort_values("calls_answered", ascending=False)

    # Porcentaje del total de contestadas
    ext_stats["pct_of_answered"] = round(
        ext_stats["calls_answered"] / ext_stats["calls_answered"].sum() * 100, 1
    )

    return ext_stats


def compute_quarterly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la evolución trimestral de llamadas y tasa de contestación.

    Solo llamadas entrantes externas.

    ¿Por qué importa?
    Permite ver tendencias: ¿crece la demanda? ¿empeora el servicio
    en verano (vacaciones de personal)? ¿hay estacionalidad?
    """

    inbound = df[df["direction"] == "inbound"]

    quarterly = inbound.groupby("quarter").agg(
        total_calls=("disposition", "count"),
        answered=("disposition", lambda x: (x == "ANSWERED").sum()),
    )

    quarterly["not_answered"] = quarterly["total_calls"] - quarterly["answered"]
    quarterly["answer_rate_pct"] = round(
        quarterly["answered"] / quarterly["total_calls"] * 100, 1
    )

    return quarterly


def compute_top_callers(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Identifica los números que más llaman.

    Solo llamadas entrantes externas.

    ¿Por qué importa?
    Puede revelar:
    - Pacientes frecuentes (fidelización)
    - Números de spam/telemarketing (filtrar)
    - Pacientes que llaman muchas veces sin que les cojan (problema grave)
    """

    inbound = df[df["direction"] == "inbound"]

    caller_stats = inbound.groupby("src_clean").agg(
        total_calls=("disposition", "count"),
        answered=("disposition", lambda x: (x == "ANSWERED").sum()),
        not_answered=("disposition", lambda x: (x != "ANSWERED").sum()),
    )

    caller_stats["answer_rate_pct"] = round(
        caller_stats["answered"] / caller_stats["total_calls"] * 100, 1
    )

    caller_stats = caller_stats.sort_values("total_calls", ascending=False).head(top_n)

    return caller_stats


def compute_all_kpis(df: pd.DataFrame) -> dict:
    """
    Calcula TODOS los KPIs y los empaqueta en un diccionario.

    Esta es la función principal que llamaremos desde main.py.
    Devuelve un diccionario con todo lo necesario para:
    - Generar gráficos (visualize.py)
    - Generar el informe con IA (ai_report.py)
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

    # Resumen por pantalla
    g = results["general"]
    print(f"   📞 Entrantes externas: {g['total_calls']:,} (de {g['total_all_directions']:,} totales)")
    print(f"   📊 Desglose: {g['direction_breakdown']}")
    print(f"   ✅ Tasa de contestación: {g['answer_rate_pct']}%")
    print(f"   📵 Tasa de pérdida: {g['miss_rate_pct']}%")
    print(f"   ⏱️  Duración media: {g['avg_duration_min']} min")
    print(f"   👤 Llamantes únicos: {g['unique_callers']:,}")
    print(f"   📅 Media diaria: {g['avg_calls_per_day']} llamadas/día")

    return results


# ── Si ejecutas este fichero directamente, prueba con los datos de ejemplo ──
if __name__ == "__main__":
    from src.ingest import load_and_process

    calls = load_and_process()
    kpis = compute_all_kpis(calls)

    print(f"\n{'='*50}")
    print("Distribución por hora (top 5):")
    print(kpis["hourly"].sort_values("total", ascending=False).head())

    print(f"\nRendimiento por extensión:")
    print(kpis["extension"])