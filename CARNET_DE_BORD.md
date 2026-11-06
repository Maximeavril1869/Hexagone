# Carnet de bord — Hexagone

Ce fichier retrace toutes les opérations effectuées, pour pouvoir reprendre le projet où il en est. Les entrées les plus récentes sont en bas.

## État actuel

- Étape en cours : étape 1 — tableau de bord de la France réelle.
- Dépôt : public (pour la page GitHub Pages). Passage en privé possible plus tard.
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

## Questions ouvertes

- Marchés (Brent, gaz) : voir ARCHITECTURE.md, section « Décisions en attente ».
- Activation de GitHub Pages : à faire par le propriétaire du dépôt quand la première page existera.
