"""Prepara las propiedades de ATUS sin interpretar sus códigos categóricos."""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "datos/originales/atus/accidentes_merida.geojson"
OUTPUT = ROOT / "datos/para-etl/atus/accidentes_merida.csv"
CATALOGS = ROOT / "scripts/catalogos_atus.json"
CATALOG_VARIABLES = (
    "TIPACCID", "CLASE", "CAUSAACCI", "DIASEMANA", "SEXO", "ALIENTO",
    "CINTURON", "URBANA", "SUBURBANA", "CAPAROD",
)
VEHICLES = [
    "AUTOMOVIL", "CAMPASAJ", "MICROBUS", "PASCAMION", "OMNIBUS", "TRANVIA",
    "CAMIONETA", "CAMION", "TRACTOR", "FERROCARRI", "MOTOCICLET", "BICICLETA",
    "OTROVEHIC",
]
VICTIMS = [
    "CONDMUERTO", "CONDHERIDO", "PASAMUERTO", "PASAHERIDO", "PEATMUERTO",
    "PEATHERIDO", "CICLMUERTO", "CICLHERIDO", "OTROMUERTO", "OTROHERIDO",
]
REQUIRED = [
    "OID", "ID", "ANIO", "MES", "DIA", "HORA", "MINUTOS", "DIASEMANA", "EDO",
    "MPIO", "TIPACCID", "CLASE", "CALLE1", "CALLE2", "CARRETERA", "LATITUD",
    "LONGITUD", "TOTMUERTOS", "TOTHERIDOS", *VEHICLES, *VICTIMS,
]
FLAGS = {
    "TIENE_MOTOCICLETA": "MOTOCICLET",
    "TIENE_BICICLETA": "BICICLETA",
    "TIENE_AUTOMOVIL": "AUTOMOVIL",
    "TIENE_CAMION": "CAMION",
    "TIENE_HERIDOS": "TOTHERIDOS",
    "TIENE_MUERTOS": "TOTMUERTOS",
}
IMPORTANT = [
    "OID", "ID", "ANIO", "MES", "DIA", "HORA", "MINUTOS", "DIASEMANA",
    "EDO", "MPIO", "TIPACCID", "CLASE", "LATITUD", "LONGITUD", "CALLE1",
    "CALLE2", "CARRETERA", "TOTMUERTOS", "TOTHERIDOS", "FECHA",
    "HORA_COMPLETA", "INTERSECCION", *FLAGS,
]


def read_properties(path):
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("El archivo de entrada no es una FeatureCollection.")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("El GeoJSON no contiene una lista de features con datos.")
    properties = []
    for index, feature in enumerate(features):
        if (not isinstance(feature, dict) or feature.get("type") != "Feature"
                or not isinstance(feature.get("properties"), dict)):
            raise ValueError(f"Feature {index} sin propiedades válidas.")
        properties.append(feature["properties"])
    # La unión de claves conserva incluso propiedades presentes en una sola fila.
    return pd.DataFrame(properties)


def clean_string(value, uppercase=False):
    if not isinstance(value, str):
        return value
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return pd.NA
    return value.upper() if uppercase else value


def whole_numbers(series):
    """Conversión temporal para derivados; la columna original no se modifica."""
    numbers = pd.to_numeric(series, errors="coerce")
    return numbers.where(numbers.mod(1).eq(0))


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Clave duplicada en los catálogos: {key}")
        result[key] = value
    return result


def load_catalogs(path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as stream:
        catalogs = json.load(stream, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(catalogs, dict):
        raise ValueError("El registro de catálogos debe ser un objeto JSON.")
    if set(catalogs) - set(CATALOG_VARIABLES):
        raise ValueError("Hay variables no admitidas en el registro de catálogos.")
    for variable, catalog in catalogs.items():
        if not isinstance(catalog, dict) or catalog.get("estado") not in {"pendiente", "verificado"}:
            raise ValueError(f"Estado de catálogo inválido para {variable}.")
        if catalog["estado"] == "pendiente":
            continue
        source = catalog.get("fuente_url")
        host = urlparse(source).hostname if isinstance(source, str) else None
        if (not host or not (host == "inegi.org.mx" or host.endswith(".inegi.org.mx"))
                or urlparse(source).scheme != "https"):
            raise ValueError(f"{variable}: se requiere una URL oficial HTTPS de INEGI.")
        reference = catalog.get("referencia")
        years = catalog.get("anios")
        codes = catalog.get("codigos")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError(f"{variable}: falta referencia al documento, tabla o página.")
        if not isinstance(years, list) or not years or any(type(y) is not int for y in years):
            raise ValueError(f"{variable}: faltan años de aplicación verificados.")
        if (not isinstance(codes, dict) or not codes
                or any(not k or k != k.strip() or not isinstance(v, str) or not v.strip()
                       for k, v in codes.items())):
            raise ValueError(f"{variable}: códigos o descripciones inválidos.")
    return catalogs


def enrich_catalogs(df, catalogs):
    """Solo usa etiquetas declaradas verificadas y dentro de su vigencia."""
    df = df.copy()
    report = []
    for variable in CATALOG_VARIABLES:
        target = f"{variable}_DESC"
        if target in df.columns:
            raise ValueError(f"No se sobrescribirá la columna existente {target}.")
        df[target] = pd.Series(pd.NA, index=df.index, dtype="string")
        catalog = catalogs.get(variable, {})
        if variable not in df:
            report.append(f"{variable}: variable ausente en la fuente.")
            continue
        if catalog.get("estado") != "verificado":
            report.append(f"{variable}: catálogo pendiente; {target} permanece nula.")
            continue
        # Comparación textual exacta: no equiparar, por ejemplo, '01' con '1'.
        codes = df[variable].astype("string")
        applicable = pd.to_numeric(df["ANIO"], errors="coerce").isin(catalog["anios"])
        df.loc[applicable, target] = codes[applicable].map(catalog["codigos"]).astype("string")
        unknown = sorted(codes[applicable & codes.notna() & df[target].isna()].unique())
        report.append(
            f"{variable}: {int(df[target].notna().sum())} mapeados; "
            f"{int((~applicable).sum())} filas fuera de años verificados; "
            f"códigos sin correspondencia: {', '.join(unknown) or 'ninguno'}."
        )
    return df, report


def transform(df):
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f"Faltan variables obligatorias: {', '.join(missing)}")
    derived = {"FECHA", "HORA_COMPLETA", "INTERSECCION", *FLAGS}
    if derived.intersection(df.columns):
        raise ValueError("La fuente ya contiene columnas derivadas; no se sobrescribirán.")
    df = df.copy()
    for column in df.columns:
        # Uniformar nombres de vías; conservar identificadores y códigos originales.
        df[column] = df[column].map(
            lambda value: clean_string(value, column in {"CALLE1", "CALLE2", "CARRETERA"})
        )
    if df["OID"].isna().any():
        raise ValueError("Hay OID vacíos; no es posible deduplicar con seguridad.")
    duplicate = df["OID"].astype("string").duplicated(keep="first")
    removed = int(duplicate.sum())
    df = df.loc[~duplicate].copy().reset_index(drop=True)

    parts = pd.DataFrame({
        "year": whole_numbers(df["ANIO"]),
        "month": whole_numbers(df["MES"]),
        "day": whole_numbers(df["DIA"]),
    })
    df["FECHA"] = pd.to_datetime(parts, errors="coerce")
    hours = whole_numbers(df["HORA"])
    minutes = whole_numbers(df["MINUTOS"])
    valid_time = hours.between(0, 23) & minutes.between(0, 59)
    df["HORA_COMPLETA"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df.loc[valid_time, "HORA_COMPLETA"] = (
        hours[valid_time].astype("int64").astype("string").str.zfill(2)
        + ":" + minutes[valid_time].astype("int64").astype("string").str.zfill(2)
    )

    street1 = df["CALLE1"].astype("string")
    street2 = df["CALLE2"].astype("string")
    df["INTERSECCION"] = street1.fillna(street2)
    both = street1.notna() & street2.notna()
    df.loc[both, "INTERSECCION"] = street1[both] + " x " + street2[both]

    for target, source in FLAGS.items():
        counts = whole_numbers(df[source])
        # Desconocido/inválido no equivale a cero ni a False.
        df[target] = counts.gt(0).astype("boolean").where(counts.ge(0), pd.NA)
    return df, removed


def print_summary(df, removed):
    print(f"\nFilas finales: {len(df)}")
    print(f"Columnas: {len(df.columns)}")
    print(", ".join(df.columns))
    print(f"Duplicados eliminados por OID: {removed} (se conserva la primera aparición)")
    print("\nValores nulos importantes:")
    print(df[IMPORTANT].isna().sum().to_string())
    years = sorted(df["ANIO"].dropna().astype(str).unique())
    print(f"\nAños disponibles: {', '.join(years)}")
    print("\nPrimeras 10 filas (todas las columnas):")
    print(df.head(10).to_string(index=False))


def main():
    print(f"Leyendo: {INPUT}", flush=True)
    original = read_properties(INPUT)
    print(f"Filas originales: {len(original)}; variables originales: {len(original.columns)}")
    df, removed = transform(original)
    df, catalog_report = enrich_catalogs(df, load_catalogs(CATALOGS))
    print("\nEstado de los catálogos:")
    for line in catalog_report:
        print(f"  {line}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".csv.tmp")
    try:
        df.to_csv(temporary, index=False, encoding="utf-8", date_format="%Y-%m-%d", na_rep="")
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print_summary(df, removed)
    print(f"\nTransformación terminada correctamente. Archivo: {OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
