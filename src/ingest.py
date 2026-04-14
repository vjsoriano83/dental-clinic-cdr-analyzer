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

# Extensiones que son buzón de voz (no personas reales)
VOICEMAIL_EXTENSIONS = {"vmu201", "vms201"}


def load_cdr(path: str) -> pd.DataFrame:
    """
    Carga uno o varios ficheros CSV de CDR.

    Parámetros:
        path: puede ser:
            - Un fichero concreto: "data/sample_cdr.csv"
            - Un patrón glob: "data/*.csv" (carga todos los CSV)

    Retorna:
        Un DataFrame de pandas con todos los registros combinados.
    """

    # glob.glob() busca ficheros que coincidan con el patrón
    files = glob.glob(path)

    if not files:
        raise FileNotFoundError(f"No se encontraron ficheros en: {path}")

    # Cargamos cada fichero y los combinamos en un solo DataFrame.
    # dtype={"src": str, "dst": str} fuerza lectura como texto,
    # evitando que pandas convierta +34612... en número y pierda el +.
    dataframes = []
    for f in sorted(files):
        df = pd.read_csv(f, low_memory=False, dtype={"src": str, "dst": str})
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
        3. Añadir columnas temporales (hora, día, trimestre)
        4. Filtrar registros de sistema (códigos como *271)
        5. Clasificar dirección de llamada (entrante/saliente/interna)
    """

    # ── 1. Parsear fechas ──
    # 'calldate' viene como texto ("2025-12-31 12:19:03").
    # Lo convertimos a datetime para poder calcular hora, día, etc.
    df["calldate"] = pd.to_datetime(df["calldate"], errors="coerce")

    # Eliminamos filas con fecha corrupta
    df = df.dropna(subset=["calldate"])

    # ── 2. Limpiar números de teléfono ──
    # Quitamos el prefijo +34 para normalizar y comparar fácilmente
    df["src_clean"] = df["src"].astype(str).str.replace("+34", "", regex=False)

    # ── 3. Columnas temporales ──
    df["hour"] = df["calldate"].dt.hour           # Hora (0-23)
    df["weekday"] = df["calldate"].dt.day_name()   # "Monday", "Tuesday"...
    df["date"] = df["calldate"].dt.date            # Solo la fecha
    df["month"] = df["calldate"].dt.month          # Mes (1-12)
    df["quarter"] = df["calldate"].dt.quarter      # Trimestre (1-4)

    # ── 4. Filtrar registros de sistema ──
    # Extensiones que empiezan por * son códigos de función internos
    # (como *271 para acceder al buzón). No son llamadas reales.
    df = df[~df["dst"].astype(str).str.startswith("*")]

    # ── 5. Clasificar dirección de llamada ──
    # - Entrante externa (inbound): un paciente llama a la clínica
    # - Interna (internal): transferencia entre extensiones
    # - Saliente (outbound): la clínica llama hacia fuera
    def classify_direction(row):
        src = str(row["src_clean"])  # Sin +34
        dst = str(row["dst"])
        context = str(row["dcontext"])

        # Saliente: desde extensión interna hacia número externo
        if context == "from-internal" and (dst.startswith("+34") or (len(dst) >= 9 and dst[0] in "6789")):
            return "outbound"
        # Interna: origen es extensión corta (2-3 dígitos)
        if len(src) <= 4 and src.isdigit():
            return "internal"
        # Entrante externa: origen es número largo de móvil/fijo
        if len(src) >= 9 and src[0] in "6789":
            return "inbound"
        return "other"

    df["direction"] = df.apply(classify_direction, axis=1)

    print(f"   🧹 Registros tras limpieza: {len(df):,}")

    return df


def deduplicate_calls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplica los registros para obtener UNA fila por llamada real.

    Esta es la función más importante del proyecto. Sin ella, una sola
    llamada que entra en la cola 251 y hace ring en 4 extensiones
    aparecería como 8 registros (4 en ext-queues + 4 en ext-local).

    Lógica:
        1. Agrupamos todos los registros por 'linkedid'
        2. Para cada grupo (= una llamada real), determinamos:
           - ¿Se contestó? Si ALGÚN registro es ANSWERED
           - ¿Quién contestó? La extensión del registro ANSWERED en ext-local
           - ¿Fue al buzón de voz? Si contestó vmu201 o vms201
           - ¿Cuánto duró? El billsec del registro que contestó
    """

    def resolve_call(group):
        """Procesa un grupo de registros de la misma llamada."""

        # ¿Hay algún registro ANSWERED?
        answered_records = group[group["disposition"] == "ANSWERED"]

        if len(answered_records) > 0:
            # Buscamos el ANSWERED en contexto ext-local
            # (ahí el dst es la extensión real que cogió la llamada)
            local_answered = answered_records[answered_records["dcontext"] == "ext-local"]
            if len(local_answered) > 0:
                best = local_answered.sort_values("billsec", ascending=False).iloc[0]
            else:
                best = answered_records.sort_values("billsec", ascending=False).iloc[0]

            answering_ext = best["dst"]

            # ¿Contestó el buzón de voz?
            if answering_ext in VOICEMAIL_EXTENSIONS:
                disposition = "VOICEMAIL"
            else:
                disposition = "ANSWERED"

            billsec = best["billsec"]
        else:
            # Nadie contestó
            best = group.iloc[0]
            disposition = best["disposition"]  # NO ANSWER, BUSY o FAILED
            answering_ext = None
            billsec = 0

        return pd.Series({
            "calldate": group["calldate"].min(),       # Momento de entrada
            "src": group["src"].iloc[0],                # Quién llamó
            "src_clean": group["src_clean"].iloc[0],
            "disposition": disposition,                  # Resultado real
            "answering_ext": answering_ext,             # Quién contestó (o None)
            "billsec": int(billsec),                    # Duración conversación
            "duration": int(best["duration"]),           # Duración total
            "hour": group["hour"].iloc[0],
            "weekday": group["weekday"].iloc[0],
            "date": group["date"].iloc[0],
            "month": group["month"].iloc[0],
            "quarter": group["quarter"].iloc[0],
            "num_records": len(group),                  # Registros que generó
            "direction": group["direction"].iloc[0],    # inbound/outbound/internal
        })

    print("   🔗 Deduplicando por linkedid...")
    calls = df.groupby("linkedid").apply(resolve_call, include_groups=False).reset_index(drop=True)

    # Ordenamos por fecha (más reciente primero)
    calls = calls.sort_values("calldate", ascending=False).reset_index(drop=True)

    # Resumen
    total = len(calls)
    answered = len(calls[calls["disposition"] == "ANSWERED"])
    voicemail = len(calls[calls["disposition"] == "VOICEMAIL"])
    missed = total - answered - voicemail

    print(f"   ✅ Llamadas únicas: {total:,}")
    print(f"   📞 Contestadas: {answered:,} ({answered/total*100:.1f}%)")
    print(f"   📧 Buzón de voz: {voicemail:,} ({voicemail/total*100:.1f}%)")
    print(f"   📵 No contestadas: {missed:,} ({missed/total*100:.1f}%)")

    return calls


def load_and_process(path: str = "data/sample_cdr.csv") -> pd.DataFrame:
    """
    Pipeline completo: carga → limpieza → deduplicación.

    Es la función que llamaremos desde main.py.
    Devuelve un DataFrame limpio con una fila por llamada real.
    """
    print("📥 Paso 1: Cargando CDR...")
    raw = load_cdr(path)

    print("🧹 Paso 2: Limpiando datos...")
    clean = clean_cdr(raw)

    print("🔗 Paso 3: Deduplicando llamadas...")
    calls = deduplicate_calls(clean)

    return calls


# ── Ejecución directa para pruebas ──
if __name__ == "__main__":
    calls = load_and_process()
    print(f"\n{'='*50}")
    print(f"Resumen del pipeline de ingesta:")
    print(f"  Llamadas totales: {len(calls):,}")
    print(f"  Rango de fechas:  {calls['calldate'].min()} → {calls['calldate'].max()}")
    print(f"  Columnas:         {list(calls.columns)}")
    print(f"  Direcciones:      {calls['direction'].value_counts().to_dict()}")
    print(f"  Disposiciones:    {calls['disposition'].value_counts().to_dict()}")