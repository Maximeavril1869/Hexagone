import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import collect

JSONSTAT_OK = {
    "id": ["freq", "unit", "coicop", "geo", "time"],
    "size": [1, 1, 1, 1, 4],
    "updated": "2026-10-30T11:00:00+0100",
    "dimension": {
        "time": {"category": {"index": {"2025-01": 0, "2025-02": 1, "2025-03": 2, "2025-04": 3}}}
    },
    "value": {"0": 1.5, "1": 1.7, "3": 2.0},
    "status": {"3": "p"},
}

JSONSTAT_AMBIGU = {
    "id": ["geo", "time"],
    "size": [2, 2],
    "dimension": {"time": {"category": {"index": {"2024": 0, "2025": 1}}}},
    "value": {"0": 1.0},
}

JSONSTAT_TEMPS_NON_FINAL = {
    "id": ["time", "geo"],
    "size": [3, 1],
    "dimension": {"time": {"category": {"index": ["2023", "2024", "2025"]}}},
    "value": [10.0, None, 12.0],
}

ECB_OK = (
    "KEY,FREQ,TIME_PERIOD,OBS_VALUE,OBS_STATUS\n"
    "FM.B.U2.EUR.4F.KR.DFR.LEV,B,2026-10-01,2.00,A\n"
    "FM.B.U2.EUR.4F.KR.DFR.LEV,B,2026-10-02,2.00,A\n"
    "FM.B.U2.EUR.4F.KR.DFR.LEV,B,2026-10-05,,A\n"
    "FM.B.U2.EUR.4F.KR.DFR.LEV,B,2026-10-06,2.25,P\n"
)


class TestParsing(unittest.TestCase):
    def test_jsonstat_valeurs_manquantes_et_statut(self):
        obs, updated = collect.parse_jsonstat(JSONSTAT_OK)
        self.assertEqual([o["periode"] for o in obs], ["2025-01", "2025-02", "2025-04"])
        self.assertEqual(obs[-1]["valeur"], 2.0)
        self.assertEqual(obs[-1]["statut"], "provisoire")
        self.assertEqual(obs[0]["statut"], "publié")
        self.assertEqual(updated, "2026-10-30T11:00:00+0100")

    def test_drapeaux_eurostat_traduits(self):
        self.assertEqual(collect._eurostat_status("u"), "faible fiabilité")
        self.assertEqual(collect._eurostat_status("bp"), "rupture de série, provisoire")
        self.assertEqual(collect._eurostat_status(""), "publié")
        self.assertIn("«", collect._eurostat_status("q"))  # drapeau inconnu : repris tel quel

    def test_jsonstat_refuse_les_series_ambigues(self):
        with self.assertRaises(ValueError):
            collect.parse_jsonstat(JSONSTAT_AMBIGU)

    def test_jsonstat_ambiguite_liste_les_codes_possibles(self):
        doc = {
            "id": ["sex", "age", "time"],
            "size": [3, 2, 1],
            "dimension": {
                "sex": {"category": {"index": {"F": 0, "M": 1, "T": 2}, "label": {"T": "Total"}}},
                "age": {"category": {"index": ["Y_LT1", "Y1"]}},
                "time": {"category": {"index": {"2024": 0}}},
            },
            "value": {"0": 1.0},
        }
        with self.assertRaises(ValueError) as ctx:
            collect.parse_jsonstat(doc)
        message = str(ctx.exception)
        self.assertIn("« sex » a 3 valeurs", message)
        self.assertIn("T (Total)", message)
        self.assertIn("« age » a 2 valeurs", message)
        self.assertIn("Y_LT1", message)

    def test_jsonstat_temps_en_premiere_dimension_et_valeurs_en_liste(self):
        obs, _ = collect.parse_jsonstat(JSONSTAT_TEMPS_NON_FINAL)
        self.assertEqual([(o["periode"], o["valeur"]) for o in obs], [("2023", 10.0), ("2025", 12.0)])

    def test_jsonstat_erreur_producteur(self):
        with self.assertRaises(ValueError):
            collect.parse_jsonstat({"error": [{"status": 404}]})

    def test_ecb_csv(self):
        obs = collect.parse_ecb_csv(ECB_OK)
        self.assertEqual(len(obs), 3)
        self.assertEqual(obs[-1], {"periode": "2026-10-06", "valeur": 2.25, "statut": "provisoire"})

    def test_ecb_csv_refuse_plusieurs_cles(self):
        text = "KEY,TIME_PERIOD,OBS_VALUE\nA,2026-01,1\nB,2026-01,2\n"
        with self.assertRaises(ValueError):
            collect.parse_ecb_csv(text)


class TestCollecte(unittest.TestCase):
    CONFIG = {
        "series": [
            {
                "id": "inflation",
                "nom": "Inflation",
                "categorie": "Économie",
                "source": "eurostat",
                "dataset": "prc_hicp_manr",
                "params": {"geo": "FR"},
                "since": "2025-01",
                "keep": 2,
                "unite": "%",
            },
            {
                "id": "depot",
                "nom": "Taux de dépôt",
                "categorie": "Taux et changes",
                "source": "bce",
                "flux": "FM",
                "cle": "B.U2.EUR.4F.KR.DFR.LEV",
                "derniers": 10,
                "keep": 10,
                "unite": "%",
            },
        ]
    }
    NOW = datetime(2026, 11, 6, 5, 17, tzinfo=timezone.utc)

    def fetch_ok(self, url):
        return json.dumps(JSONSTAT_OK) if "eurostat" in url else ECB_OK

    def test_collecte_complete_et_troncature(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            ok, results = collect.collect_all(self.CONFIG, self.fetch_ok, data, self.NOW)
            self.assertEqual(ok, 2)
            doc = json.loads((data / "inflation.json").read_text(encoding="utf-8"))
            self.assertEqual(len(doc["observations"]), 2)  # keep = 2
            self.assertEqual(doc["meta"]["date_publication"], "2026-10-30T11:00:00+0100")
            self.assertNotIn("params", doc["meta"])
            index = json.loads((data / "index.json").read_text(encoding="utf-8"))
            self.assertEqual([s["id"] for s in index["series"]], ["inflation", "depot"])
            self.assertEqual(index["series"][0]["derniere"]["periode"], "2025-04")

    def test_une_source_en_echec_garde_la_derniere_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            collect.collect_all(self.CONFIG, self.fetch_ok, data, self.NOW)
            avant = (data / "inflation.json").read_text(encoding="utf-8")

            def fetch_eurostat_en_panne(url):
                if "eurostat" in url:
                    raise collect.FetchError(503, "HTTP 503")
                return ECB_OK

            ok, results = collect.collect_all(self.CONFIG, fetch_eurostat_en_panne, data, self.NOW)
            self.assertEqual(ok, 1)
            self.assertFalse(results[0]["ok"])
            self.assertIn("503", results[0]["erreur"])
            self.assertEqual((data / "inflation.json").read_text(encoding="utf-8"), avant)
            index = json.loads((data / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(len(index["series"]), 2)  # la série en panne reste dans l'index

    def test_repli_sans_filtre_temporel_sur_http_400(self):
        urls = []

        def fetch(url):
            urls.append(url)
            if "sinceTimePeriod" in url:
                raise collect.FetchError(400, "HTTP 400")
            return json.dumps(JSONSTAT_OK)

        with tempfile.TemporaryDirectory() as tmp:
            ok, _ = collect.collect_all(
                {"series": [self.CONFIG["series"][0]]}, fetch, Path(tmp), self.NOW
            )
        self.assertEqual(ok, 1)
        self.assertEqual(len(urls), 2)
        self.assertNotIn("sinceTimePeriod", urls[1])

    def test_urls(self):
        url = collect.build_url(self.CONFIG["series"][0])
        self.assertTrue(url.startswith(collect.EUROSTAT_BASE + "prc_hicp_manr?"))
        self.assertIn("geo=FR", url)
        self.assertIn("sinceTimePeriod=2025-01", url)
        url = collect.build_url(self.CONFIG["series"][1])
        self.assertEqual(
            url,
            collect.ECB_BASE + "FM/B.U2.EUR.4F.KR.DFR.LEV?format=csvdata&lastNObservations=10",
        )

    def test_sources_json_est_coherent(self):
        config = json.loads(collect.CONFIG_PATH.read_text(encoding="utf-8"))
        ids = [s["id"] for s in config["series"]]
        self.assertEqual(len(ids), len(set(ids)))
        for s in config["series"]:
            for champ in ("nom", "categorie", "source", "organisme", "unite", "licence", "url_source"):
                self.assertIn(champ, s, "%s : champ « %s » manquant" % (s["id"], champ))
            collect.build_url(s)


if __name__ == "__main__":
    unittest.main()
