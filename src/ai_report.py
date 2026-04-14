"""
ai_report.py — Generación de informe ejecutivo con IA
======================================================
Este módulo usa la API de Claude (Anthropic) para analizar los KPIs
de la clínica y generar un informe ejecutivo con recomendaciones.

¿Cómo funciona?
    1. Tomamos los KPIs calculados por kpis.py
    2. Los formateamos como texto estructurado (el "contexto")
    3. Construimos un prompt que le dice a Claude qué queremos
    4. Enviamos prompt + contexto a la API
    5. Claude devuelve un informe en Markdown
    6. Guardamos el informe en output/report_sample.md

Esto es una aplicación práctica de los conceptos que vemos en las
ofertas de empleo:
    - LLM: usamos Claude como modelo de lenguaje
    - Prompt engineering: diseñamos el prompt para obtener un informe estructurado
    - Contexto (mini-RAG): le damos datos específicos para que no alucine

Modos de funcionamiento:
    - Con API Key: genera un informe real llamando a Claude
    - Sin API Key: carga un informe de ejemplo pregenerado (modo demo)

Autor: Víctor Soriano Tárrega (@vjsoriano83)
"""

import os
import json

# Carpeta de salida para el informe
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def _format_kpis_as_context(kpis: dict) -> str:
    """
    Convierte los KPIs a texto estructurado para enviárselo a Claude.

    ¿Por qué texto y no JSON?
    Porque Claude entiende mejor el texto natural con estructura.
    Le damos los datos organizados por secciones para que sea fácil
    de procesar y generar un informe coherente.
    """

    g = kpis["general"]

    context = f"""
## CALL CENTER KPIs — DENTAL CLINIC

### General Metrics (Inbound External Calls Only)
- Total inbound calls: {g['total_calls']:,}
- Calls answered: {g['answered']:,} ({g['answer_rate_pct']}%)
- Calls missed (no answer): {g['not_answered']:,}
- Calls busy: {g['busy']:,}
- Calls failed: {g['failed']:,}
- Overall miss rate: {g['miss_rate_pct']}%
- Average call duration: {g['avg_duration_sec']} seconds ({g['avg_duration_min']} minutes)
- Unique callers: {g['unique_callers']:,}
- Average calls per day: {g['avg_calls_per_day']}

### Hourly Distribution (Busiest Hours)
{kpis['hourly'].sort_values('total', ascending=False).head(5).to_string()}

### Weekday Distribution
{kpis['weekday'].to_string()}

### Extension Performance (Who Answers the Most)
{kpis['extension'].to_string() if not kpis['extension'].empty else 'No data available'}

### Quarterly Trend
{kpis['quarterly'].to_string() if not kpis['quarterly'].empty else 'Single quarter only'}

### Top Callers (Most Frequent Numbers)
{kpis['top_callers'].head(5).to_string() if not kpis['top_callers'].empty else 'No data available'}
"""

    return context.strip()


def _build_prompt(context: str) -> str:
    """
    Construye el prompt que enviaremos a Claude.

    Prompt engineering: le damos un rol claro, le pasamos los datos
    como contexto, y le pedimos un formato específico de salida.
    Esto es exactamente lo que se hace en aplicaciones profesionales de IA.
    """

    prompt = f"""You are a senior data analyst specializing in healthcare operations, 
specifically dental clinic management. You have deep expertise in call center metrics 
and operational efficiency.

I'm providing you with Call Detail Record (CDR) KPIs from a dental clinic's phone system 
(Asterisk/FreePBX). These metrics have been calculated from deduplicated call records — 
each row represents one real call, not raw PBX records.

IMPORTANT: The KPIs only include INBOUND EXTERNAL calls (patients calling the clinic). 
Internal transfers and outbound calls have been filtered out.

Here are the KPIs:

{context}

Based on this data, generate an executive report in Markdown format with the following 
sections:

## Executive Summary
A 3-4 sentence high-level overview of the clinic's phone performance.

## Key Findings
The most important discoveries from the data, with specific numbers.

## Problems Detected
Issues ranked by business impact. For each problem, explain WHY it matters 
for a dental clinic specifically (lost patients = lost revenue).

## Actionable Recommendations
Concrete, practical actions the clinic manager can take. Be specific — 
don't just say "improve staffing", say exactly what to change and when.

## Next Steps
What additional data or analysis would help make better decisions.

Keep the language professional but accessible — the audience is a clinic manager, 
not a data scientist. Use the actual numbers from the KPIs to support every claim."""

    return prompt


def generate_report_with_ai(kpis: dict) -> str:
    """
    Genera el informe ejecutivo usando la API de Claude.

    Retorna:
        El informe en formato Markdown (string).
    """

    # Intentamos cargar la API Key desde el fichero .env
    # python-dotenv busca un fichero .env en el directorio actual
    # y carga las variables de entorno definidas en él.
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # Si no tiene python-dotenv, intentamos sin él

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key or api_key == "your-api-key-here":
        print("   ⚠️  No API Key found — using demo mode")
        return _demo_report(kpis)

    # ── Llamada real a la API de Claude ──
    try:
        import anthropic

        print("   🤖 Connecting to Claude API...")
        client = anthropic.Anthropic(api_key=api_key)

        context = _format_kpis_as_context(kpis)
        prompt = _build_prompt(context)

        # Esta es la llamada a la API.
        # model: qué versión de Claude usar
        # max_tokens: longitud máxima de la respuesta
        # messages: la conversación (en este caso, solo un mensaje del usuario)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )

        # La respuesta viene en response.content[0].text
        report = response.content[0].text
        print("   ✅ Report generated successfully with Claude API")
        return report

    except Exception as e:
        print(f"   ❌ API error: {e}")
        print("   ⚠️  Falling back to demo mode")
        return _demo_report(kpis)


def _demo_report(kpis: dict) -> str:
    """
    Genera un informe de ejemplo sin usar la API.

    Este informe se basa en los KPIs reales pero el texto está
    pregenerado. Sirve para que el proyecto funcione sin API Key
    y para que cualquiera que descargue el repo pueda ver un
    ejemplo de output.
    """

    g = kpis["general"]

    report = f"""# Dental Clinic CDR Analysis — Executive Report

> Auto-generated report based on {g['total_calls']:,} inbound calls analysis.
> Demo mode — generated without AI. Run with API key for AI-powered insights.

## Executive Summary

The dental clinic received **{g['total_calls']:,} inbound external calls** during the analysis period, 
with an overall answer rate of **{g['answer_rate_pct']}%** and an average call duration of 
**{g['avg_duration_min']} minutes**. A total of **{g['unique_callers']:,} unique callers** contacted the clinic, 
with approximately **{g['avg_calls_per_day']} calls per day** on average.

## Key Findings

1. **Answer Rate: {g['answer_rate_pct']}%** — {"Above" if g['answer_rate_pct'] >= 80 else "Below"} the industry benchmark of 80% for healthcare facilities.
2. **Miss Rate: {g['miss_rate_pct']}%** — {g['not_answered'] + g['busy'] + g['failed']:,} callers could not reach the clinic.
3. **Average Duration: {g['avg_duration_min']} min** — Within the expected range for dental clinic calls (appointment scheduling, confirmations).
4. **Daily Volume: {g['avg_calls_per_day']} calls/day** — This volume requires dedicated reception coverage during business hours.

## Problems Detected

### {"⚠️ High" if g['miss_rate_pct'] > 20 else "📊 Moderate" if g['miss_rate_pct'] > 10 else "✅ Low"} Call Loss Rate ({g['miss_rate_pct']}%)
Every missed call is a potential patient who may book with a competitor. 
At an estimated average value of €150-300 per new patient visit, 
even a {g['miss_rate_pct']}% miss rate represents significant revenue impact.

### Peak Hour Congestion
The hourly distribution shows concentrated call volumes during specific time slots. 
Reception staff may be overwhelmed during these peaks while underutilized during valleys.

## Actionable Recommendations

1. **Implement a callback system** for missed calls during peak hours — this recovers 
   up to 60% of lost calls according to healthcare industry data.
2. **Review staffing during peak hours** — ensure adequate reception coverage 
   during the busiest time slots identified in the hourly analysis.
3. **Set up a simple IVR** (Interactive Voice Response) to handle basic queries 
   (address, opening hours) automatically, freeing reception for appointment scheduling.
4. **Monitor weekly trends** — use this analysis tool regularly to track whether 
   changes in staffing or processes improve the answer rate.

## Next Steps

- Run this analysis monthly to track trends over time.
- Cross-reference missed calls with appointment booking data to quantify revenue impact.
- Analyze call duration patterns to identify opportunities for efficiency improvements.
- Consider implementing online booking to reduce phone dependency.

---
*Report generated by Dental Clinic CDR Analyzer — [github.com/vjsoriano83/dental-clinic-cdr-analyzer](https://github.com/vjsoriano83/dental-clinic-cdr-analyzer)*
"""

    print("   📝 Demo report generated (no API key)")
    return report


def generate_and_save_report(kpis: dict) -> str:
    """
    Genera el informe y lo guarda como fichero Markdown.

    Esta es la función principal que llamaremos desde main.py.
    """

    print("📝 Generando informe ejecutivo...")

    report = generate_report_with_ai(kpis)

    # Guardamos el informe
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "report_sample.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"   💾 Informe guardado en: output/report_sample.md")

    return report


# ── Si ejecutas este fichero directamente ──
if __name__ == "__main__":
    from src.ingest import load_and_process
    from src.kpis import compute_all_kpis

    calls = load_and_process()
    kpis = compute_all_kpis(calls)
    report = generate_and_save_report(kpis)

    print(f"\n{'='*50}")
    print("Primeras líneas del informe:")
    print("\n".join(report.split("\n")[:15]))