# Architecture — Hexagone

## 1. Objectif

Tester des décisions sur une France recréée à partir de données officielles, dans le respect des règles réelles, et comparer les résultats à la trajectoire réelle. Pas de score unique, pas d'objectif imposé.

## 2. Principes

1. **Traçabilité** : chaque chiffre affiché indique sa source, sa période, sa date de publication et son statut (observé, prévision officielle, hypothèse, résultat calculé).
2. **Honnêteté du modèle** : les effets simulés sont donnés en fourchette, avec les hypothèses visibles et modifiables. Un effet estimé n'est jamais présenté comme une donnée officielle.
3. **Neutralité** : toutes les mesures, de tous bords, passent par la même fiche et les mêmes sources.
4. **Par étapes** : on livre quelque chose d'utilisable à chaque étape avant d'attaquer la suivante.

## 3. Flux technique

```
Sources officielles (API, fichiers)
        |
        v
Collecteur (script Python, tâche planifiée GitHub Actions)
  - télécharge, normalise, conserve les fichiers bruts
        |
        v
Données normalisées dans le dépôt (dossier data/)
        |
        v
Application web (PWA, hébergée par GitHub Pages)
  - lit data/, fonctionne hors ligne
  - moteur de simulation côté navigateur
```

Le collecteur évite les blocages CORS et protège les clés (stockées plus tard dans les secrets GitHub, jamais dans le code). Le dépôt étant public, rien de secret n'y figure.

## 4. Les quatre couches de données

| Couche | Contenu | Statut affiché |
|---|---|---|
| Observations officielles | chiffres publiés par les producteurs | provisoire, révisé, définitif |
| Prévisions officielles | projections publiées par les organismes | prévision |
| Paramètres de simulation | élasticités, délais, hypothèses | hypothèse (modifiable) |
| Résultats calculés | sorties du moteur | simulation (avec fourchette) |

## 5. Métadonnées minimales par série

```
source_id, organisme, dataset_id, series_id, url_source, licence, unite,
perimetre_geographique, perimetre_institutionnel, periodicite_observation,
frequence_publication, periode_observee, date_publication, date_collecte,
version_source, statut_observation, valeur
```

Les périmètres comptables restent séparés (dette de l'État ≠ dette des administrations publiques) pour éviter les doubles comptes.

## 6. Sources de l'étape 1 (sans clé ni compte)

**Étape 1a — dans le code** (`collector/sources.json`) :

| Domaine | Source | Séries | Rythme réel |
|---|---|---|---|
| Finances publiques | Eurostat | dette publique, solde public, PIB en valeur | annuel |
| Économie | Eurostat | croissance trimestrielle du PIB, inflation (IPCH), chômage (BIT) | trimestriel, mensuel |
| Niveau de vie et bien-être | Eurostat | revenu réel des ménages (indice), coefficient de Gini, pauvreté monétaire, espérance de vie, satisfaction de vie | annuel ; satisfaction de vie irrégulière (enquête ponctuelle) |
| Taux et changes | BCE | taux de dépôt, taux de refinancement, taux à long terme de la France, euro/dollar | quotidien ouvré, mensuel |

**Étape 1b — à ajouter après la première collecte réelle** : Insee (BDM, Melodi), Data Économie (LFI, exécution, balances de l'État), Agence France Trésor (dette de l'État), OFGL (collectivités). Leurs identifiants de séries doivent être vérifiés contre les vraies réponses ; ils ne peuvent pas l'être depuis l'environnement de développement (accès réseau limité).

Le « J+1 » réel ne concerne que quelques familles : taux et changes, énergie, signaux géopolitiques, droit publié. Le reste arrive par paliers, avec sa date de publication.

Le « J+1 » réel ne concerne que quelques familles : taux et changes, énergie, signaux géopolitiques, droit publié. Le reste arrive par paliers, avec sa date de publication.

## 7. Exclusions et reports

- **ACLED** : licence interdisant la redistribution, incompatible avec un dépôt public.
- **Clés et comptes** (Banque de France, EIA, Légifrance/PISTE, UCDP) : reportés après l'étape 1.
- **Cotations de marché intrajournalières** (OAT, Brent, gaz) : pas de source officielle gratuite avec droits clairs.
- **Cour des comptes** : corpus documentaire, pas de flux structuré actuel.

## 8. Indicateurs de résultat (comparaison côte à côte)

- Finances : dette publique, déficit, PIB, croissance.
- Économie : chômage, inflation, pouvoir d'achat.
- Social : inégalités, pauvreté, espérance de vie.
- Ressenti : satisfaction de vie, **estimée par modèle** (les enquêtes sont rares), affichée avec sa fourchette.

## 9. Modes

- **Live** : à chaque ouverture, récupère la veille, applique les chocs du monde réel à la France simulée. Les décisions modifient la France, pas le monde.
- **Accéléré** : simulation sur plusieurs années, avec points de sauvegarde et branches comparables.

## 10. Catalogue de mesures (étape 2)

Chaque mesure a une fiche : ce qu'elle change, délais légaux, effets en fourchette, sources de chaque hypothèse. Format testé d'abord sur trois cas très différents : TVA (impôt), retraites (réforme structurelle), Frexit (rupture). Le catalogue couvre les propositions des principaux candidats, au même format. Contrôle de crédibilité : rejouer une réforme passée (retraites 2023) pour vérifier les ordres de grandeur.

## 11. Étapes

0. Jouer à La Bataille du Budget et à l'Atelier des finances publiques.
1. Tableau de bord de la France réelle.
2. Fiches de mesures, leviers budgétaires, mode accéléré et branches.
3. Réactions des acteurs (opinion, marchés, UE).
4. Mode live complet.
5. Régimes alternatifs, collectivités, Sécu.
6. Époques anciennes (option, avec niveau de fiabilité affiché).

## 12. Décisions prises et points ouverts

- Marchés : pas de pétrole à l'étape 1 (le Brent EIA exige une clé gratuite). Il viendra plus tard, quand le compte EIA sera créé. Pas de gaz en direct : hypothèse de scénario.
- Première collecte réelle faite : 10 séries sur 10 collectées, filtres Eurostat et clés BCE acceptés. Une série était périmée (inflation, jeu Eurostat figé fin 2025) : basculée sur `prc_hicp_minr`. Les producteurs peuvent changer de jeu de données sans prévenir : d'où le badge « données anciennes ».
- Reste à confronter à une source indépendante : dette, solde public et PIB 2025 (ordres de grandeur plausibles).
- Niveau de vie : quatre séries sur cinq collectées avec succès (revenu réel des ménages, Gini, espérance de vie, satisfaction de vie). La pauvreté monétaire (`ilc_li02`) attend ses filtres : la dimension `indic_il` n'existe plus, le prochain message d'erreur listera les dimensions réelles. Le revenu réel des ménages d'Eurostat n'est qu'une approximation du pouvoir d'achat.

## 13. Arborescence du dépôt

```
index.html, style.css, app.js     tableau de bord (PWA)
sw.js, manifest.webmanifest       mode hors ligne et installation
icon.svg
collector/collect.py              collecteur (Python, sans dépendance)
collector/sources.json            liste des séries et leurs métadonnées
collector/test_collect.py         tests sur échantillons
.github/workflows/collecte.yml    tâche planifiée quotidienne (+ lancement manuel)
data/                             données normalisées (écrites par le collecteur)
  index.json                      séries et dernière observation
  status.json                     résultat de la dernière collecte, par série
  <id_serie>.json                 série complète avec métadonnées
```

Garde-fous du collecteur : une série en échec garde sa dernière version valide ; une réponse contenant plusieurs séries est refusée ; le statut de chaque série est écrit à chaque exécution ; les tests tournent avant chaque collecte. Côté page, une série dont la dernière observation est plus ancienne que sa périodicité ne le permet (annuelle 700 jours, trimestrielle 200, mensuelle 130, quotidienne 12) reçoit le badge « données anciennes » ; les taux directeurs, valables jusqu'à la décision suivante, n'ont pas ce contrôle.
