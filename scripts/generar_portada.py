"""Regenera assets/portada.png a partir de ATUS y el Marco Geoestadístico."""

import argparse
import csv
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]
FUENTES = ROOT / "datos/originales/marco-geoestadistico"
PROYECCION = Transformer.from_crs(4326, 32616, always_xy=True)


def anillos_proyectados(filename):
    data = json.loads((FUENTES / filename).read_text(encoding="utf-8-sig"))
    for feature in data["features"]:
        geo = feature["geometry"]
        polygons = [geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"]
        for polygon in polygons:
            for ring in polygon:
                coords = np.asarray(ring)
                yield np.column_stack(PROYECCION.transform(coords[:, 0], coords[:, 1]))


def fuentes(portable):
    windows = os.environ.get("WINDIR")
    if windows and not portable:
        base = Path(windows) / "Fonts"
        paths = [base / name for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf")]
        if all(path.is_file() for path in paths):
            return [FontProperties(fname=path) for path in paths]
    return [
        FontProperties(family="DejaVu Sans"),
        FontProperties(family="DejaVu Sans", weight="bold"),
        FontProperties(family="DejaVu Sans Mono"),
    ]


def generar(salida, portable=False):
    boundary = list(anillos_proyectados("mgem_31050.geojson"))
    urban = list(anillos_proyectados("agebu_31050.geojson"))
    with (ROOT / "datos/para-etl/atus/accidentes_merida.csv").open(encoding="utf-8-sig", newline="") as file:
        records = list(csv.DictReader(file))
    x, y = PROYECCION.transform([float(row["LONGITUD"]) for row in records],
                               [float(row["LATITUD"]) for row in records])
    years = sorted({int(row["ANIO"]) for row in records})

    bg, panel, border = "#101B22", "#14272C", "#2E494D"
    offwhite, pale, accent = "#F5F2EA", "#C4D1CD", "#F6C878"
    fig = plt.figure(figsize=(12, 5), dpi=144, facecolor=bg)
    regular, bold, mono = fuentes(portable)

    def label(x, y, text, font, size, color, **kwargs):
        return fig.text(x, y, text, fontproperties=font, fontsize=size,
                        color=color, va="center", **kwargs)

    layout = fig.add_axes([0, 0, 1, 1], xlim=(0, 1), ylim=(0, 1))
    layout.set_axis_off()
    layout.add_patch(Rectangle((0.057, 0.806), 0.026, 0.010, color=accent, lw=0, transform=layout.transAxes))
    label(0.094, 0.812, "MÉRIDA, YUCATÁN", mono, 12, accent)
    label(0.057, 0.634, "¿Dónde se nos", bold, 39, offwhite)
    label(0.057, 0.501, "complica el volante?", bold, 36 if portable else 39, offwhite)
    layout.plot([0.059, 0.484], [0.373, 0.373], color=border, lw=1.2, transform=layout.transAxes)
    label(0.057, 0.239, f"{len(records):,}", bold, 39, accent)
    label(0.238, 0.242, f"registros de accidentes\nINEGI ATUS · {years[0]}–{years[-1]}",
          regular, 13, pale, linespacing=1.45)
    layout.add_patch(FancyBboxPatch((0.535, 0.081), 0.413, 0.839,
                                   boxstyle="round,pad=0.008,rounding_size=0.017",
                                   facecolor=panel, edgecolor=border, linewidth=1.1,
                                   transform=layout.transAxes))
    label(0.560, 0.860, "UBICACIONES REGISTRADAS", mono, 10, pale)

    ax = fig.add_axes([0.552, 0.177, 0.380, 0.645], facecolor="none")
    ax.set_axis_off()
    whole = np.vstack(boundary)
    xmin, ymin = whole.min(axis=0) - 1800
    xmax, ymax = whole.max(axis=0) + 1800
    ax.set(xlim=(xmin, xmax), ylim=(ymin, ymax), aspect="equal")
    for grid_x in np.arange(np.ceil(xmin / 8000) * 8000, xmax, 8000):
        ax.axvline(grid_x, color=border, alpha=0.45, lw=0.5, zorder=1)
    for grid_y in np.arange(np.ceil(ymin / 8000) * 8000, ymax, 8000):
        ax.axhline(grid_y, color=border, alpha=0.45, lw=0.5, zorder=1)
    ax.add_collection(LineCollection(urban, colors="#42635F", linewidths=0.26, alpha=0.8, zorder=2))
    ax.add_collection(LineCollection(boundary, colors="#7A9D95", linewidths=0.9, zorder=3))
    unique_locations = np.unique(np.column_stack((x, y)), axis=0)
    ax.scatter(unique_locations[:, 0], unique_locations[:, 1], s=2.2,
               color=accent, alpha=0.60, linewidths=0, zorder=4)
    layout.scatter([0.563], [0.135], s=11, color=accent, transform=layout.transAxes, linewidths=0)
    label(0.575, 0.135, "Ubicación ATUS", regular, 10, pale)
    layout.plot([0.734, 0.751], [0.135, 0.135], color="#7A9D95", lw=1.1, transform=layout.transAxes)
    label(0.759, 0.135, "Límite municipal", regular, 10, pale)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, dpi=144, facecolor=bg, metadata={
        "Title": "Accidentes viales en Mérida",
        "Source": "INEGI ATUS 2021–2024 y Marco Geoestadístico, diciembre de 2025",
    })
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=ROOT / "assets/portada.png")
    parser.add_argument("--portable", action="store_true", help="Usar fuentes DejaVu en cualquier sistema.")
    args = parser.parse_args()
    generar(args.salida, args.portable or not os.environ.get("WINDIR"))
