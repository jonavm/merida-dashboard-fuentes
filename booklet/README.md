# Booklet · Equipo 6

Capítulo 06 del Acto 3, «Moverse». El equipo describe el conjunto de accidentes registrados en Mérida y enlaza con el capítulo del Equipo 4 sobre peatones y cruces.

- [Ficha del capítulo](ficha.md)
- [Datos finales y procedencia](datos/FUENTES.md)
- [Escenas D3](graficas/index.html)
- [Código de reproducción](../scripts/)

## Abrir las escenas

Desde la raíz del repositorio, inicia el servidor local:

~~~sh
python -m http.server 8000
~~~

Abre [la vista completa](http://localhost:8000/booklet/graficas/) en el navegador. Para integrar una sola escena, añade `?escena=1`, `?escena=2`, `?escena=3` o `?escena=4` a la URL de `index.html`. Las escenas conservan las etiquetas principales en el SVG para impresión. D3 7.9.0 y Outfit se incluyen localmente junto con sus licencias. Los mapas, colores y datos son los mismos en pantalla y en impresión.

## Regenerar datos y portada

Con Python 3.12, desde la raíz:

~~~sh
python -m pip install -r scripts/requisitos.txt
python scripts/etl_booklet.py
python scripts/generar_portada.py
~~~

El ETL usa la copia de ATUS, el Marco y el recorte censal con sus huellas de procedencia. Verifica los insumos, vuelve a limpiar y asignar los puntos, y escribe cuatro CSV, la geometría de dibujo y el control de conteos. Para comprobar la salida sin tocar la carpeta de entrega, pasa `--salida` con una carpeta temporal. `--tablas-atus` exporta además los dos CSV de trabajo de ATUS al directorio indicado. `--censo-zip` reconstruye el recorte local si se conserva el ZIP oficial.

El script de portada reproduce el PNG del README con las fuentes de Windows usadas en el original. En sistemas sin esas fuentes, `--portable` usa DejaVu y el dibujo conserva los mismos datos. Las cuatro escenas del booklet se generan en D3.
