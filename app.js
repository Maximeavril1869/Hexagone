"use strict";

const CATEGORIES = ["Finances publiques", "Économie", "Taux et changes"];
const SVG_NS = "http://www.w3.org/2000/svg";
const STALE_DAYS = 3;

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  }
  for (const child of children || []) node.append(child);
  return node;
}

function formatNumber(value, decimals) {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

// Les dates d'Eurostat sont de la forme « +0100 » : on les normalise (« +01:00 »)
// pour que tous les navigateurs, Safari compris, les comprennent.
function parseDate(iso) {
  if (!iso) return null;
  const date = new Date(String(iso).replace(/([+-]\d{2})(\d{2})$/, "$1:$2"));
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(iso) {
  const date = parseDate(iso);
  if (!date) return iso ? String(iso) : "non fournie par la source";
  return date.toLocaleString("fr-FR", {
    dateStyle: "long",
    timeStyle: "short",
    timeZone: "Europe/Paris",
  });
}

function sparkline(points, decimals, unit) {
  const values = points.map((p) => p.valeur);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "courbe");
  svg.setAttribute("viewBox", "0 0 200 44");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("role", "img");
  const first = points[0];
  const last = points[points.length - 1];
  svg.setAttribute(
    "aria-label",
    "Évolution de " + first.periode + " (" + formatNumber(first.valeur, decimals) + ") à " +
      last.periode + " (" + formatNumber(last.valeur, decimals) + " " + unit + ")"
  );
  if (values.length < 2) return svg;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (i) => 4 + (i * 192) / (values.length - 1);
  const y = (v) => 40 - ((v - min) / span) * 36;
  const coords = values.map((v, i) => x(i).toFixed(1) + "," + y(v).toFixed(1)).join(" ");

  const line = document.createElementNS(SVG_NS, "polyline");
  line.setAttribute("points", coords);
  svg.append(line);
  const dot = document.createElementNS(SVG_NS, "circle");
  dot.setAttribute("cx", x(values.length - 1).toFixed(1));
  dot.setAttribute("cy", y(values[values.length - 1]).toFixed(1));
  dot.setAttribute("r", "3");
  svg.append(dot);
  return svg;
}

function detailRow(label, content) {
  return [el("dt", { text: label }), el("dd", {}, [content])];
}

function card(serie) {
  const decimals = Number.isInteger(serie.decimales) ? serie.decimales : 2;
  const last = serie.derniere;

  const value = el("p", { class: "valeur" }, [
    formatNumber(last.valeur, decimals),
    el("span", { class: "unite", text: serie.unite }),
  ]);

  const period = el("p", { class: "periode" }, [
    last.periode + " · ",
    el("span", { class: "badge", text: last.statut }),
  ]);

  const link = el("a", { href: serie.url_source, target: "_blank", rel: "noopener noreferrer", text: "Jeu de données" });

  const collected = parseDate(serie.date_collecte);
  const ageDays = collected ? (Date.now() - collected.getTime()) / 86400000 : null;
  const stale = ageDays !== null && ageDays > STALE_DAYS;

  const details = el("details", {}, [el("summary", { text: "Source, périmètre et licence" })]);
  const dl = el("dl");
  const rows = [
    ["Producteur", serie.organisme],
    ["Jeu de données", link],
    ["Périmètre", serie.perimetre_institutionnel + " — " + serie.perimetre_geographique],
    ["Périodicité", serie.periodicite_observation],
    ["Publication", serie.frequence_publication],
    ["Dernière mise à jour par la source", formatDate(serie.date_publication)],
    ["Collectée par Hexagone le", formatDate(serie.date_collecte) + (stale ? " (collecte ancienne)" : "")],
    ["Licence", serie.licence],
  ];
  for (const [label, content] of rows) {
    for (const node of detailRow(label, typeof content === "string" ? document.createTextNode(content) : content)) {
      dl.append(node);
    }
  }
  details.append(dl);

  return el("article", { class: "carte" }, [
    el("h3", { text: serie.nom }),
    value,
    period,
    sparkline(serie.serie, decimals, serie.unite),
    details,
  ]);
}

async function loadJson(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(path + " : HTTP " + response.status);
  return response.json();
}

function showAlert(status, series) {
  const failed = (status.resultats || []).filter((r) => !r.ok);
  const box = document.getElementById("alerte");
  if (failed.length === 0) {
    box.hidden = true;
    return;
  }
  const names = new Map(series.map((s) => [s.id, s.nom]));
  const list = el("ul");
  for (const r of failed) {
    const outcome = names.has(r.id)
      ? "dernière version valide affichée"
      : "aucune donnée disponible pour l'instant";
    list.append(el("li", { text: (names.get(r.id) || r.id) + " — " + outcome + " (" + r.erreur + ")" }));
  }
  box.replaceChildren(
    el("strong", { text: "Certaines séries n'ont pas pu être mises à jour lors de la dernière collecte :" }),
    list
  );
  box.hidden = false;
}

function showEmpty(main) {
  main.replaceChildren(
    el("div", { class: "vide" }, [
      el("p", { text: "Aucune donnée collectée pour l'instant." }),
      el("p", { text: "Lance la tâche « Collecte » depuis l'onglet Actions du dépôt GitHub : les chiffres apparaîtront ici après quelques minutes." }),
    ])
  );
  document.getElementById("collecte").textContent = "Aucune collecte effectuée.";
}

async function main() {
  const main = document.getElementById("contenu");
  let index;
  try {
    index = await loadJson("data/index.json");
  } catch (err) {
    showEmpty(main);
    return;
  }
  let status = { resultats: [] };
  try {
    status = await loadJson("data/status.json");
  } catch (err) {
    /* le statut est facultatif */
  }

  const series = index.series || [];
  if (series.length === 0) {
    showEmpty(main);
    return;
  }

  document.getElementById("collecte").textContent =
    "Dernière collecte : " + formatDate(status.execution || index.genere);
  showAlert(status, series);

  const known = new Set(CATEGORIES);
  const order = CATEGORIES.concat([...new Set(series.map((s) => s.categorie))].filter((c) => !known.has(c)));
  const sections = [];
  for (const category of order) {
    const members = series.filter((s) => s.categorie === category);
    if (members.length === 0) continue;
    sections.push(el("h2", { text: category }));
    sections.push(el("div", { class: "grille" }, members.map(card)));
  }
  main.replaceChildren(...sections);
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
main();
