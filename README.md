# Fuentes para el dashboard de accidentes viales en Mérida

Entrega de fuentes del equipo para el ETL y el dashboard colaborativo. La base es el registro georreferenciado de INEGI ATUS para el **municipio de Mérida, Yucatán (31050), 2021–2024**. Los archivos ya descargados se pueden usar sin acceso a la VM.

## Datos listos para cargar

| Fuente | Archivo incluido | Enlace oficial y acceso |
| --- | --- | --- |
| **INEGI ATUS** | [CSV limpio](datos/para-etl/atus/accidentes_merida.csv), [CSV con geografía](datos/para-etl/atus/accidentes_merida_enriquecido.csv) y [GeoJSON de origen](datos/originales/atus/accidentes_merida.geojson). Se conservaron 8,815 registros. | [Programa ATUS de INEGI](https://www.inegi.org.mx/programas/accidentes/) y [servicio WFS](https://mapas.inegi.org.mx/geoserver/wfs). La [ficha de la descarga](datos/originales/atus/accidentes_merida.fuente.json) detalla la capa, el filtro `EDO=31 AND MPIO=50` y la paginación. |
| **INEGI Marco Geoestadístico** | [Municipio](datos/originales/marco-geoestadistico/mgem_31050.geojson), [AGEB urbanas](datos/originales/marco-geoestadistico/agebu_31050.geojson) y [AGEB rurales](datos/originales/marco-geoestadistico/agebr_31050.geojson), edición de diciembre de 2025. | [Catálogo oficial de INEGI](https://www.inegi.org.mx/servicios/catalogounico.html). Las URLs de cada capa están en [fuentes.json](datos/originales/marco-geoestadistico/fuentes.json). |
| **C01 · INEGI DENUE** | [CSV de 56,909 establecimientos](datos/para-etl/denue/establecimientos_merida.csv), edición 2026/05 corregida. Incluye ID, actividad, estrato, coordenadas e indicadores de validación. | [API DENUE](https://www.inegi.org.mx/servicios/api_denue.html). Para actualizar, usar `BuscarAreaAct` con entidad `31`, municipio `050` y un token propio. |
| **C02 · SICT / datos.gob.mx** | [CSV de aforos de Yucatán](datos/para-etl/sict/datos_viales_yucatan.csv), 4,169 observaciones de 2013–2024, y [respuestas JSON originales](datos/originales/sict/). | [Datos viales de la SICT](https://www.datos.gob.mx/es/dataset/datos_viales), CC BY 4.0 según el catálogo. El [manifiesto](datos/originales/sict/provenance.json) documenta el filtro por Yucatán y el acceso a través de la API CKAN. |
| **C03 · SIEGY** | [Boletín original en PDF](datos/originales/siegy/boletin_2025_11_transporte_sostenible.pdf) y [CSV con seis indicadores transcritos](datos/para-etl/siegy/indicadores_movilidad_siegy_2025_11.csv). | [Boletín 2025-11 del Gobierno de Yucatán](https://datos.yucatan.gob.mx/storage/boletines/archivos/2025/Boletin_2025_11.pdf). |
| **C06 · Prensa** | [CSV con enlaces y metadatos](datos/para-etl/prensa/referencias.csv). Incluye 34 artículos revisados y el estado de selección de cada uno. | Consultar los enlaces de cada fila en [La Jornada Maya](https://www.lajornadamaya.mx/) y [Yucatán al Instante](https://www.yucatanalinstante.com/). El equipo incluyó 25 artículos en su muestra. Los textos y las fotos se consultan en los sitios de origen. |

## Acceso y preparación de las demás partes

| Parte | Estado y acceso |
| --- | --- |
| **C04 · GeoPortal de Mérida** | Consultar la capa **GENERAL → Calles** desde el [visor municipal](https://geoportal.merida.gob.mx/). La capa municipal continúa pendiente de adquisición. Para el piloto actual están disponibles ATUS y el Marco Geoestadístico de INEGI. |
| **C05 · Solicitud gubernamental** | Borrador preparado para pedir datos de hechos viales a la [Unidad de Transparencia de la SSP Yucatán](https://transparencia.yucatan.gob.mx/ssp/unidad-transparencia). Estado: solicitud por enviar. |
| **C07 · Datos propios** | [Plantilla de captura vacía](preparacion/encuesta/survey_template.csv) y [diccionario del instrumento](preparacion/encuesta/survey_schema.json). Pendiente de recolección de respuestas. |
| **C08 · LiDAR** | [Índice de fichas consultadas](preparacion/lidar/indice_productos.csv), con la URL oficial por fila. La búsqueda dejó referencias documentales y sigue pendiente un producto LiDAR utilizable para Mérida. |
| **C09 · Realidad aumentada** | [Datos derivados de tres zonas piloto](preparacion/ar/locations.json) y [método de selección](preparacion/ar/overview.json). La maqueta reutiliza ATUS y DENUE como capa de presentación. [Referencia WebXR](https://developer.mozilla.org/es/docs/Web/API/WebXR_Device_API). |

## Para unir los datos

1. Leer `OID` como identificador del accidente en ATUS. Mantener los códigos originales y los valores desconocidos. Para repartir registros por AGEB, usar las asignaciones únicas del CSV enriquecido y conservar los estados de coincidencia para reportar la cobertura.
2. Relacionar DENUE por ubicación y documentar el desfase entre la edición 2026 y los accidentes 2021–2024. En SICT, conservar año, distancia y el control de coordenadas. La cercanía de un aforo se usa como contexto exploratorio.
3. Mantener SIEGY por indicador, periodo y territorio. Un valor estatal repetido al cruzar con ATUS se sigue interpretando como un solo valor agregado. En prensa, distinguir la fecha de publicación de la fecha del hecho y conservar el estado de revisión.

Los conteos describen las fuentes disponibles. Las concentraciones espaciales y las coincidencias por cercanía se usan para explorar patrones.

