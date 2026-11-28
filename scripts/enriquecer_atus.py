"""Une accidentes a AGEB y municipio oficiales, sin aproximaciones por nombre."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "datos/para-etl/atus/accidentes_merida.csv"
OUTPUT = ROOT / "datos/para-etl/atus/accidentes_merida_enriquecido.csv"
SOURCES = ROOT / "datos/originales/marco-geoestadistico"
URLS = {kind: f"https://gaia.inegi.org.mx/wscatgeo/v2/geo/{kind}/31/050"
        for kind in ("agebu", "agebr", "mgem")}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acquire(refresh=False):
    manifest_path = SOURCES / "fuentes.json"
    if not refresh and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for kind in URLS:
            if digest(SOURCES / f"{kind}_31050.geojson") != manifest[kind]["sha256"]:
                raise ValueError(f"La fuente local {kind} cambió respecto al manifiesto.")
        return manifest
    SOURCES.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with requests.Session() as session:
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retry))
        for kind, url in URLS.items():
            print(f"Descargando fuente oficial: {url}", flush=True)
            response = session.get(url, timeout=(15, 90))
            response.raise_for_status()
            payload = response.json()
            if response.status_code != 200 or payload.get("type") != "FeatureCollection" or not payload.get("features"):
                raise ValueError(f"Respuesta geográfica inválida: {kind}")
            if payload.get("totalReg") != len(payload["features"]):
                raise ValueError(f"Conteo incompleto en {kind}.")
            path = SOURCES / f"{kind}_31050.geojson"
            path.write_bytes(response.content)
            manifest[kind] = {"url": url, "consulta_utc": datetime.now(timezone.utc).isoformat(),
                              "sha256": digest(path), "features": len(payload["features"]),
                              "metadatos": payload.get("metadatos", {}),
                              "crs": payload.get("crs", "EPSG:4326, convención GeoJSON sin miembro crs")}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def read_layer(kind):
    payload = json.loads((SOURCES / f"{kind}_31050.geojson").read_text(encoding="utf-8"))
    crs = payload.get("crs", {}).get("properties", {}).get("name", "EPSG:4326")
    layer = gpd.GeoDataFrame.from_features(payload["features"], crs=crs).to_crs("EPSG:4326")
    if not {"cvegeo", "cve_ent", "cve_mun"}.issubset(layer.columns):
        raise ValueError(f"Faltan claves en {kind}.")
    if not (layer.cve_ent.eq("31") & layer.cve_mun.eq("050")).all():
        raise ValueError(f"La capa {kind} contiene otra entidad/municipio.")
    if (layer.cvegeo.isna().any() or layer.cvegeo.duplicated().any()
            or layer.geometry.isna().any() or layer.geometry.is_empty.any()
            or not layer.geometry.is_valid.all()
            or not layer.geom_type.isin(["Polygon", "MultiPolygon"]).all()):
        raise ValueError(f"Geometrías o claves inválidas en {kind}; no se reparan silenciosamente.")
    if kind != "mgem":
        if not layer.cve_ageb.astype(str).str.fullmatch(r"[0-9A-Z]{4}").all():
            raise ValueError("Formato de AGEB inesperado.")
        expected = layer.cve_ent + layer.cve_mun
        if kind == "agebu":
            expected += layer.cve_loc
        expected += layer.cve_ageb
        if not expected.eq(layer.cvegeo).all():
            raise ValueError("CVEGEO no coincide con sus componentes oficiales.")
        layer["tipo_ageb"] = "urbana" if kind == "agebu" else "rural"
    return layer


def spatial_matches(points, polygons):
    """Interiores primero; bordes solo si no existe una coincidencia interior."""
    if points.crs is None or polygons.crs is None:
        raise ValueError("Ambas capas requieren CRS declarado.")
    polygons = polygons.to_crs(points.crs)
    inside = gpd.sjoin(points[["geometry"]], polygons, how="inner", predicate="within")
    inside["predicado"] = "within"
    unmatched = points.loc[~points.index.isin(inside.index)]
    edges = gpd.sjoin(unmatched[["geometry"]], polygons, how="inner", predicate="intersects")
    edges["predicado"] = "intersects"
    matches = pd.concat([inside, edges]).drop(columns=["geometry", "index_right"])
    counts = matches.groupby(level=0).size()
    status = pd.Series("sin_coincidencia", index=points.index, dtype="string")
    status.loc[counts.index] = "multiple"
    single = matches.loc[matches.index.isin(counts[counts.eq(1)].index)]
    status.loc[single.index] = single.predicado.map({"within": "interior", "intersects": "borde_unico"})
    return single, status, counts.reindex(points.index, fill_value=0), matches


def enrich(original, ageb, municipality):
    required = {"OID", "LATITUD", "LONGITUD"}
    if required - set(original.columns) or original.empty:
        raise ValueError("Faltan columnas base o filas.")
    if original.OID.isna().any() or original.OID.eq("").any() or original.OID.duplicated().any():
        raise ValueError("OID deben estar presentes y ser únicos.")
    names = ["AGEB", "CVEGEO", "TIPO_AGEB", "CVE_LOC", "CVEGEO_MUNICIPIO", "MUNICIPIO_GEO",
             "ESTADO_UNION_AGEB", "N_COINCIDENCIAS_AGEB", "ESTADO_UNION_MUNICIPIO"]
    metadata_names = {"FUENTE_GEOGRAFICA", "CONSULTA_GEOGRAFICA_UTC"}
    if metadata_names & set(original.columns):
        raise ValueError("No se sobrescribirán metadatos geográficos existentes.")
    if set(names) & set(original.columns):
        raise ValueError("No se sobrescribirán columnas geográficas existentes.")
    output = original.copy()
    lat = pd.to_numeric(original.LATITUD, errors="coerce")
    lon = pd.to_numeric(original.LONGITUD, errors="coerce")
    valid = (lat.between(-90, 90) & lon.between(-180, 180)).fillna(False)
    points = gpd.GeoDataFrame(index=original.index[valid],
                             geometry=gpd.points_from_xy(lon[valid], lat[valid]), crs="EPSG:4326")
    for name in names:
        output[name] = pd.Series(pd.NA, index=original.index, dtype="string")
    output["N_COINCIDENCIAS_AGEB"] = pd.Series(0, index=original.index, dtype="Int64")
    candidates = []
    for kind, layer, mapping in [
        ("AGEB", ageb, {"cve_ageb": "AGEB", "cvegeo": "CVEGEO", "tipo_ageb": "TIPO_AGEB", "cve_loc": "CVE_LOC"}),
        ("MUNICIPIO", municipality, {"cvegeo": "CVEGEO_MUNICIPIO", "nomgeo": "MUNICIPIO_GEO"}),
    ]:
        single, status, counts, matches = spatial_matches(points, layer)
        output[f"ESTADO_UNION_{kind}"] = "coordenada_invalida"
        output.loc[status.index, f"ESTADO_UNION_{kind}"] = status
        for source, target in mapping.items():
            if source in single:
                output.loc[single.index, target] = single[source].astype("string")
        if kind == "AGEB":
            output.loc[counts.index, "N_COINCIDENCIAS_AGEB"] = counts.astype("Int64")
        evidence = matches[["cvegeo", "predicado"]].copy()
        evidence.insert(0, "OID", original.loc[evidence.index, "OID"].to_numpy())
        evidence["nivel"] = kind
        candidates.append(evidence)
    return output, pd.concat(candidates, ignore_index=True)


def main(refresh=False):
    manifest = acquire(refresh)
    urban, rural, municipal = (read_layer(kind) for kind in URLS)
    ageb = gpd.GeoDataFrame(pd.concat([urban, rural], ignore_index=True), crs=urban.crs)
    original = pd.read_csv(INPUT, dtype="string", keep_default_na=False)
    output, evidence = enrich(original, ageb, municipal)
    version = manifest["agebu"]["metadatos"].get("Fuente_informacion_vectorial", "Edición no indicada")
    output["FUENTE_GEOGRAFICA"] = version
    output["CONSULTA_GEOGRAFICA_UTC"] = manifest["agebu"]["consulta_utc"]
    pd.testing.assert_frame_equal(output[original.columns], original)
    if len(output) != len(original) or not output.OID.is_unique:
        raise ValueError("La unión alteró el número de accidentes.")
    temporary = OUTPUT.with_suffix(".csv.tmp")
    try:
        output.to_csv(temporary, index=False, encoding="utf-8", na_rep="")
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    evidence.to_csv(OUTPUT.parent / "coincidencias_geograficas.csv", index=False)
    report = {"fuente_accidentes_sha256": digest(INPUT), "fuentes": manifest,
              "filas": len(output), "columnas": len(output.columns), "crs_join": "EPSG:4326",
              "geometrias": {"urbanas": len(urban), "rurales": len(rural), "municipio": len(municipal)},
              "estados_ageb": output.ESTADO_UNION_AGEB.value_counts().to_dict(),
              "estados_municipio": output.ESTADO_UNION_MUNICIPIO.value_counts().to_dict(),
              "ambitos_asignados": output.TIPO_AGEB.value_counts().to_dict()}
    (OUTPUT.parent / "enriquecimiento_geografico_resumen.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "fuentes"}, ensure_ascii=False, indent=2))
    print(f"Cartografía: {version}. No se asignó COLONIA. Archivo: {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Volver a descargar la cartografía oficial.")
    try:
        main(parser.parse_args().refresh)
    except (OSError, ValueError, TypeError, requests.RequestException) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
