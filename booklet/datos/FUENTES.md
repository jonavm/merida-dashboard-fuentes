# Fuentes y cálculos de las escenas

## Fuente base de accidentes

**[ATUS] INEGI. Accidentes de Tránsito Terrestre en Zonas Urbanas y Suburbanas, capa georreferenciada.** Municipio de Mérida (Yucatán), años 2021 a 2024. **Corte de observación: 31 de diciembre de 2024.** Copia consultada el 23 de septiembre de 2026 (UTC). [Programa ATUS](https://www.inegi.org.mx/programas/accidentes/) · [Servicio WFS](https://mapas.inegi.org.mx/geoserver/wfs) · [Manifiesto de la consulta](../../datos/originales/atus/accidentes_merida.fuente.json).

**[MG25] INEGI. Marco Geoestadístico, diciembre de 2025.** Geometrías del estado, municipio y AGEB urbanas y rurales. [Servicio del Catálogo Único](https://www.inegi.org.mx/servicios/catalogounico/) · [Contorno estatal](https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgee/31) · [URLs, edición y huellas](../../datos/originales/marco-geoestadistico/fuentes.json).

**[CPV2020] INEGI. Censo de Población y Vivienda 2020.** Resultados por AGEB y manzana urbana de Yucatán, corte censal 2020. [Ficha del conjunto](https://www.inegi.org.mx/app/descarga/ficha.html?ag=0&f=csv&tit=326101) · [Descarga original](https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_31_cpv2020_csv.zip) · [Recorte publicado y manifiesto](../../datos/originales/censo-2020/).

## Un CSV por escena

| Archivo | Fuente y corte | Cálculo |
| --- | --- | --- |
| [escena-1.csv](escena-1.csv) | ATUS, 31 dic. 2024 · MG25, dic. 2025 | Cuenta cada OID una vez. Asigna por punto en polígono, usa el borde solo si no hay interior y conserva únicamente coincidencias urbanas únicas. Divide los accidentes de cada área entre su superficie completa en km² (UTM 16N, EPSG:32616). Incluye 545 AGEB, aunque su conteo sea cero. En el área de mayor densidad, cuenta una vez cada registro que menciona «MANUEL BERZUNZA» en `CALLE1` o `CALLE2`. |
| [escena-2.csv](escena-2.csv) | ATUS, 31 dic. 2024 · MG25, dic. 2025 · CPV2020 | Conserva los mismos conteos urbanos. Toma las filas de total por AGEB del Censo (`MZA=000`, `AGEB≠0000`). Cruza por `ENTIDAD+MUN+LOC+AGEB` de 13 caracteres. Acepta `POBTOT` cuando es positivo e igual al `pob_total` que el Marco atribuye al Censo 2020. Multiplica el conteo acumulado por 1,000 y divide entre esa población. El resultado queda vacío ante ausencia de clave, discrepancia o población no positiva. |
| [escena-3.csv](escena-3.csv) | ATUS, 31 dic. 2024 | Deriva el día de la semana de la fecha válida `ANIO+MES+DIA`, de lunes a domingo. Agrupa la hora local de `HORA` en 24 franjas y cuenta OID. Incluye las 168 combinaciones; la cuadrícula recoge 8,815 registros y excluye cero por fecha u hora inválida en el recorte. |
| [escena-4.csv](escena-4.csv) | ATUS, 31 dic. 2024 | Cuenta OID por código original `TIPACCID`. Conserva el código y usa las etiquetas de los catálogos de INEGI. Si aparece un código sin correspondencia, se muestra tal cual. [2021](https://www.inegi.org.mx/rnm/index.php/catalog/788/variable/V13?name=TIPACCID) · [2022](https://www.inegi.org.mx/rnm/index.php/catalog/903/variable/F1/V13?name=TIPACCID) · [2023](https://www.inegi.org.mx/rnm/index.php/catalog/1007/variable/F1/V13?name=TIPACCID) · [2024](https://www.inegi.org.mx/rnm/index.php/catalog/1115/variable/F1/V13?name=TIPACCID). |

## Archivos auxiliares

- [mapa-base.geojson](mapa-base.geojson) conserva claves, AGEB urbanas y límites estatal y municipal del Marco MG25. Se simplificó para dibujar: 12 m para las capas municipal y urbana y 450 m para el contorno estatal. Se entrega en EPSG:4326. Se usaron las geometrías completas para calcular conteos y superficies. La escena 1 baja del estado a la localidad de Mérida (`310500001`) y a la AGEB `3105000013248`. En el último panel, cada punto es el centro de una celda de 100 m en UTM 16N con al menos un registro que menciona la vía. Las seis celdas agrupan 25 registros, incluidas menciones de la lateral.
- [control.json](control.json) documenta la conciliación del recorte: 8,815 en total, de los cuales 8,074 tienen AGEB urbana única, 261 rural, 321 múltiples y 159 sin asignación. De las 545 AGEB urbanas, 526 claves coinciden con el Censo y tienen la misma cifra publicada en el Marco; 520 tienen un denominador positivo. Los expedientes de accidentes no se distribuyen en esta carpeta.
- Los mapas usan clases de densidad o cociente. Un cero calculado aparece en blanco y los faltantes de población, en gris. Los cocientes altos en AGEB con pocos residentes se mantienen en el CSV y el mapa los agrupa en el intervalo superior. No se calculan tasas de exposición.
