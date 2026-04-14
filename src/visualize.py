"""
visualize.py — Generación de gráficos
=======================================
Este módulo genera visualizaciones profesionales a partir de los KPIs.
Los gráficos se guardan como PNG en output/charts/.

Usamos matplotlib, la librería estándar de Python para gráficos.
Es la misma que se usa en ciencia de datos, investigación y en la industria.

Cada gráfico tiene:
- Un título descriptivo
- Etiquetas claras en los ejes
- Colores consistentes
- Anotaciones donde aportan contexto

Autor: Víctor Soriano Tárrega (@vjsoriano83)
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np
import os

# ── Configuración visual ──
# Definimos colores consistentes para todo el proyecto.
# Usar los mismos colores en todos los gráficos da aspecto profesional.
COLORS = {
    "answered": "#2ecc71",      # Verde — bueno, se contestó
    "not_answered": "#e74c3c",  # Rojo — malo, se perdió
    "busy": "#f39c12",          # Naranja — ocupado
    "failed": "#95a5a6",        # Gris — fallo técnico
    "primary": "#2c3e50",       # Azul oscuro — color principal
    "secondary": "#3498db",     # Azul claro — color secundario
}

# Carpeta donde se guardan los gráficos
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "charts")


def _ensure_output_dir():
    """Crea la carpeta de salida si no existe."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _save_and_close(fig, filename):
    """Guarda el gráfico como PNG y cierra la figura para liberar memoria."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"   📈 Guardado: {filename}")


def plot_disposition_pie(kpis: dict):
    """
    Gráfico de tarta: distribución de resultados de llamada.

    Muestra de un vistazo qué porcentaje se contesta, se pierde,
    está ocupado o falla. Es el gráfico más inmediato para un gerente.
    """

    g = kpis["general"]
    labels = []
    sizes = []
    colors = []

    # Solo añadimos segmentos que tengan valor > 0
    if g["answered"] > 0:
        labels.append(f"Answered\n({g['answered']:,})")
        sizes.append(g["answered"])
        colors.append(COLORS["answered"])
    if g["not_answered"] > 0:
        labels.append(f"No Answer\n({g['not_answered']:,})")
        sizes.append(g["not_answered"])
        colors.append(COLORS["not_answered"])
    if g["busy"] > 0:
        labels.append(f"Busy\n({g['busy']:,})")
        sizes.append(g["busy"])
        colors.append(COLORS["busy"])
    if g["failed"] > 0:
        labels.append(f"Failed\n({g['failed']:,})")
        sizes.append(g["failed"])
        colors.append(COLORS["failed"])

    fig, ax = plt.subplots(figsize=(8, 6))

    # autopct muestra el porcentaje dentro de cada segmento
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, textprops={"fontsize": 11}
    )

    # Hacemos los porcentajes más visibles
    for autotext in autotexts:
        autotext.set_fontweight("bold")
        autotext.set_fontsize(12)

    ax.set_title("Call Disposition Distribution", fontsize=14, fontweight="bold", pad=20)

    _save_and_close(fig, "01_disposition_pie.png")


def plot_hourly_bars(kpis: dict):
    """
    Gráfico de barras apiladas: llamadas por hora del día.

    Muestra los picos de actividad y diferencia las contestadas
    de las perdidas en cada franja horaria. Permite identificar
    las horas donde la clínica necesita más personal.
    """

    hourly = kpis["hourly"]

    fig, ax = plt.subplots(figsize=(12, 6))

    hours = hourly.index
    width = 0.7

    # Barras apiladas: primero las contestadas (verde), encima las perdidas (rojo)
    answered = hourly["ANSWERED"]
    missed = hourly["NO ANSWER"] + hourly.get("BUSY", 0) + hourly.get("FAILED", 0)

    ax.bar(hours, answered, width, label="Answered", color=COLORS["answered"])
    ax.bar(hours, missed, width, bottom=answered, label="Missed", color=COLORS["not_answered"], alpha=0.8)

    ax.set_xlabel("Hour of Day", fontsize=12)
    ax.set_ylabel("Number of Calls", fontsize=12)
    ax.set_title("Calls by Hour of Day (Answered vs Missed)", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)

    # Etiquetas del eje X: solo horas enteras
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45, ha="right")

    # Línea de cuadrícula horizontal suave para facilitar la lectura
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    _save_and_close(fig, "02_hourly_distribution.png")


def plot_weekday_bars(kpis: dict):
    """
    Gráfico de barras: llamadas por día de la semana.

    Revela patrones semanales: ¿los lunes son caóticos?
    ¿los viernes muertos? Ayuda a planificar personal.
    """

    weekday = kpis["weekday"]

    fig, ax = plt.subplots(figsize=(10, 6))

    days = weekday.index
    # Nombres cortos para el gráfico
    day_short = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed",
                 "Thursday": "Thu", "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun"}

    x = range(len(days))
    width = 0.35

    answered = weekday["ANSWERED"]
    missed = weekday["NO ANSWER"] + weekday.get("BUSY", 0) + weekday.get("FAILED", 0)

    ax.bar([i - width/2 for i in x], answered, width, label="Answered", color=COLORS["answered"])
    ax.bar([i + width/2 for i in x], missed, width, label="Missed", color=COLORS["not_answered"], alpha=0.8)

    ax.set_xlabel("Day of Week", fontsize=12)
    ax.set_ylabel("Number of Calls", fontsize=12)
    ax.set_title("Calls by Day of Week", fontsize=14, fontweight="bold")
    ax.set_xticks(list(x))
    ax.set_xticklabels([day_short.get(d, d) for d in days], fontsize=11)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    _save_and_close(fig, "03_weekday_distribution.png")


def plot_extension_performance(kpis: dict):
    """
    Gráfico de barras horizontales: rendimiento por extensión.

    Muestra quién contesta más y la duración media de sus llamadas.
    Si una extensión contesta el 50% y las demás se reparten el resto,
    hay un desequilibrio que puede causar burnout.
    """

    ext = kpis["extension"]

    if ext.empty:
        print("   ⚠️  No hay datos de extensiones — saltando gráfico")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Convertimos el índice a string para evitar problemas con floats
    ext_labels = [str(int(e)) if not pd.isna(e) else str(e) for e in ext.index]

    # Gráfico 1: llamadas contestadas por extensión
    bars1 = ax1.barh(ext_labels, ext["llamadas_contestadas"], color=COLORS["secondary"])
    ax1.set_xlabel("Calls Answered", fontsize=11)
    ax1.set_title("Calls Answered per Extension", fontsize=13, fontweight="bold")

    # Añadimos el porcentaje al lado de cada barra
    for bar, pct in zip(bars1, ext["pct_del_total"]):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f"{pct}%", va="center", fontsize=10)

    # Gráfico 2: duración media por extensión
    bars2 = ax2.barh(ext_labels, ext["duracion_media"], color=COLORS["primary"])
    ax2.set_xlabel("Avg Duration (seconds)", fontsize=11)
    ax2.set_title("Avg Call Duration per Extension", fontsize=13, fontweight="bold")

    for bar, dur in zip(bars2, ext["duracion_media"]):
        ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f"{dur:.0f}s", va="center", fontsize=10)

    fig.tight_layout()
    _save_and_close(fig, "04_extension_performance.png")


def plot_heatmap(df: pd.DataFrame):
    """
    Heatmap: mapa de calor de llamadas por día y hora.

    Es el gráfico más visual del proyecto. Las celdas más "calientes"
    (oscuras) muestran los momentos críticos. De un vistazo se ve
    cuándo la clínica está más presionada.
    """

    # Creamos una tabla pivote: filas = día de la semana, columnas = hora
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    day_short = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed",
                 "Thursday": "Thu", "Friday": "Fri"}

    # Filtramos solo días laborables
    df_work = df[df["weekday"].isin(day_order)]

    # Tabla pivote con el conteo de llamadas
    pivot = df_work.pivot_table(
        index="weekday", columns="hour", values="disposition",
        aggfunc="count", fill_value=0
    )

    # Reordenamos los días
    existing_days = [d for d in day_order if d in pivot.index]
    pivot = pivot.reindex(existing_days)

    fig, ax = plt.subplots(figsize=(14, 5))

    # imshow() muestra la tabla como un mapa de calor
    im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")

    # Etiquetas de los ejes
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{h:02d}:00" for h in pivot.columns], rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([day_short.get(d, d) for d in pivot.index])

    # Añadimos el número dentro de cada celda
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            value = pivot.values[i, j]
            # Texto blanco si la celda es oscura, negro si es clara
            text_color = "white" if value > pivot.values.max() * 0.65 else "black"
            ax.text(j, i, f"{value:.0f}", ha="center", va="center",
                   fontsize=8, color=text_color, fontweight="bold")

    ax.set_title("Call Volume Heatmap (Day × Hour)", fontsize=14, fontweight="bold")

    # Barra de color a la derecha
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Number of Calls", fontsize=11)

    fig.tight_layout()
    _save_and_close(fig, "05_heatmap_day_hour.png")


def generate_all_charts(df: pd.DataFrame, kpis: dict):
    """
    Genera todos los gráficos del proyecto.

    Parámetros:
        df: DataFrame deduplicado (para el heatmap)
        kpis: diccionario de KPIs (salida de compute_all_kpis)
    """

    _ensure_output_dir()

    print("📈 Generando gráficos...")
    plot_disposition_pie(kpis)
    plot_hourly_bars(kpis)
    plot_weekday_bars(kpis)
    plot_extension_performance(kpis)
    plot_heatmap(df)
    print(f"   ✅ {5} gráficos generados en output/charts/")


# ── Si ejecutas este fichero directamente ──
if __name__ == "__main__":
    from src.ingest import load_and_process
    from src.kpis import compute_all_kpis

    calls = load_and_process()
    kpis = compute_all_kpis(calls)
    generate_all_charts(calls, kpis)