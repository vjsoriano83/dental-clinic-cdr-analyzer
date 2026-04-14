"""
ai_report.py — Generación de informe ejecutivo con IA
======================================================
Este módulo usa la API de Claude (Anthropic) para analizar los KPIs
de la clínica y generar un informe ejecutivo con recomendaciones.

¿Cómo funciona?
    1. Tomamos los KPIs calculados por kpis.py
    2. Los formateamos como texto estructurado (el "contexto")
    3. Construimos un prompt con instrucciones para Claude
    4. Enviamos prompt + contexto a la API
    5. Claude devuelve un informe en Markdown
    6. Guardamos el informe en output/report_sample.md

Esto es una aplicación práctica de IA generativa:
    - LLM: usamos Claude como modelo de lenguaje
    - Prompt engineering: diseñamos el prompt para un informe estructurado
    - Contexto (mini-RAG): le damos datos específicos para que no alucine

Modos:
    - Con API Key: genera un informe real llamando a Claude
    - Sin API Key: carga un informe demo pregenerado

Autor: Víctor Soriano Tárrega (@vjsoriano83)
"""

import os

# Carpeta de salida
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def _format_kpis_as_context(kpis: dict) -> str:
    """
    Convierte los KPIs a texto estructurado para Claude.

    Le damos los datos organizados por secciones para que genere
    un informe coherente basado en información real.
    """

    g = kpis["general"]

    context = f"""
## KPIs DEL CENTRO DE LLAMADAS — CLÍNICA DENTAL

### Métricas generales (solo llamadas entrantes externas)
- Total llamadas entrantes: {g['total_calls']:,}
- Contestadas por persona: {g['answered']:,} ({g['answer_rate_pct']}%)
- Derivadas a buzón de voz: {g['voicemail']:,} ({g['voicemail_rate_pct']}%)
- No contestadas: {g['not_answered']:,}
- Línea ocupada: {g['busy']:,}
- Fallidas: {g['failed']:,}
- Tasa de pérdida (sin buzón): {g['miss_rate_pct']}%
- Duración media de conversación: {g['avg_duration_sec']} seg ({g['avg_duration_min']} min)
- Llamantes únicos: {g['unique_callers']:,}
- Media de llamadas por día: {g['avg_calls_per_day']}

### Distribución por hora (horas con más tráfico)
{kpis['hourly'].sort_values('total', ascending=False).head(5).to_string()}

### Distribución por día de la semana
{kpis['weekday'].to_string()}

### Rendimiento por extensión (quién contesta)
{kpis['extension'].to_string() if not kpis['extension'].empty else 'Sin datos'}

### Evolución trimestral
{kpis['quarterly'].to_string() if not kpis['quarterly'].empty else 'Solo un trimestre'}

### Llamantes más frecuentes
{kpis['top_callers'].head(5).to_string() if not kpis['top_callers'].empty else 'Sin datos'}
"""

    return context.strip()


def _build_prompt(context: str) -> str:
    """
    Construye el prompt para Claude.

    Prompt engineering: rol claro, datos como contexto, formato de salida definido.
    """

    prompt = f"""Eres un analista de datos senior especializado en operaciones de 
clínicas dentales. Tienes experiencia en métricas de call center y eficiencia operativa.

Te proporciono los KPIs de los registros de llamadas (CDR) de la centralita 
Asterisk/FreePBX de una clínica dental. Estas métricas se han calculado a partir 
de registros deduplicados — cada fila representa una llamada real, no registros 
brutos de la PBX.

IMPORTANTE: 
- Los KPIs solo incluyen llamadas ENTRANTES EXTERNAS (pacientes llamando a la clínica).
- Las transferencias internas y llamadas salientes se han filtrado.
- Las llamadas al buzón de voz se contabilizan por separado.
- La clínica tiene recepción (ext 201, 221) y gabinetes (ext 222-227) configurados 
  en ring group. Los gabinetes atienden por desbordamiento cuando recepción no puede.

Aquí están los KPIs:

{context}

Genera un informe ejecutivo en Markdown en ESPAÑOL con las siguientes secciones:

## Resumen ejecutivo
3-4 frases con la visión general del rendimiento telefónico de la clínica.

## Hallazgos clave
Los descubrimientos más importantes, con cifras concretas.

## Problemas detectados
Problemas ordenados por impacto en el negocio. Para cada uno, explica POR QUÉ 
importa para una clínica dental (llamada perdida = paciente perdido = ingreso perdido).

## Recomendaciones accionables
Acciones concretas y prácticas que el gerente puede implementar. Sé específico — 
no digas solo "mejorar la plantilla", di exactamente qué cambiar y cuándo.

## Próximos pasos
Qué datos o análisis adicionales ayudarían a tomar mejores decisiones.

Usa un lenguaje profesional pero accesible — la audiencia es el gerente de la clínica, 
no un científico de datos. Apoya cada afirmación con cifras reales de los KPIs."""

    return prompt


def generate_report_with_ai(kpis: dict) -> str:
    """
    Genera el informe ejecutivo usando la API de Claude.

    Si no hay API Key configurada, genera un informe demo.
    """

    # Intentamos cargar la API Key desde el fichero .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key or api_key == "your-api-key-here":
        print("   ⚠️  No se encontró API Key — usando modo demo")
        return _demo_report(kpis)

    # ── Llamada real a la API de Claude ──
    try:
        import anthropic

        print("   🤖 Conectando con la API de Claude...")
        client = anthropic.Anthropic(api_key=api_key)

        context = _format_kpis_as_context(kpis)
        prompt = _build_prompt(context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )

        report = response.content[0].text
        print("   ✅ Informe generado con Claude API")
        return report

    except Exception as e:
        print(f"   ❌ Error de API: {e}")
        print("   ⚠️  Usando modo demo como alternativa")
        return _demo_report(kpis)


def _demo_report(kpis: dict) -> str:
    """
    Genera un informe de ejemplo sin usar la API.

    Usa los KPIs reales pero el texto es plantilla.
    Sirve para que el proyecto funcione sin API Key.
    """

    g = kpis["general"]

    report = f"""# Análisis CDR Clínica Dental — Informe Ejecutivo

> Informe generado a partir del análisis de {g['total_calls']:,} llamadas entrantes.
> Modo demo — generado sin IA. Ejecuta con API Key para obtener análisis con IA.

## Resumen ejecutivo

La clínica recibió **{g['total_calls']:,} llamadas entrantes externas** durante el periodo analizado, 
con una tasa de contestación del **{g['answer_rate_pct']}%** y una duración media de conversación de 
**{g['avg_duration_min']} minutos**. Un total de **{g['unique_callers']:,} llamantes únicos** contactaron 
con la clínica, con una media de **{g['avg_calls_per_day']} llamadas diarias**. 
El **{g['voicemail_rate_pct']}%** de las llamadas fueron derivadas al buzón de voz.

## Hallazgos clave

1. **Tasa de contestación: {g['answer_rate_pct']}%** — {"Por encima" if g['answer_rate_pct'] >= 80 else "Por debajo"} del benchmark del sector sanitario (80%).
2. **Tasa de pérdida: {g['miss_rate_pct']}%** — {g['not_answered'] + g['busy'] + g['failed']:,} llamantes no pudieron contactar con la clínica.
3. **Buzón de voz: {g['voicemail_rate_pct']}%** — {g['voicemail']:,} llamadas fueron derivadas al buzón cuando nadie pudo atender.
4. **Duración media: {g['avg_duration_min']} min** — Dentro del rango esperado para llamadas de clínica dental (pedir cita, confirmar, consultar dirección).
5. **Volumen diario: {g['avg_calls_per_day']} llamadas/día** — Requiere cobertura dedicada de recepción durante horario comercial.

## Problemas detectados

### {"⚠️ Alta" if g['miss_rate_pct'] > 20 else "📊 Moderada" if g['miss_rate_pct'] > 10 else "✅ Baja"} tasa de llamadas perdidas ({g['miss_rate_pct']}%)
Cada llamada perdida es un paciente potencial que puede reservar con la competencia. 
Con un valor medio estimado de 150-300€ por primera visita, incluso un {g['miss_rate_pct']}% 
de pérdida representa un impacto significativo en facturación.

### Congestión en horas punta
La distribución horaria muestra picos de volumen concentrados en franjas específicas. 
El personal de recepción puede verse desbordado en estos picos mientras está infrautilizado 
en los valles.

### Derivación a buzón de voz ({g['voicemail_rate_pct']}%)
Las llamadas al buzón de voz indican que la recepción no da abasto en ciertos momentos. 
Muchos pacientes no dejan mensaje y simplemente cuelgan, lo que equivale a una llamada perdida.

## Recomendaciones accionables

1. **Implementar un sistema de callback** para llamadas perdidas en horas punta — esto recupera 
   hasta un 60% de llamadas perdidas según datos del sector sanitario.
2. **Revisar plantilla en horas punta** — asegurar cobertura adecuada de recepción 
   durante las franjas con más tráfico identificadas en el análisis horario.
3. **Configurar un IVR básico** (respuesta automática) para consultas frecuentes 
   (dirección, horario), liberando a recepción para gestión de citas.
4. **Monitorizar tendencias semanales** — usar esta herramienta de análisis periódicamente 
   para comprobar si los cambios de personal o procesos mejoran la tasa de contestación.

## Próximos pasos

- Ejecutar este análisis mensualmente para detectar tendencias.
- Cruzar llamadas perdidas con datos de reservas para cuantificar el impacto en facturación.
- Analizar patrones de duración para detectar oportunidades de eficiencia.
- Valorar la implementación de citas online para reducir la dependencia del teléfono.

---
*Informe generado por Dental Clinic CDR Analyzer — [github.com/vjsoriano83/dental-clinic-cdr-analyzer](https://github.com/vjsoriano83/dental-clinic-cdr-analyzer)*
"""

    print("   📝 Informe demo generado (sin API Key)")
    return report


def generate_and_save_report(kpis: dict) -> str:
    """
    Genera el informe y lo guarda como Markdown.

    Función principal — se llama desde main.py.
    """

    print("📝 Generando informe ejecutivo...")

    report = generate_report_with_ai(kpis)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "report_sample.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"   💾 Informe guardado en: output/report_sample.md")

    return report


# ── Ejecución directa para pruebas ──
if __name__ == "__main__":
    from src.ingest import load_and_process
    from src.kpis import compute_all_kpis

    calls = load_and_process()
    kpis = compute_all_kpis(calls)
    report = generate_and_save_report(kpis)

    print(f"\n{'='*50}")
    print("Primeras líneas del informe:")
    print("\n".join(report.split("\n")[:15]))