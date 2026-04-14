"""
ingest.py — Ingesta y deduplicación de CDRs
=============================================
Este módulo carga los ficheros CSV exportados de FreePBX/Asterisk,
los limpia y deduplica para obtener UNA fila por llamada real.

¿Por qué deduplicar?
    Cuando una llamada entra en la cola 251, Asterisk genera un registro
    por cada extensión del ring group (201, 221, 224, 225), tanto en el
    contexto ext-queues como en ext-local. Una sola llamada puede generar
    8+ registros. Si no deduplicamos, el análisis es incorrecto.

¿Cómo deduplicamos?
    Todos los registros de una misma llamada comparten el mismo campo
    'linkedid'. Agrupamos por linkedid y nos quedamos con UN registro
    por llamada, determinando si fue contestada o no.

Autor: Víctor Soriano Tárrega (@vjsoriano83)
"""

import pandas as pd
import os
import glob


def load_cdr(path: str) -> pd.DataFrame:
    """
    Carga uno o varios ficheros CSV de CDR.

    Parámetros:
        path: puede ser:
            - Un fichero concreto: "data/sample_cdr.csv"
            - Un patrón glob: "data/*.csv" (carga todos los CSV de la carpeta)

    Retorna:
        Un DataFrame de pandas con todos los registros combinados.
    """

    # glob.glob() busca ficheros que coincidan con el patrón.
    # Si path es "data/*.csv", devuelve ["data/1T.csv", "data/2T.csv", ...]
    # Si path es un fichero concreto, devuelve solo ese fichero.
    files = glob.glob(path)

    if not files:
        raise FileNotFoundError(f"No se encontraron ficheros en: {path}")

    # Cargamos cada fichero y los combinamos en un solo DataFrame.
    # pd.read_csv() lee un CSV y lo convierte en DataFrame (tabla en memoria).
    # pd.concat() une varios DataFrames uno debajo de otro.
    dataframes = []
    for f in sorted(files):
        df = pd.read_csv(f, low_memory=False)
        dataframes.append(df)
        print(f"   📄 {os.path.basename(f)}: {len(df):,} registros")

    combined = pd.concat(dataframes, ignore_index=True)
    print(f"   📊 Total registros brutos: {len(combined):,}")

    return combined


def clean_cdr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y enriquece los datos brutos del CDR.

    Operaciones:
        1. Parsear fechas (convertir texto a formato fecha)
        2. Limpiar números de teléfono
        3. Añadir columnas útiles (hora, día de la semana, trimestre)
        4. Filtrar registros de sistema (códigos de función como *271)
    """

    # ── 1. Parsear fechas ──
    # El campo 'calldate' viene como texto ("2025-12-31 12:19:03").
    # Lo convertimos a datetime de pandas para poder hacer cálculos
    # como "¿a qué hora fue?" o "¿qué día de la semana?".
    df["calldate"] = pd.to_datetime(df["calldate"], errors="coerce")

    # Eliminamos filas donde la fecha no se pudo parsear (datos corruptos)
    df = df.dropna(subset=["calldate"])

    # ── 2. Limpiar números de teléfono ──
    # El campo 'src' a veces trae el prefijo +34 y a veces no.
    # Normalizamos: quitamos el +34 si existe, para comparar fácilmente.
    df["src_clean"] = df["src"].astype(str).str.replace("+34", "", regex=False)

    # ── 3. Añadir columnas útiles ──
    # Extraemos información temporal que usaremos en los KPIs y gráficos.
    df["hour"] = df["calldate"].dt.hour           # Hora (0-23)
    df["weekday"] = df["calldate"].dt.day_name()   # "Monday", "Tuesday"...
    df["date"] = df["calldate"].dt.date            # Solo la fecha, sin hora
    df["month"] = df["calldate"].dt.month          # Mes (1-12)

    # Trimestre: Q1 = Ene-Mar, Q2 = Abr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dic
    df["quarter"] = df["calldate"].dt.quarter

    # ── 4. Filtrar registros de sistema ──
    # Extensiones que empiezan por * son códigos de función internos
    # (como *271 para buzón de voz). No son llamadas reales.
    df = df[~df["dst"].astype(str).str.startswith("*")]

    print(f"   🧹 Registros tras limpieza: {len(df):,}")

    return df


def deduplicate_calls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplica los registros para obtener UNA fila por llamada real.

    Esta es la función más importante del proyecto. Sin ella, una sola
    llamada que entra en la cola 251 y hace ring en 4 extensiones
    aparecería como 8 registros (4 en ext-queues + 4 en ext-local).

    Lógica de deduplicación:
        1. Agrupamos todos los registros por 'linkedid'
        2. Para cada grupo (= una llamada real), determinamos:
           - ¿Se contestó? → si ALGÚN registro tiene disposition = ANSWERED
           - ¿Quién contestó? → la extensión del registro ANSWERED
           - ¿Cuánto duró la conversación? → el billsec del registro ANSWERED
           - ¿Cuándo entró? → la fecha del primer registro del grupo
           - ¿Quién llamó? → el src del primer registro del grupo
    """

    # Agrupamos por linkedid y procesamos cada grupo.
    # .agg() nos permite aplicar diferentes funciones a cada columna.

    def resolve_call(group):
        """Procesa un grupo de registros que pertenecen a la misma llamada."""

        # ¿Hay algún registro ANSWERED en el grupo?
        answered_records = group[group["disposition"] == "ANSWERED"]

        if len(answered_records) > 0:
            # La llamada se contestó.
            # Tomamos el registro ANSWERED que tiene billsec > 0
            # (ese es el que realmente mantuvo la conversación).
            best = answered_records.sort_values("billsec", ascending=False).iloc[0]
            disposition = "ANSWERED"
            answering_ext = best["dst"]
            billsec = best["billsec"]
        else:
            # La llamada NO se contestó.
            # Tomamos el primer registro del grupo para los datos básicos.
            best = group.iloc[0]
            disposition = best["disposition"]  # NO ANSWER, BUSY, or FAILED
            answering_ext = None
            billsec = 0

        # Construimos una fila resumen para esta llamada
        return pd.Series({
            "calldate": group["calldate"].min(),      # Momento en que entró
            "src": group["src"].iloc[0],               # Quién llamó
            "src_clean": group["src_clean"].iloc[0],
            "disposition": disposition,                 # Resultado real
            "answering_ext": answering_ext,            # Quién contestó
            "billsec": int(billsec),                   # Duración conversación
            "duration": int(best["duration"]),          # Duración total
            "hour": group["hour"].iloc[0],
            "weekday": group["weekday"].iloc[0],
            "date": group["date"].iloc[0],
            "month": group["month"].iloc[0],
            "quarter": group["quarter"].iloc[0],
            "num_records": len(group),                 # Cuántos registros generó
        })

    # Aplicamos resolve_call a cada grupo de linkedid
    print("   🔗 Deduplicando por linkedid...")
    calls = df.groupby("linkedid").apply(resolve_call, include_groups=False).reset_index(drop=True)

    # Ordenamos por fecha (más reciente primero)
    calls = calls.sort_values("calldate", ascending=False).reset_index(drop=True)

    print(f"   ✅ Llamadas únicas: {len(calls):,}")
    print(f"   📞 Contestadas: {len(calls[calls['disposition'] == 'ANSWERED']):,} "
          f"({len(calls[calls['disposition'] == 'ANSWERED']) / len(calls) * 100:.1f}%)")
    print(f"   📵 No contestadas: {len(calls[calls['disposition'] != 'ANSWERED']):,} "
          f"({len(calls[calls['disposition'] != 'ANSWERED']) / len(calls) * 100:.1f}%)")

    return calls


def load_and_process(path: str = "data/sample_cdr.csv") -> pd.DataFrame:
    """
    Pipeline completo: carga → limpieza → deduplicación.

    Esta función ejecuta los tres pasos en orden y devuelve
    un DataFrame limpio con una fila por llamada real.
    Es la función que llamaremos desde main.py.
    """
    print("📥 Paso 1: Cargando CDR...")
    raw = load_cdr(path)

    print("🧹 Paso 2: Limpiando datos...")
    clean = clean_cdr(raw)

    print("🔗 Paso 3: Deduplicando llamadas...")
    calls = deduplicate_calls(clean)

    return calls


# ── Si ejecutas este fichero directamente, muestra un resumen ──
if __name__ == "__main__":
    calls = load_and_process()
    print(f"\n{'='*50}")
    print(f"Resumen del pipeline de ingesta:")
    print(f"  Llamadas totales: {len(calls):,}")
    print(f"  Rango de fechas:  {calls['calldate'].min()} → {calls['calldate'].max()}")
    print(f"  Columnas:         {list(calls.columns)}")