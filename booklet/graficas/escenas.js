"use strict";

const formatoEntero = new Intl.NumberFormat("es-MX");
const formatoDecimal = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 1 });
const entero = value => formatoEntero.format(value);
const decimal = value => formatoDecimal.format(value);
const hora = value => String(value).padStart(2, "0") + ":00";
const mayusculaInicial = value => value[0].toUpperCase() + value.slice(1);
const dataDir = "../datos/";
const revalidar = { cache: "no-cache" };
const paleta = getComputedStyle(document.documentElement);
const token = name => paleta.getPropertyValue("--" + name).trim();
const W = 760;

function escena(numero, titulo, lectura) {
  const figure = d3.select("#escena-" + numero);
  figure.select("h2").text(titulo);
  figure.select("figcaption").text(lectura);
  return figure.select(".dibujo");
}

function lienzo(container, height, title, description) {
  const id = container.node().closest("figure").id;
  const svg = container.append("svg")
    .attr("viewBox", [0, 0, W, height])
    .attr("role", "img")
    .attr("aria-labelledby", id + "-svg-titulo " + id + "-svg-desc");
  svg.append("title").attr("id", id + "-svg-titulo").text(title);
  svg.append("desc").attr("id", id + "-svg-desc").text(description);
  return svg;
}

function leyenda(container, items, label) {
  const list = container.append("div").attr("class", "leyenda")
    .attr("role", "list").attr("aria-label", label);
  const item = list.selectAll("span.leyenda-item").data(items).join("span")
    .attr("class", "leyenda-item").attr("role", "listitem");
  item.append("span").attr("class", "muestra").attr("aria-hidden", "true")
    .style("background", datum => datum[1]);
  item.append("span").text(datum => datum[0]);
}

function colorearMapa(umbrales) {
  const interpolar = d3.interpolateLab(token("papel"), token("morado"));
  const colores = d3.range(umbrales.length + 1).map(i => interpolar(0.16 + 0.84 * i / umbrales.length));
  const escala = d3.scaleThreshold(umbrales, colores);
  const items = [["0", token("papel")]];
  for (let i = 0; i < colores.length; i += 1) {
    const etiqueta = i === 0 ? "Más de 0 a < " + umbrales[0]
      : i === umbrales.length ? umbrales[i - 1] + " o más"
      : umbrales[i - 1] + " a < " + umbrales[i];
    items.push([etiqueta, colores[i]]);
  }
  return {
    items,
    relleno(value) {
      if (value === null) return token("gris");
      return value === 0 ? token("papel") : escala(value);
    }
  };
}

function dibujarMapa(container, geo, rows, config) {
  const estado = geo.features.filter(f => f.properties.capa === "estado");
  const total = geo.features.filter(f => f.properties.capa === "municipio");
  const urbanas = geo.features.filter(f => f.properties.capa === "urbana");
  const cabecera = urbanas.filter(f => f.properties.cvegeo.startsWith("310500001"));
  const indice = new Map(rows.map(row => [row.cvegeo_ageb, row]));
  const escala = colorearMapa(config.umbrales);
  const svg = lienzo(container, 410, config.unidad, config.descripcion);
  const vistas = config.recorrido
    ? [
      { x: 0, ancho: 164, alto: 158, etiqueta: "1 · Yucatán", marco: estado, limite: estado, referencia: total },
      { x: 0, y: 169, ancho: 164, alto: 241, etiqueta: "2 · Municipio", marco: total, areas: urbanas, limite: total },
      { x: 175, ancho: 280, etiqueta: "3 · Localidad de Mérida", marco: cabecera, areas: cabecera },
    ]
    : [
      { x: 0, etiqueta: "Municipio", marco: total, areas: urbanas, limite: total },
      { x: 385, etiqueta: "Acercamiento · localidad de Mérida", marco: cabecera, areas: cabecera },
    ];

  for (const { x, y = 0, ancho = 375, alto = 410, etiqueta, marco, areas = [], limite = [], referencia = [] } of vistas) {
    const panel = svg.append("g").attr("transform", "translate(" + x + "," + y + ")");
    panel.append("rect").attr("width", ancho - 1).attr("height", alto - 2).attr("rx", 9)
      .attr("fill", "#faf8fc").attr("stroke", token("borde"));
    panel.append("text").attr("x", 13).attr("y", 24).attr("font-size", 15)
      .attr("class", "svg-foco").text(etiqueta);
    const map = panel.append("g").attr("transform", "translate(10,36)");
    const projection = d3.geoMercator().fitSize([ancho - 20, alto - 52], { type: "FeatureCollection", features: marco });
    const path = d3.geoPath(projection);
    map.selectAll("path.limite").data(limite).join("path").attr("class", "limite")
      .attr("d", path).attr("fill", "#f2f0f4").attr("stroke", token("gris")).attr("stroke-width", 1);
    map.selectAll("path.municipio-destacado").data(referencia).join("path")
      .attr("class", "municipio-destacado").attr("d", path)
      .attr("fill", token("morado")).attr("stroke", token("morado")).attr("stroke-width", 1);
    const paths = map.selectAll("path.ageb").data(areas).join("path").attr("class", "ageb").attr("d", path)
      .attr("fill", feature => escala.relleno(indice.get(feature.properties.cvegeo)[config.campo]))
      .attr("stroke", "#817587").attr("stroke-width", 0.43);
    paths.append("title").text(feature => {
      const row = indice.get(feature.properties.cvegeo);
      return "AGEB " + row.cvegeo_ageb + " · " + config.detalle(row);
    });
    const destacada = areas.find(feature => feature.properties.cvegeo === config.destacada);
    if (destacada) {
      const [cx, cy] = path.centroid(destacada);
      map.append("circle").attr("cx", cx).attr("cy", cy).attr("r", 10)
        .attr("fill", "none").attr("stroke", token("papel")).attr("stroke-width", 4)
        .attr("pointer-events", "none");
      map.append("circle").attr("class", "foco-densidad").attr("cx", cx).attr("cy", cy).attr("r", 10)
        .attr("fill", "none").attr("stroke", token("oro-oscuro")).attr("stroke-width", 2)
        .attr("pointer-events", "none");
    }
  }
  if (config.recorrido) {
    const focal = urbanas.find(feature => feature.properties.cvegeo === config.destacada);
    const marks = geo.features.find(feature => feature.properties.capa === "celdas_via"
      && feature.properties.cvegeo === config.destacada);
    dibujarVistaVial(svg, focal, marks, indice.get(config.destacada));
  }
  const items = [...escala.items];
  if (config.mostrarSinDato) items.push(["Sin denominador", token("gris")]);
  if (config.destacada) items.push(["Mayor densidad (anillo)", token("oro-oscuro")]);
  leyenda(container, items, config.unidad);
}

function dibujarVistaVial(svg, focal, marks, row) {
  const panel = svg.append("g").attr("class", "vista-vial").attr("transform", "translate(466,0)");
  panel.append("rect").attr("width", 293).attr("height", 408).attr("rx", 9)
    .attr("fill", "#faf8fc").attr("stroke", token("borde"));
  panel.append("text").attr("x", 14).attr("y", 24).attr("class", "svg-foco")
    .attr("font-size", 15).text("4 · A ras de calle");
  panel.append("text").attr("x", 14).attr("y", 50).attr("class", "svg-tinta")
    .attr("font-weight", 650).attr("font-size", 16).text(row.via_del_acercamiento);
  panel.append("text").attr("x", 14).attr("y", 92).attr("class", "svg-foco")
    .attr("font-size", 34).text(entero(row.registros_que_mencionan_la_via) + " de " + entero(row.accidentes));
  panel.append("text").attr("x", 14).attr("y", 114).attr("class", "svg-contexto")
    .attr("font-size", 15).text("registros de esta AGEB mencionan la vía");
  const projection = d3.geoMercator().fitSize([255, 225],
    { type: "FeatureCollection", features: [focal, marks] });
  const path = d3.geoPath(projection).pointRadius(4);
  const map = panel.append("g").attr("transform", "translate(19,132)");
  map.append("path").datum(focal).attr("d", path).attr("fill", "#ebe0f2")
    .attr("stroke", "#817587").attr("stroke-width", 1);
  map.append("path").datum(marks).attr("class", "celdas-via").attr("d", path)
    .attr("fill", token("morado")).attr("stroke", token("papel")).attr("stroke-width", 0.9);
  panel.append("text").attr("x", 14).attr("y", 389).attr("class", "svg-contexto")
    .attr("font-size", 15).text("Puntos: celdas de 100 m con registros");
}

function escenaDensidad(geo, rows, control) {
  const locales = d3.sum(rows, row => row.accidentes);
  const foco = rows.find(row => row.via_del_acercamiento);
  const amplia = entero(control.accidentes_ageb_rural) + " se asignaron a AGEB rurales, "
    + entero(control.accidentes_ageb_multiple) + " tuvieron coincidencias múltiples y "
    + entero(control.accidentes_sin_ageb) + " quedaron sin asignación.";
  const titulo = "Al Periférico le conviene ir buscando abogado. Lo mencionan "
    + entero(foco.registros_que_mencionan_la_via) + " de los " + entero(foco.accidentes)
    + " registros de la zona más densa";
  const container = escena(1, titulo,
    "El mapa reúne " + entero(locales) + " registros asignados a AGEB urbanas. "
    + "El anillo oro marca la zona de mayor densidad: " + entero(foco.accidentes)
    + " registros en " + Number(foco.superficie_km2).toFixed(2) + " km² ("
    + decimal(foco.accidentes_por_km2) + " por km²). El último panel agrupa las ubicaciones de los registros que mencionan la vía. De los " + entero(control.accidentes_total)
    + " registros de Mérida, " + amplia);
  dibujarMapa(container, geo, rows, {
    umbrales: [10, 25, 50, 75, 100],
    campo: "accidentes_por_km2",
    recorrido: true,
    destacada: foco.cvegeo_ageb,
    unidad: "Accidentes por km²",
    descripcion: "Cuatro escalas: Yucatán, municipio, localidad y Periférico Lic. Manuel Berzunza. Los tonos oscuros indican más registros por km². El último mapa usa celdas de 100 metros para agrupar las ubicaciones.",
    detalle: row => decimal(row.accidentes_por_km2) + " accidentes por km² · " + entero(row.accidentes) + " registros",
  });
}

function escenaPoblacion(geo, rows) {
  const validas = rows.filter(row => row.accidentes_por_1000_habitantes !== null);
  const mediana = d3.median(validas, row => row.accidentes_por_1000_habitantes);
  const titulo = "El Censo puso los vecinos. ATUS puso la lámina doblada. La mediana fue de "
    + decimal(mediana) + " accidentes por cada 1,000 habitantes";
  const container = escena(2, titulo,
    "La mediana usa " + entero(validas.length) + " de " + entero(rows.length)
    + " AGEB urbanas. Las áreas sin población compatible o positiva están en gris. Un denominador pequeño eleva la razón. La población residente sirve como referencia, con independencia de quién circula por la zona.");
  dibujarMapa(container, geo, rows, {
    umbrales: [2, 5, 10, 20, 40],
    campo: "accidentes_por_1000_habitantes",
    unidad: "Accidentes por cada 1,000 habitantes",
    descripcion: "Mapa temático y acercamiento. Las áreas grises carecen de un denominador censal positivo y compatible.",
    mostrarSinDato: true,
    detalle: row => row.poblacion_2020 === null
      ? "sin denominador calculable · " + entero(row.accidentes) + " registros"
      : decimal(row.accidentes_por_1000_habitantes) + " por cada 1,000 · " + entero(row.accidentes)
        + " registros · " + entero(row.poblacion_2020) + " habitantes en 2020",
  });
}

function escenaHoras(rows, control) {
  const pico = d3.greatest(rows, row => row.accidentes);
  const dia = mayusculaInicial(pico.dia_semana);
  const [inicio, fin] = control.periodo;
  const title = "A las ocho, hasta el reloj del sábado pidió grúa. La franja de las "
    + hora(pico.hora_local) + " acumuló " + entero(pico.accidentes) + " registros entre " + inicio + " y " + fin;
  const invalidos = control.registros_sin_fecha_u_hora;
  const lectura = "Cada reloj arranca a medianoche y se lee en sentido horario. El arco con borde oro marca "
    + "la franja con más registros de los cuatro años. Los relojes reúnen "
    + entero(d3.sum(rows, row => row.accidentes)) + " accidentes."
    + (invalidos ? " Quedaron fuera " + entero(invalidos) + " registros con fecha u hora inválida." : "");
  const container = escena(3, title, lectura);
  const svg = lienzo(container, 402, "Siete relojes de accidentes registrados",
    title + ". Un reloj por día. Cada arco corresponde a una hora. Las cuatro horas cardinales se indican en cada reloj.");
  const days = d3.groups(rows, row => row.dia_semana);
  const color = d3.scaleSequential(d3.interpolateLab(token("papel"), token("morado")))
    .domain([0, pico.accidentes]);
  const angulo = index => index * (2 * Math.PI / 24);
  const arc = d3.arc().innerRadius(35).outerRadius(60)
    .startAngle(row => angulo(row.hora_local - 0.5))
    .endAngle(row => angulo(row.hora_local + 0.5))
    .padAngle(0.023).padRadius(60).cornerRadius(1.2);
  const cardinales = [
    { h: "00", x: 0, y: -72 },
    { h: "06", x: 74, y: 0 },
    { h: "12", x: 0, y: 73 },
    { h: "18", x: -74, y: 0 },
  ];
  const cell = svg.selectAll("g.reloj").data(days).join("g")
    .attr("class", "reloj")
    .attr("transform", (_, i) => "translate(" + ((i % 4) * 190 + 95) + "," + (Math.floor(i / 4) * 198 + 100) + ")");
  cell.append("rect").attr("x", -91).attr("y", -95).attr("width", 182).attr("height", 188).attr("rx", 12)
    .attr("fill", ([day]) => day === pico.dia_semana ? "#faf2fc" : "#faf9fb")
    .attr("stroke", ([day]) => day === pico.dia_semana ? token("oro-oscuro") : token("borde"));
  cell.selectAll("path.hora-dia").data(([, entries]) => entries).join("path")
    .attr("class", "hora-dia").attr("d", arc)
    .attr("fill", row => color(row.accidentes))
    .attr("stroke", row => row === pico ? token("oro-oscuro") : token("borde"))
    .attr("stroke-width", row => row === pico ? 2.5 : 0.8)
    .append("title").text(row => mayusculaInicial(row.dia_semana) + " " + hora(row.hora_local)
      + " · " + entero(row.accidentes) + " registros");
  cell.selectAll("text.hora-cardinal").data(cardinales).join("text").attr("class", "svg-contexto hora-cardinal")
    .attr("x", marker => marker.x).attr("y", marker => marker.y)
    .attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .attr("font-size", 15).text(marker => marker.h);
  cell.append("text").attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .attr("class", ([day]) => day === pico.dia_semana ? "svg-foco" : "svg-tinta")
    .attr("font-size", 16).attr("font-weight", 650).attr("y", ([day]) => day === pico.dia_semana ? -8 : 0)
    .text(([day]) => mayusculaInicial(day));
  cell.filter(([day]) => day === pico.dia_semana).append("text")
    .attr("text-anchor", "middle").attr("dominant-baseline", "central")
    .attr("class", "svg-rotulo").attr("font-size", 16).attr("y", 12).text(hora(pico.hora_local));

  const nota = svg.append("g").attr("transform", "translate(660,286)");
  nota.append("text").attr("text-anchor", "middle").attr("class", "svg-rotulo").attr("font-size", 16)
    .attr("y", -34).text("PICO DE REGISTROS");
  nota.append("text").attr("text-anchor", "middle").attr("class", "svg-foco").attr("font-size", 46)
    .attr("y", 15).text(entero(pico.accidentes));
  nota.append("text").attr("text-anchor", "middle").attr("class", "svg-tinta").attr("font-size", 17)
    .attr("y", 43).text(dia + " · " + hora(pico.hora_local));
  const steps = d3.ticks(0, pico.accidentes, 4);
  if (steps.at(-1) !== pico.accidentes) steps.push(pico.accidentes);
  leyenda(container, steps.map(value => [entero(value), color(value)]), "Accidentes registrados");
}

function escenaTipos(rows) {
  const ranking = d3.sort(rows, row => -row.accidentes);
  const count = d3.sum(ranking, row => row.accidentes);
  const principales = ranking.slice(0, 3);
  const objetoFijo = ranking.find(row => String(row.codigo_tipaccid) === "4");
  const porcentaje = new Intl.NumberFormat("es-MX", { minimumFractionDigits: 1, maximumFractionDigits: 1 })
    .format(100 * d3.sum(principales, row => row.accidentes) / count);
  const titulo = "Los postes no cambian de carril. " + entero(objetoFijo.accidentes) + " choques con objetos fijos";
  const container = escena(4, titulo, "El bloque morado muestra la categoría completa de choques con objetos fijos, "
    + "que representa el " + decimal(100 * objetoFijo.accidentes / count) + " % del total. "
    + "Junto con los choques con vehículos y motocicletas, reúne el " + porcentaje + " % de los registros.");
  const height = 231;
  const svg = lienzo(container, height, "Mosaico de accidentes por tipo oficial", titulo + ".");
  const hierarchy = d3.hierarchy({ children: ranking }).sum(row => row.accidentes || 0);
  d3.treemap().size([W, height]).tile(d3.treemapSquarify.ratio(1.15))(hierarchy);
  const piezas = svg.selectAll("g.pieza").data(hierarchy.leaves()).join("g").attr("class", "pieza")
    .attr("transform", leaf => "translate(" + leaf.x0 + "," + leaf.y0 + ")");
  piezas.append("rect")
    .attr("width", leaf => leaf.x1 - leaf.x0).attr("height", leaf => leaf.y1 - leaf.y0)
    .attr("fill", leaf => leaf.data === objetoFijo ? token("morado") : token("gris"))
    .attr("stroke", token("papel")).attr("stroke-width", 0.9)
    .append("title").text(leaf => leaf.data.tipo_accidente + " · " + entero(leaf.data.accidentes));
  const etiquetas = {
    "1": ["Vehículo", "automotor"],
    "4": ["Objeto fijo"],
    "10": ["Motocicleta"],
  };
  const foco = piezas.filter(leaf => principales.includes(leaf.data));
  const tintaDeEtiqueta = leaf => leaf.data === objetoFijo ? token("papel") : token("tinta");
  foco.append("text").attr("x", 14).attr("y", 35).attr("fill", tintaDeEtiqueta)
    .attr("font-size", 28).attr("font-weight", 750).text(leaf => entero(leaf.data.accidentes));
  foco.append("text").attr("x", 14).attr("y", 58).attr("fill", tintaDeEtiqueta)
    .attr("font-size", 17)
    .selectAll("tspan").data(leaf => etiquetas[leaf.data.codigo_tipaccid] || [leaf.data.tipo_accidente]).join("tspan")
    .attr("x", 14).attr("dy", (_, i) => i === 0 ? 0 : 20).text(label => label);

  const lista = container.append("dl").attr("class", "tipos-clave").attr("aria-label", "Registros por tipo de accidente");
  const entries = lista.selectAll("div").data(ranking).join("div")
    .attr("class", row => row === objetoFijo ? "tipo-principal" : null);
  entries.append("dt").text(row => row.tipo_accidente);
  entries.append("dd").text(row => entero(row.accidentes));
}

function cifrasCapitulo(control, horas, tipos) {
  const pico = d3.greatest(horas, row => row.accidentes);
  const tipo = d3.greatest(tipos, row => row.accidentes);
  const data = [
    [control.accidentes_total, "accidentes registrados en Mérida"],
    [pico.accidentes, "accidentes en la franja del " + pico.dia_semana + " a las " + hora(pico.hora_local)],
    [tipo.accidentes, "registros por " + tipo.tipo_accidente.toLowerCase()],
  ];
  const bloques = d3.select(".cifras").attr("hidden", null).selectAll("div").data(data).join("div")
    .attr("class", "cifra");
  bloques.append("dt").text(row => entero(row[0]));
  bloques.append("dd").text(row => row[1] + " · ATUS, 2021–2024");
}

function mapaRow(row) {
  return {
    ...row,
    accidentes: Number(row.accidentes),
    accidentes_por_km2: row.accidentes_por_km2 === undefined ? null : Number(row.accidentes_por_km2),
    poblacion_2020: row.poblacion_2020 ? Number(row.poblacion_2020) : null,
    accidentes_por_1000_habitantes: row.accidentes_por_1000_habitantes
      ? Number(row.accidentes_por_1000_habitantes) : null,
  };
}

async function iniciar() {
  const codigo = new URLSearchParams(window.location.search).get("escena");
  const solo = ["1", "2", "3", "4"].includes(codigo) ? Number(codigo) : null;
  if (solo) {
    document.body.classList.add("solo-escena");
    d3.selectAll(".escena").attr("hidden", function () {
      return this.id === "escena-" + solo ? null : "";
    });
  }
  const activa = n => solo === null || solo === n;
  const [control, geo, densidad, poblacion, horas, tipos] = await Promise.all([
    activa(1) || activa(3) ? d3.json(dataDir + "control.json", revalidar) : null,
    activa(1) || activa(2) ? d3.json(dataDir + "mapa-base.geojson", revalidar) : null,
    activa(1) ? d3.csv(dataDir + "escena-1.csv", revalidar, mapaRow) : null,
    activa(2) ? d3.csv(dataDir + "escena-2.csv", revalidar, mapaRow) : null,
    activa(3) ? d3.csv(dataDir + "escena-3.csv", revalidar, d3.autoType) : null,
    activa(4) ? d3.csv(dataDir + "escena-4.csv", revalidar, d3.autoType) : null,
  ]);
  if (densidad) escenaDensidad(geo, densidad, control);
  if (poblacion) escenaPoblacion(geo, poblacion);
  if (horas) escenaHoras(horas, control);
  if (tipos) escenaTipos(tipos);
  if (solo === null) cifrasCapitulo(control, horas, tipos);
  document.getElementById("estado").hidden = true;
  document.documentElement.dataset.graficasListas = "true";
}

iniciar().catch(error => {
  document.getElementById("estado").textContent =
    "No se pudieron cargar las gráficas. Abre esta página con un servidor HTTP desde el repositorio.";
  console.error(error);
});
