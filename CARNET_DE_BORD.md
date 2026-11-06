# Carnet de bord — Hexagone

Ce fichier retrace toutes les opérations effectuées, pour pouvoir reprendre le projet où il en est. Les entrées les plus récentes sont en bas.

## État actuel

- Étape en cours : étape 1 — tableau de bord de la France réelle.
- Dépôt : public (pour la page GitHub Pages). Passage en privé possible plus tard.
- Étape 1a terminée côté code (collecteur Eurostat + BCE, tableau de bord, tâche planifiée) ; première collecte réelle pas encore lancée.
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

## Questions ouvertes

- Résultat de la première collecte réelle : à lire dans l'onglet Actions et dans `data/status.json`.
- Activation de GitHub Pages : à faire par le propriétaire du dépôt une fois la première collecte réussie.
- Le texte de Perplexity contenait « [message 1/20] » : explication reçue (c'est son propre compteur), sans conséquence.
