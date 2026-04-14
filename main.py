"""
Dental Clinic CDR Analyzer
============================
Script principal — ejecuta el pipeline completo:
  1. Carga y deduplica los datos CDR
  2. Calcula KPIs de negocio
  3. Genera gráficos
  4. Genera informe ejecutivo con IA

Uso:
    python3 main.py                        # Usa datos de ejemplo
    python3 main.py data/real_cdr.csv      # Usa tus propios datos
    python3 main.py "data/*.csv"           # Múltiples ficheros

Autor: Víctor Soriano Tárrega (@vjsoriano83)
"""

import sys
from src.ingest import load_and_process
from src.kpis import compute_all_kpis
from src.visualize import generate_all_charts
from src.ai_report import generate_and_save_report


def main():
    # Si el usuario pasa una ruta como argumento, usamos esa.
    # Si no, usamos el CSV de ejemplo.
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_cdr.csv"

    print("=" * 60)
    print("  DENTAL CLINIC CDR ANALYZER")
    print("=" * 60)
    print(f"  Fuente de datos: {data_path}\n")

    # ── Pipeline ──
    calls = load_and_process(data_path)
    print()

    kpis = compute_all_kpis(calls)
    print()

    generate_all_charts(calls, kpis)
    print()

    generate_and_save_report(kpis)

    print(f"\n{'=' * 60}")
    print("  ✅ ANÁLISIS COMPLETADO")
    print(f"  📊 Gráficos guardados en: output/charts/")
    print(f"  📝 Informe guardado en:   output/report_sample.md")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()