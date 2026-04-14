"""
Dental Clinic CDR Analyzer
============================
Main entry point — runs the full pipeline:
  1. Load and deduplicate CDR data
  2. Compute business KPIs
  3. Generate charts
  4. Generate AI-powered executive report

Usage:
    python3 main.py                        # Uses sample data
    python3 main.py data/real_cdr.csv      # Uses your own data
    python3 main.py "data/*.csv"           # Multiple files

Author: Víctor Soriano Tárrega (@vjsoriano83)
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
    print(f"  Data source: {data_path}\n")

    # ── Pipeline ──
    calls = load_and_process(data_path)
    print()

    kpis = compute_all_kpis(calls)
    print()

    generate_all_charts(calls, kpis)
    print()

    generate_and_save_report(kpis)

    print(f"\n{'=' * 60}")
    print("  ✅ ANALYSIS COMPLETE")
    print(f"  📊 Charts saved to: output/charts/")
    print(f"  📝 Report saved to: output/report_sample.md")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()