#!/usr/bin/env python3
"""Collecteur Hexagone.

Télécharge des séries officielles (Eurostat, BCE, Insee), les normalise avec
leurs métadonnées et les écrit dans data/. Aucune dépendance externe, aucune clé.

Règles :
- une source qui échoue ne détruit jamais la dernière version valide ;
- chaque exécution écrit data/status.json (succès et erreurs par série) ;
- le script ne sort en erreur que si AUCUNE série n'a pu être collectée.
"""
import csv
import io
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_DIR = ROOT / "data"
CONFIG_PATH = HERE / "sources.json"

USER_AGENT = "Hexagone-collecteur/0.1 (+https://github.com/Maximeavril1869/Hexagone)"
EUROSTAT_BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
ECB_BASE = "https://data-api.ecb.europa.eu/service/data/"
# Service web SDMX direct de la Banque de données macroéconomiques (BDM) de l'Insee.
# Distinct du portail api.insee.fr (qui exige une inscription).
INSEE_BDM_BASE = "https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/"

# Clés de configuration purement techniques, non reprises dans les métadonnées.
TECH_KEYS = {"params", "since", "derniers", "keep", "source"}
SPARK_POINTS = 60


class FetchError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def http_get(url, timeout=60, retries=3):
    """GET avec nouvelles tentatives sur erreurs réseau et 5xx/429."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8-sig")
        except urllib.error.HTTPError as exc:
            if exc.code < 500 and exc.code != 429:
                # Le corps de la réponse explique souvent quel paramètre est refusé.
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace").strip().replace("\n", " ")[:300]
                except Exception:
                    pass
                message = "HTTP %d" % exc.code + (" : " + detail if detail else "")
                raise FetchError(exc.code, message) from exc
            last = FetchError(exc.code, "HTTP %d" % exc.code)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = FetchError(None, str(exc))
        time.sleep(2 * (attempt + 1))
    raise last


# --------------------------------------------------------------------------
# Analyse des formats
# --------------------------------------------------------------------------

EUROSTAT_FLAGS = {
    "p": "provisoire",
    "e": "estimé",
    "f": "prévision officielle",
    "b": "rupture de série",
    "u": "faible fiabilité",
    "r": "révisé",
    "d": "définition différente",
    "c": "confidentiel",
    "n": "non significatif",
    "s": "estimation d'Eurostat",
    "i": "voir les métadonnées",
    "z": "sans objet",
}


def _eurostat_status(flag):
    if not flag:
        return "publié"
    labels = []
    for ch in flag:
        labels.append(EUROSTAT_FLAGS.get(ch, "drapeau Eurostat « %s »" % ch))
    return ", ".join(labels)


def _category_codes(doc, dim, limit=30):
    """Liste lisible des codes d'une dimension, pour les messages d'erreur."""
    category = doc.get("dimension", {}).get(dim, {}).get("category", {})
    index = category.get("index")
    if not index:
        return "codes non fournis"
    if isinstance(index, list):
        codes = list(index)
    else:
        codes = [code for code, _ in sorted(index.items(), key=lambda kv: kv[1])]
    labels = category.get("label", {})
    shown = [("%s (%s)" % (c, labels[c])) if c in labels else c for c in codes[:limit]]
    if len(codes) > limit:
        shown.append("… %d au total" % len(codes))
    return ", ".join(shown)


def parse_jsonstat(doc):
    """Extrait une série unique d'un document JSON-stat 2.0 (Eurostat).

    Refuse toute réponse qui contiendrait plusieurs séries : mieux vaut une
    erreur explicite qu'une série mélangée. Le message d'erreur liste les
    dimensions à préciser et leurs codes possibles.
    Retourne (observations, date_de_mise_a_jour).
    """
    if "error" in doc:
        raise ValueError("réponse d'erreur du producteur : %s" % doc["error"])
    ids = doc["id"]
    sizes = doc["size"]
    if "time" not in ids:
        raise ValueError("dimension « time » absente")
    ambiguous = [
        "« %s » a %d valeurs [%s]" % (dim, size, _category_codes(doc, dim))
        for dim, size in zip(ids, sizes)
        if dim != "time" and size != 1
    ]
    if ambiguous:
        raise ValueError("série ambiguë, filtres à préciser : " + " ; ".join(ambiguous))
    t_pos = ids.index("time")
    stride = 1
    for size in sizes[t_pos + 1:]:
        stride *= size

    categories = doc["dimension"]["time"]["category"]["index"]
    if isinstance(categories, list):
        categories = {code: i for i, code in enumerate(categories)}

    values = doc.get("value", {})
    if isinstance(values, list):
        values = {str(i): v for i, v in enumerate(values) if v is not None}
    status = doc.get("status", {})
    if isinstance(status, list):
        status = {str(i): s for i, s in enumerate(status) if s}

    observations = []
    for code, pos in sorted(categories.items(), key=lambda kv: kv[1]):
        key = str(pos * stride)
        if key not in values or values[key] is None:
            continue
        observations.append(
            {
                "periode": code,
                "valeur": values[key],
                "statut": _eurostat_status(status.get(key, "")),
            }
        )
    return observations, doc.get("updated")


ECB_STATUS = {"P": "provisoire", "E": "estimé", "F": "prévision officielle"}


def parse_ecb_csv(text):
    """Extrait une série unique d'un CSV de l'API de données de la BCE."""
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("réponse vide")
    for needed in ("TIME_PERIOD", "OBS_VALUE"):
        if needed not in rows[0]:
            raise ValueError("colonne « %s » absente" % needed)
    if "KEY" in rows[0]:
        keys = {row["KEY"] for row in rows}
        if len(keys) > 1:
            raise ValueError("série ambiguë : %d clés dans la réponse" % len(keys))
    observations = []
    for row in rows:
        raw = (row.get("OBS_VALUE") or "").strip()
        if raw == "":
            continue
        observations.append(
            {
                "periode": row["TIME_PERIOD"],
                "valeur": float(raw),
                "statut": ECB_STATUS.get((row.get("OBS_STATUS") or "").strip(), "publié"),
            }
        )
    observations.sort(key=lambda o: o["periode"])
    return observations


# Codes de statut des observations de la BDM : seuls A, P et E sont traduits ;
# tout autre code est repris tel quel plutôt que deviné.
INSEE_STATUS = {"A": "publié", "P": "provisoire", "E": "estimé"}


def _local_name(name):
    """Nom sans espace de noms XML : « {urn:x}Obs » devient « Obs »."""
    return name.rsplit("}", 1)[-1] if isinstance(name, str) else ""


def _insee_attrs(element):
    return {_local_name(k).upper(): v for k, v in element.attrib.items()}


def parse_insee_sdmx(text):
    """Extrait une série unique d'une réponse SDMX-ML de la BDM de l'Insee.

    Lecture indépendante des espaces de noms (seuls comptent les éléments
    « Series » et « Obs » et leurs attributs TIME_PERIOD, OBS_VALUE,
    OBS_STATUS). Refuse une réponse à plusieurs séries ou sans observation, avec
    un message qui décrit ce qui a été reçu, pour pouvoir corriger la
    configuration sans accès direct à l'API.
    Retourne (observations, date_de_mise_a_jour).
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        extrait = " ".join(text[:200].split())
        raise ValueError("réponse Insee illisible (%s) : %s" % (exc, extrait))

    series = [e for e in root.iter() if _local_name(e.tag) == "Series"]
    if len(series) > 1:
        ids = [_insee_attrs(s).get("IDBANK", "?") for s in series]
        raise ValueError("série ambiguë : %d séries dans la réponse (%s)" % (len(series), ", ".join(ids[:10])))
    scope = series[0] if series else root
    meta = _insee_attrs(scope) if series else {}

    elements = [e for e in scope.iter() if _local_name(e.tag) == "Obs"]
    if not elements:
        presents = sorted({_local_name(e.tag) for e in root.iter()})
        raise ValueError(
            "aucune observation (<Obs>) dans la réponse Insee ; éléments présents : %s ; attributs de la série : %s"
            % (", ".join(presents), ", ".join(sorted(meta)) or "aucun")
        )
    first = _insee_attrs(elements[0])
    if "TIME_PERIOD" not in first or "OBS_VALUE" not in first:
        raise ValueError(
            "attributs de <Obs> inattendus : %s (attendus : TIME_PERIOD, OBS_VALUE)" % ", ".join(sorted(first))
        )

    observations = []
    for element in elements:
        attrs = _insee_attrs(element)
        raw = (attrs.get("OBS_VALUE") or "").strip()
        if raw == "" or raw.lower() == "nan":
            continue
        code = (attrs.get("OBS_STATUS") or "").strip()
        status = INSEE_STATUS.get(code) if code else "publié"
        observations.append(
            {
                "periode": attrs["TIME_PERIOD"],
                "valeur": float(raw),
                "statut": status or "statut Insee « %s »" % code,
            }
        )
    observations.sort(key=lambda o: o["periode"])

    updated = meta.get("LAST_UPDATE")
    if updated:
        try:
            datetime.fromisoformat(updated)
        except ValueError:
            updated = None  # format inattendu : mieux vaut « non fournie » qu'une date fausse
    return observations, updated or None


# --------------------------------------------------------------------------
# Collecte
# --------------------------------------------------------------------------

def build_url(cfg, with_since=True):
    if cfg["source"] == "eurostat":
        params = {"format": "JSON", "lang": "EN"}
        params.update(cfg["params"])
        if with_since and cfg.get("since"):
            params["sinceTimePeriod"] = cfg["since"]
        return EUROSTAT_BASE + cfg["dataset"] + "?" + urllib.parse.urlencode(params)
    if cfg["source"] == "bce":
        query = {"format": "csvdata"}
        if cfg.get("derniers"):
            query["lastNObservations"] = cfg["derniers"]
        return ECB_BASE + cfg["flux"] + "/" + cfg["cle"] + "?" + urllib.parse.urlencode(query)
    if cfg["source"] == "insee":
        url = INSEE_BDM_BASE + urllib.parse.quote(str(cfg["idbank"]), safe="")
        if cfg.get("derniers"):
            url += "?" + urllib.parse.urlencode({"lastNObservations": cfg["derniers"]})
        return url
    raise ValueError("source inconnue : %s" % cfg["source"])


def collect_series(cfg, fetch, now):
    url = build_url(cfg)
    try:
        text = fetch(url)
    except FetchError as exc:
        # Certains jeux refusent le filtre temporel : on réessaie sans lui.
        if exc.code == 400 and cfg["source"] == "eurostat" and cfg.get("since"):
            url = build_url(cfg, with_since=False)
            text = fetch(url)
        else:
            raise

    if cfg["source"] == "eurostat":
        observations, updated = parse_jsonstat(json.loads(text))
    elif cfg["source"] == "insee":
        observations, updated = parse_insee_sdmx(text)
    else:
        observations, updated = parse_ecb_csv(text), None

    if not observations:
        raise ValueError("aucune observation dans la réponse")
    observations = observations[-int(cfg.get("keep", 120)):]

    meta = {k: v for k, v in cfg.items() if k not in TECH_KEYS}
    meta["date_publication"] = updated
    meta["date_collecte"] = now.isoformat(timespec="seconds")
    meta["url_requete"] = url
    return {"meta": meta, "observations": observations}


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def index_entry(doc):
    entry = dict(doc["meta"])
    obs = doc["observations"]
    entry["derniere"] = obs[-1]
    entry["serie"] = [
        {"periode": o["periode"], "valeur": o["valeur"]} for o in obs[-SPARK_POINTS:]
    ]
    return entry


def collect_all(config, fetch, data_dir, now):
    results = []
    ok = 0
    for cfg in config["series"]:
        sid = cfg["id"]
        try:
            doc = collect_series(cfg, fetch, now)
            write_json(data_dir / ("%s.json" % sid), doc)
            ok += 1
            results.append(
                {
                    "id": sid,
                    "ok": True,
                    "observations": len(doc["observations"]),
                    "derniere_periode": doc["observations"][-1]["periode"],
                }
            )
        except Exception as exc:  # une série en échec ne doit pas bloquer les autres
            results.append({"id": sid, "ok": False, "erreur": "%s : %s" % (type(exc).__name__, exc)})

    # L'index reprend les fichiers présents, y compris les dernières versions
    # valides de séries qui ont échoué cette fois.
    index = []
    for cfg in config["series"]:
        path = data_dir / ("%s.json" % cfg["id"])
        if path.exists():
            index.append(index_entry(json.loads(path.read_text(encoding="utf-8"))))
    stamp = now.isoformat(timespec="seconds")
    write_json(data_dir / "index.json", {"genere": stamp, "series": index})
    write_json(data_dir / "status.json", {"execution": stamp, "resultats": results})
    return ok, results


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    ok, results = collect_all(config, http_get, DATA_DIR, now)
    for r in results:
        if r["ok"]:
            print("OK      %-22s %s (%d obs.)" % (r["id"], r["derniere_periode"], r["observations"]))
        else:
            print("ERREUR  %-22s %s" % (r["id"], r["erreur"]))
    print("%d série(s) sur %d collectée(s)." % (ok, len(results)))
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
