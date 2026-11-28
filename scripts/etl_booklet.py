"""Regenera las escenas del booklet desde las copias oficiales del repositorio."""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd
from shapely import orient_polygons
from shapely.geometry import MultiPoint, mapping

import enriquecer_atus as espacial
import transformar_atus as tabular


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "datos/originales"
CENSO = ORIGINAL / "censo-2020/poblacion_ageb_31050.csv"
CENSO_FUENTE = CENSO.with_name("fuente.json")
CENSO_URL = (
    "https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/"
    "ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip"
)
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
TIPOS = {
    "1": "Colisión con vehículo automotor", "2": "Colisión con peatón",
    "3": "Colisión con animal", "4": "Colisión con objeto fijo", "5": "Volcadura",
    "6": "Caída de pasajero", "7": "Salida del camino", "8": "Incendio",
    "9": "Colisión con ferrocarril", "10": "Colisión con motocicleta",
    "11": "Colisión con ciclista", "12": "Otro",
}
ESTADO_UNICO = {"interior", "borde_unico"}
VIA_ZOOM = "Periférico Lic. Manuel Berzunza"
GRID_M = 100


def leer_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def guardar_json(path, data, *, compact=False):
    kwargs = {"separators": (",", ":")} if compact else {"indent": 2}
    path.write_text(json.dumps(data, ensure_ascii=False, **kwargs) + "\n", encoding="utf-8", newline="\n")


def guardar_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def verificar_hash(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"La copia de {path.name} no coincide con su SHA-256.")


def importar_censo(path):
    """Extrae solo totales de AGEB urbanas de Mérida de la descarga oficial."""
    with ZipFile(path) as archive:
        members = [
            name for name in archive.namelist()
            if "/conjunto_de_datos/" in name and name.endswith(".csv")
        ]
        if len(members) != 1:
            raise ValueError("Se esperaba un solo CSV de datos censales en el ZIP.")
        member = members[0]
        with archive.open(member) as raw:
            rows = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            records = [
                (row["ENTIDAD"] + row["MUN"] + row["LOC"] + row["AGEB"], row["POBTOT"])
                for row in rows
                if row["ENTIDAD"] == "31" and row["MUN"] == "050"
                and row["MZA"] == "000" and row["AGEB"] != "0000"
            ]
    if not records or len({key for key, _ in records}) != len(records):
        raise ValueError("El recorte censal está vacío o contiene claves duplicadas.")
    CENSO.parent.mkdir(parents=True, exist_ok=True)
    guardar_csv(CENSO, ["cvegeo_ageb", "poblacion_2020"], sorted(records))
    guardar_json(CENSO_FUENTE, {
        "institucion": "INEGI",
        "conjunto": "Censo de Población y Vivienda 2020. Resultados por AGEB y manzana urbana, Yucatán",
        "url": CENSO_URL,
        "archivo_zip": member,
        "sha256_zip": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sha256_recorte": hashlib.sha256(CENSO.read_bytes()).hexdigest(),
        "filtros": {"ENTIDAD": "31", "MUN": "050", "MZA": "000", "AGEB": "distinta de 0000"},
        "filas": len(records),
    })


def insumos_atus():
    raw_path = ORIGINAL / "atus/accidentes_merida.geojson"
    source = leer_json(raw_path.with_suffix(".fuente.json"))
    verificar_hash(raw_path, source["sha256"])
    geometria = espacial.acquire()
    urban, rural, municipal = (espacial.read_layer(key) for key in ("agebu", "agebr", "mgem"))
    base, _duplicates = tabular.transform(tabular.read_properties(raw_path))
    base, _ = tabular.enrich_catalogs(base, {})
    select = (
        base["EDO"].astype(str).eq("31") & base["MPIO"].astype(str).eq("50")
        & base["ANIO"].astype(str).isin(["2021", "2022", "2023", "2024"])
    )
    if not select.all() or len(base) != source["numberMatched"]:
        raise ValueError("El recorte ATUS no coincide con el ámbito o con el conteo de su manifiesto.")
    ageb = gpd.GeoDataFrame(pd.concat([urban, rural], ignore_index=True), crs=urban.crs)
    enriched, _ = espacial.enrich(base, ageb, municipal)
    enriched["FUENTE_GEOGRAFICA"] = geometria["agebu"]["metadatos"]["Fuente_informacion_vectorial"]
    enriched["CONSULTA_GEOGRAFICA_UTC"] = geometria["agebu"]["consulta_utc"]
    return base, enriched, urban, municipal


def poblaciones(urban):
    source = leer_json(CENSO_FUENTE)
    verificar_hash(CENSO, source["sha256_recorte"])
    with CENSO.open(encoding="utf-8", newline="") as stream:
        table = list(csv.DictReader(stream))
    values = {row["cvegeo_ageb"]: row["poblacion_2020"] for row in table}
    if len(table) != len(values) or len(table) != source["filas"]:
        raise ValueError("Las filas censales no coinciden con su manifiesto.")
    # El Marco atribuye su campo pob_total al Censo 2020. Solo se acepta
    # un denominador cuando la clave y el valor coinciden en ambas fuentes.
    result = {}
    for record in urban.itertuples():
        val = values.get(record.cvegeo)
        if val is None:
            result[record.cvegeo] = (None, "sin_clave_censo")
        elif val != str(record.pob_total):
            result[record.cvegeo] = (None, "poblacion_no_coincide")
        elif not val.isascii() or not val.isdecimal() or int(val) <= 0:
            result[record.cvegeo] = (None, "sin_poblacion_positiva")
        else:
            result[record.cvegeo] = (int(val), "calculable")
    return result


def mapas(destino, enriched, urban, municipal):
    selected = enriched[
        enriched["TIPO_AGEB"].eq("urbana") & enriched["ESTADO_UNION_AGEB"].isin(ESTADO_UNICO)
    ]
    counts = Counter(selected["CVEGEO"])
    area = urban.to_crs("EPSG:32616").area / 1_000_000
    if not (area > 0).all():
        raise ValueError("Se encontraron AGEB urbanas sin superficie calculable.")
    pop = poblaciones(urban)
    density, rate = [], []
    for key, km2 in sorted(zip(urban["cvegeo"], area, strict=True)):
        count = counts[key]
        population, status = pop[key]
        density.append((key, count, f"{km2:.8f}", f"{count / km2:.6f}"))
        rate.append((
            key, count, population, f"{count * 1000 / population:.6f}" if population else "", status
        ))
    focal_key = max(density, key=lambda row: float(row[3]))[0]
    focal = selected[selected["CVEGEO"].eq(focal_key)]
    columns = [focal[field].astype("string").str.contains(r"\bMANUEL BERZUNZA\b", na=False)
               for field in ("CALLE1", "CALLE2")]
    vial = focal[columns[0] | columns[1]]
    if vial.empty:
        raise ValueError("Ya no hay registros de la vialidad documentada en el área de enfoque.")
    guardar_csv(destino / "escena-1.csv", [
        "cvegeo_ageb", "accidentes", "superficie_km2", "accidentes_por_km2",
        "via_del_acercamiento", "registros_que_mencionan_la_via",
    ], [(*row, VIA_ZOOM, len(vial)) if row[0] == focal_key else (*row, "", "") for row in density])
    guardar_csv(destino / "escena-2.csv", [
        "cvegeo_ageb", "accidentes", "poblacion_2020", "accidentes_por_1000_habitantes", "estado_denominador"
    ], rate)
    # La simplificación se usa exclusivamente para dibujar. Las superficies y
    # las asignaciones se calcularon con los polígonos originales completos.
    features = []
    for label, layer in (("urbana", urban), ("municipio", municipal)):
        simple = layer.to_crs("EPSG:32616").geometry.simplify(12, preserve_topology=True).to_crs("EPSG:4326")
        for key, geom in zip(layer["cvegeo"], simple, strict=True):
            d3_geom = orient_polygons(geom, exterior_cw=True)
            features.append({
                "type": "Feature",
                "properties": {"cvegeo": key, "capa": label},
                "geometry": mapping(d3_geom),
            })
    marco_dir = espacial.SOURCES
    state_path = marco_dir / "mgee_31.geojson"
    state_source = leer_json(marco_dir / "fuentes.json")["mgee"]
    verificar_hash(state_path, state_source["sha256"])
    state = gpd.GeoDataFrame.from_features(leer_json(state_path)["features"], crs="EPSG:4326")
    if len(state) != 1 or state.iloc[0].cvegeo != "31" or not state.geometry.is_valid.all():
        raise ValueError("El contorno estatal no es un polígono válido de Yucatán.")
    state_geom = state.to_crs("EPSG:32616").geometry.simplify(450, preserve_topology=True).to_crs("EPSG:4326").iloc[0]
    features.append({
        "type": "Feature", "properties": {"cvegeo": "31", "capa": "estado"},
        "geometry": mapping(orient_polygons(state_geom, exterior_cw=True)),
    })

    # La vista de calle muestra celdas con registros, no posiciones individuales ni una línea vial.
    coords = gpd.GeoSeries(gpd.points_from_xy(vial["LONGITUD"], vial["LATITUD"]), crs="EPSG:4326").to_crs("EPSG:32616")
    indices = {(int(point.x // GRID_M), int(point.y // GRID_M)) for point in coords}
    centers = [((col + 0.5) * GRID_M, (row + 0.5) * GRID_M) for col, row in sorted(indices)]
    groups = gpd.GeoSeries([MultiPoint(centers)], crs="EPSG:32616").to_crs("EPSG:4326").iloc[0]
    features.append({
        "type": "Feature", "properties": {"cvegeo": focal_key, "capa": "celdas_via"},
        "geometry": mapping(groups),
    })
    guardar_json(destino / "mapa-base.geojson", {"type": "FeatureCollection", "features": features}, compact=True)
    areas_validas = [row for row in rate if row[-1] == "calculable"]
    return {
        "ageb_urbanas": len(urban),
        "accidentes_ageb_urbana": len(selected),
        "accidentes_ageb_rural": int(enriched["TIPO_AGEB"].eq("rural").sum()),
        "accidentes_ageb_multiple": int(enriched["ESTADO_UNION_AGEB"].eq("multiple").sum()),
        "accidentes_sin_ageb": int(enriched["ESTADO_UNION_AGEB"].isin(["sin_coincidencia", "coordenada_invalida"]).sum()),
        "ageb_tasa_calculable": len(areas_validas),
        "ageb_estado_denominador": dict(sorted(Counter(row[-1] for row in rate).items())),
        "accidentes_en_ageb_con_denominador": sum(row[1] for row in areas_validas),
        "acercamiento_vial": {"cvegeo_ageb": focal_key, "registros": len(vial), "celdas_de_100_m": len(centers)},
    }


def tiempos(destino, base):
    hours = pd.to_numeric(base["HORA"], errors="coerce")
    valid = base["FECHA"].notna() & hours.between(0, 23) & hours.mod(1).eq(0)
    weekday = base.loc[valid, "FECHA"].dt.dayofweek
    counts = Counter(zip(weekday, hours[valid].astype(int), strict=True))
    rows = [(day, DIAS[day - 1], hour, counts[day - 1, hour])
            for day in range(1, 8) for hour in range(24)]
    guardar_csv(destino / "escena-3.csv", ["orden_dia", "dia_semana", "hora_local", "accidentes"], rows)
    return {"registros_con_fecha_y_hora": int(valid.sum()), "registros_sin_fecha_u_hora": int((~valid).sum())}


def tipos(destino, base):
    codes = base["TIPACCID"].astype("string").fillna("")
    counts = Counter(codes)
    rows = [
        (code, TIPOS.get(code, f"Código {code}" if code else "Sin tipo informado"), count)
        for code, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    ]
    guardar_csv(destino / "escena-4.csv", ["codigo_tipaccid", "tipo_accidente", "accidentes"], rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=ROOT / "booklet/datos")
    parser.add_argument("--censo-zip", type=Path, help="Generar el recorte censal a partir del ZIP original.")
    parser.add_argument("--tablas-atus", type=Path, help="Exportar también el CSV limpio y el enriquecido a esta carpeta.")
    args = parser.parse_args()
    if args.censo_zip:
        importar_censo(args.censo_zip)
    base, enriched, urban, municipal = insumos_atus()
    args.salida.mkdir(parents=True, exist_ok=True)
    summary = {"accidentes_total": len(base), "periodo": [2021, 2024]}
    summary.update(mapas(args.salida, enriched, urban, municipal))
    summary.update(tiempos(args.salida, base))
    tipos(args.salida, base)
    if args.tablas_atus:
        args.tablas_atus.mkdir(parents=True, exist_ok=True)
        for table, name in ((base, "accidentes_merida.csv"), (enriched, "accidentes_merida_enriquecido.csv")):
            table.to_csv(args.tablas_atus / name, index=False, encoding="utf-8", date_format="%Y-%m-%d", na_rep="")
    guardar_json(args.salida / "control.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
