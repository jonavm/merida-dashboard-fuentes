CAPÍTULO 06 · DATOS VIALES · ACTO 3: MOVERSE

# ¿Dónde se nos complica el volante? 8,815 accidentes registrados en Mérida

**Pregunta.** ¿En qué zonas y momentos se concentran los accidentes registrados y qué tipo de accidente aparece con mayor frecuencia?

**Entrada.** Vamos de Yucatán al municipio de Mérida, de ahí a su localidad principal y, al final, al entorno del Periférico Lic. Manuel Berzunza. Siete relojes muestran después cómo se distribuyen los registros a lo largo de la semana.

## La historia en 10 segundos

| Cifra | Qué mide | Fuente |
| --- | --- | --- |
| **8,815 accidentes** | Registros georreferenciados en el municipio, 2021–2024. | INEGI, ATUS · corte 31 dic. 2024 · suma de [escena 4](datos/escena-4.csv). |
| **116 accidentes** | Registros acumulados en la franja del sábado de 20:00 a 20:59. | INEGI, ATUS · corte 31 dic. 2024 · máximo de [escena 3](datos/escena-3.csv). |
| **3,185 colisiones** | Registros clasificados como colisión con vehículo automotor, el tipo más frecuente. | INEGI, ATUS · corte 31 dic. 2024 · código 1 en [escena 4](datos/escena-4.csv). |

## Escenas

| Escena | Título con hallazgo | Lectura y archivo |
| --- | --- | --- |
| 1 · Dónde | **Al Periférico le conviene ir buscando abogado. Lo mencionan 25 de los 32 registros de la zona más densa** | El mapa reúne 8,074 registros asignados a AGEB urbanas. El anillo oro señala la de mayor densidad: 32 registros en 0.12 km², equivalentes a 270.7 por km² con el área sin redondear. Las menciones corresponden al Periférico Lic. Manuel Berzunza e incluyen su lateral. [CSV](datos/escena-1.csv) · [D3](graficas/index.html?escena=1) |
| 2 · Población de referencia | **El Censo puso los vecinos. ATUS puso la lámina doblada. La mediana fue de 6.9 accidentes por cada 1,000 habitantes** | La mediana usa las 520 AGEB con población positiva que coincide con el Censo 2020. Las otras 25 se marcan en gris. El cociente usa accidentes acumulados en cuatro años y residentes censados en 2020. [CSV](datos/escena-2.csv) · [D3](graficas/index.html?escena=2) |
| 3 · Cuándo | **A las ocho, hasta el reloj del sábado pidió grúa. La franja de las 20:00 acumuló 116 registros entre 2021 y 2024** | Cada día tiene su propio reloj y el borde oro señala la franja con más registros acumulados entre 2021 y 2024. [CSV](datos/escena-3.csv) · [D3](graficas/index.html?escena=3) |
| 4 · Qué pasó | **Los postes no cambian de carril. 2,461 choques con objetos fijos** | El bloque morado representa toda la categoría de objetos fijos, el 27.9 % de los registros ATUS. Junto con las colisiones con vehículo automotor y motocicleta, reúne el 88.0 %. [CSV](datos/escena-4.csv) · [D3](graficas/index.html?escena=4) |

[Procedencia, fórmulas y cortes por escena](datos/FUENTES.md).

## Lo que estos datos no dicen

- ATUS describe los accidentes que quedaron registrados en la capa georreferenciada, con la cobertura del programa. Las cifras describen frecuencia de registros. El riesgo de circular requeriría medir la exposición, por ejemplo, los viajes y flujos comparables por vía y horario.
- La cartografía es de diciembre de 2025 y se usa como base común para ubicar registros de 2021–2024. Hubo 261 asignaciones rurales, 321 coincidencias múltiples y 159 registros sin AGEB. Las escenas urbanas usan asignaciones únicas. Las AGEB son áreas geoestadísticas.
- La vista de calle cuenta menciones en los campos de ATUS de una sola AGEB. Los puntos agrupan ubicaciones en celdas de 100 metros y representan observaciones registradas, con independencia del trazo oficial de la vía.
- La población es de 2020. De las 545 AGEB urbanas, 19 claves no aparecen en el recorte censal y seis coincidieron con población cero. En las 520 calculables, la razón puede crecer mucho con pocos residentes. La población residente sirve como referencia descriptiva y deja fuera la población flotante. La coincidencia de clave y población entre fuentes no demuestra que los límites fueran idénticos en todas las fechas.
- La hora de la escena 3 es local y se agrupa en franjas de una hora. Las 116 observaciones suman los sábados de los cuatro años, no describen un sábado típico.
- La encuesta propia quedó fuera por falta de respuestas. Aforos SICT e indicadores SIEGY quedan como material de contexto del repo. El análisis de peatones y cruces corresponde al Equipo 4.

**Puente.** Si así se distribuyen los accidentes registrados, ¿qué cambia cuando recorremos esas calles a pie y toca cruzarlas?
