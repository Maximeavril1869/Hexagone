# Carnet de bord — Hexagone

Ce fichier retrace toutes les opérations effectuées, pour pouvoir reprendre le projet où il en est. Les entrées les plus récentes sont en bas.

## État actuel

- Étape en cours : étape 1b — ajout des sources françaises (Insee d'abord).
- Dépôt : public (pour la page GitHub Pages). Passage en privé possible plus tard.
- Étape 1a terminée : 15 séries sur 15 collectées et affichées (Eurostat, BCE).
- Étape 1b : lecteur Insee (BDM) écrit et testé sur échantillon, 1 série configurée (IPCH Insee), en attente de la première collecte réelle. Pouvoir d'achat par unité de consommation : idBank introuvable pour l'instant.
- Rien de simulé pour l'instant.

## Journal

### 2026-11-06 — Cadrage et lancement

- Idée : simulateur de gouvernance de la France, nourri de données officielles, avec deux modes (live à J+1 pour les chocs mondiaux, accéléré avec branches).
- Inventaire des sources et API publiques obtenu via Perplexity (voir ARCHITECTURE.md pour le tri retenu).
- Constat sur l'existant : La Bataille du Budget (2026), Cyber-Budget (2006), l'Atelier des finances publiques, Government Simulator, Democracy 4. Aucun ne combine données à jour, chocs mondiaux réels, procédure légale, régimes alternatifs et branches comparables.
- Reformulation : le projet est un banc d'essai de mesures (retraite par capitalisation, Frexit, changement de régime...) plus qu'un jeu de gestion.
- Périmètre réduit par étapes : 0 jouer aux jeux existants, 1 tableau de bord réel, 2 fiches de mesures + branches, puis le reste.
- Décisions : dépôt public « Hexagone » ; collecteur = tâche planifiée GitHub qui dépose les données dans le dépôt ; pas de clés ni de comptes en étape 1 ; ACLED exclu (licence).
- Fichiers créés : README.md, LICENSE, CARNET_DE_BORD.md, ARCHITECTURE.md.

### 2026-11-06 — Étape 1a : collecteur et tableau de bord

- Décision : pas de pétrole à l'étape 1 (clé EIA requise), taux et changes BCE conservés.
- Test d'accès réseau depuis l'environnement de développement : Eurostat et BCE refusés (403 du proxy). Le collecteur n'a donc pas pu être essayé sur les vraies API ; il est vérifié par 11 tests sur échantillons (formats JSON-stat et CSV, séries ambiguës refusées, conservation de la dernière version valide en cas de panne, repli sans filtre temporel sur erreur 400).
- Créé : `collector/` (collect.py, sources.json, test_collect.py), tableau de bord (index.html, style.css, app.js, sw.js, manifest, icône), `.github/workflows/collecte.yml`.
- 10 séries configurées : dette publique, solde public, PIB (Eurostat annuel) ; croissance trimestrielle, inflation, chômage (Eurostat) ; taux de dépôt, taux de refinancement, taux long terme France, euro/dollar (BCE).
- Page contrôlée visuellement dans un vrai navigateur (mobile clair, bureau sombre) avec des données d'exemple fictives, jamais versées au dépôt. Une correction : le message d'alerte distingue maintenant « dernière version valide affichée » et « aucune donnée disponible ».
- À faire ensuite : lancer la première collecte réelle (onglet Actions, « Collecte », « Run workflow »), lire les erreurs éventuelles, corriger les filtres ; puis activer GitHub Pages ; puis étape 1b (Insee, Data Économie, AFT, OFGL).

### 2026-11-06 — Première ouverture de la page

- La page est en ligne (GitHub Pages actif) et affiche l'état vide : aucune collecte n'a encore écrit de données dans le dépôt (vérifié : pas de dossier `data/` sur `main`).
- Défaut corrigé : si toutes les séries échouaient, rien n'était enregistré et la page ne disait pas pourquoi. L'étape d'enregistrement du workflow s'exécute désormais même après un échec, et la page affiche les erreurs de la dernière collecte.

### 2026-11-06 — Première collecte réelle et vérifications

- Première collecte réussie : 10 séries sur 10, 12 fichiers poussés par `hexagone-bot`. L'application mobile GitHub affichait « Triggered via pull request » alors que le workflow n'a que deux déclencheurs (planification, lancement manuel) : probablement un affichage de l'application, non confirmé.
- Vérifications contre des sources externes : taux BCE 2,5 % (dépôt) et 2,65 % (refinancement) au 16 septembre 2026, cohérents avec la presse (hausse de 25 points de base à cette date) ; chômage Eurostat 8,5 % en septembre 2026, cohérent avec l'Insee (8,1 % au T1 et 8,3 % au T2 2026) ; dette 2025 à 115,7 % du PIB et solde à −5,1 % : ordres de grandeur plausibles, pas encore confrontés à une source indépendante.
- Anomalie : inflation arrêtée à 2025-12, dernière mise à jour par Eurostat en février 2026. Cause : le jeu `prc_hicp_manr` est figé fin 2025 ; son successeur est `prc_hicp_minr` (classification ECOICOP version 2, filtres `coicop18=TOTAL`, `unit=RCH_A`, `geo=FR`). Série basculée sur ce jeu.
- Ajouts : badge « données anciennes » quand la dernière observation est plus vieille que ne le permet la périodicité de la série (aurait signalé l'anomalie de l'inflation) ; les taux directeurs BCE s'affichent « en vigueur depuis le [date de la dernière décision] », car la série ne change qu'aux décisions.
- À vérifier au prochain lancement : l'inflation doit atteindre 2026-09 ou 2026-10. Si une erreur « série ambiguë » ou HTTP 400 apparaît sur cette série, lire le nom de la dimension dans le message et ajuster `sources.json`.

### 2026-11-06 — Cinq indicateurs de niveau de vie et de bien-être

- Constat : le tableau de bord ne couvrait que la moitié des indicateurs de réussite demandés. Ajout d'une section « Niveau de vie et bien-être » : revenu disponible réel des ménages par habitant (`tepsr_wc310`, approximation du pouvoir d'achat), coefficient de Gini (`ilc_di12`), pauvreté monétaire à 60 % du revenu médian (`ilc_li02`), espérance de vie à la naissance (`demo_mlexpec`), satisfaction de vie (`ilc_pw01`, enquête irrégulière, donc sans contrôle de fraîcheur).
- Les filtres de ces cinq séries n'ont pas pu être confirmés (l'API d'Eurostat n'est pas accessible depuis l'environnement de développement ni depuis la recherche web) : codes probables, à valider au premier lancement. Les plus incertains : `Y_GE16` (âge, satisfaction de vie) et les filtres de `tepsr_wc310` (aucun filtre autre que la France).
- Le collecteur se diagnostique mieux : une réponse ambiguë liste les dimensions à préciser avec leurs codes possibles ; une erreur HTTP 4xx reprend le texte d'erreur du producteur. Tests : 12.
- État de la collecte : aucun lancement depuis la correction de l'inflation (dernier passage du robot à 17:38, heure de Paris). Un seul lancement prendra en compte l'inflation corrigée et les cinq nouvelles séries.

### 2026-11-06 (soir) — Deuxième collecte réelle : 14 séries sur 15

- Inflation à jour : 3,8 % en octobre 2026 (IPCH, estimation rapide), contre 0,7 % en décembre 2025. Recoupement : la presse rapporte une inflation nationale de 3,4 % en octobre 2026 (énergie à +24,1 %) ; l'IPCH, plus élevé de quelques dixièmes, est de l'ordre attendu. Le chiffre IPCH publié par l'Insee n'a pas été consulté.
- Indicateurs de niveau de vie acceptés par Eurostat (filtres justes) : revenu réel des ménages 112,3 (2025), Gini 30,4 (2025), espérance de vie 83,0 (2024, provisoire), satisfaction de vie 7,1 sur 10 (2025, drapeau « u » : faible fiabilité).
- Échec : pauvreté monétaire. Eurostat répond « Dimension INDIC_IL is not defined » : `ilc_li02` n'a plus cette dimension. Filtres réduits à la France seule, pour que la prochaine erreur liste les vraies dimensions et leurs codes.
- Drapeaux Eurostat désormais traduits (u faible fiabilité, r révisé, d définition différente, c confidentiel, n non significatif, s estimation d'Eurostat, i voir les métadonnées, z sans objet).

### 2026-11-06 (soir) — Pauvreté corrigée et explications en clair

- La collecte de 19:04 a listé les dimensions de `ilc_li02` : `statinfo` (MED_EI / MEAN_EI), `unit` (PC / THS_PER), `rskpovth` (A_40…B_70), `sex`, `age`. Filtres posés : `statinfo=MED_EI`, `unit=PC`, `rskpovth=B_60` (sous 60 % du revenu médian), `sex=T`, `age=TOTAL`. À confirmer au prochain lancement.
- Ajout de `explications.json` (écrit à la main, hors collecte) : une phrase d'introduction par rubrique et une explication « En clair » par série, affichée en tête du déroulé de chaque carte. Aucune collecte nécessaire pour qu'elles apparaissent.
- Lenteur d'actualisation signalée par l'utilisateur : pas de cause établie (voir échange). Pistes : déploiement de GitHub Pages après chaque envoi du robot, cache du navigateur ou de l'application installée.

### 2026-11-06 (soir) — Pages en panne, puis cache de l'application

- Trois déploiements GitHub Pages ont échoué (« Deployment failed, try again later », 19:04, 19:08, 19:19 heure de Paris) alors que la construction réussissait : problème côté GitHub, pas dans le code. Un déploiement a fini par passer à 19:23 (commit 32372f2).
- Capture de l'utilisateur à 19:25 : données à jour (collecte de 19:22) mais ancien code affiché (pas de ligne « En clair »). Cause probable : le navigateur gardait `app.js` en cache HTTP (GitHub Pages l'autorise 10 minutes). Correctif : le service worker demande désormais toujours une revalidation (`cache: "no-cache"`), cache renommé `hexagone-v2`.

### 2026-11-06 (soir) — Étape 1b : début avec l'Insee

- Périmètre décidé avec l'utilisateur : Insee seul pour commencer ; les « En clair » sont poussés directement, sans relecture préalable.
- Tests réseau depuis l'environnement de développement : Insee (`api.insee.fr`, `www.insee.fr`) et Data Économie refusés par le proxy (HTTP 403 à la connexion) ; AFT et OFGL échouent aussi à la connexion (cause non détaillée). Même situation que pour Eurostat et la BCE : les identifiants se valident donc sur GitHub. Aucune tentative de contournement.
- Recoupements faits sur les pages Insee (lecture seule) : IPCH d'octobre 2026 = +3,8 % (septembre : +3,4 %), IPC national = +3,4 %, estimation provisoire du 30 octobre 2026, résultats définitifs le 13 novembre 2026. L'écart 3,8 % / 3,4 % observé entre Eurostat et l'indice national est donc l'écart IPCH / IPC, pas une erreur. Pouvoir d'achat par unité de consommation : −0,7 % en 2025 (provisoire) et +2,2 % en 2024 (semi-définitif), tableau paru le 29/05/2026 ; la page de l'année précédente donnait +2,1 % pour 2024 (révision).
- Perplexity a fourni l'idBank 011812232 (IPCH, base 2025, glissement annuel, France, ensemble), non confirmé par une vraie réponse de l'API : il n'a pu récupérer aucun XML. Il n'a pas trouvé l'idBank de la série pouvoir d'achat par unité de consommation en base 2020 (le 010562205 qu'il a lu est une ancienne série en base 2014, arrêtée en 2021 : à ne pas utiliser).
- Code : nouvelle source `insee` dans `collect.py` (`parse_insee_sdmx`, lecture du SDMX-ML de `bdm.insee.fr` indépendante des espaces de noms ; refuse plusieurs séries ; décrit ce qui a été reçu quand il ne trouve pas d'observation ; statuts A, P, E traduits, autre code repris tel quel). Série `inflation_ipch_insee` ajoutée à `sources.json` après l'IPCH d'Eurostat, avec son « En clair ». 9 tests ajoutés, 22 au total, tous passés. Les échantillons XML des tests sont écrits à la main, pas de vraies réponses.
- Corrections de suivi : doublon supprimé dans ARCHITECTURE.md (paragraphe sur le « J+1 » répété) ; section « État actuel » de ce carnet remise à jour (elle disait encore que la première collecte n'était pas lancée).
- À vérifier au prochain lancement de « Collecte » : la série `inflation_ipch_insee` doit atteindre 2026-10 avec 3,8. Si elle échoue, le message d'erreur de `status.json` dira si le problème est l'accès (HTTP), le format XML (attributs ou éléments listés) ou l'identifiant.

## Questions ouvertes

- GitHub Pages : actif, la page s'ouvre sur iPhone.
- Insee : idBank de la série « pouvoir d'achat du RDB par unité de consommation » (base 2020) à trouver, puis à ajouter.
- Étape 1b suivante : Data Économie, AFT, OFGL, Melodi.
- Pauvreté monétaire : résolu (15 séries sur 15 constatées par l'utilisateur au 6 novembre).
- Le texte de Perplexity contenait « [message 1/20] » : explication reçue (c'est son propre compteur), sans conséquence.
