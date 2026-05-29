# 09 — Spécification UI

Tags: #ui #svelte #tauri #screens

## Principes UI

- Application desktop claire, locale, non web SaaS.
- Navigation par écrans principaux.
- États visibles : loading, empty, error, offline core, retry, progression job.
- Toute action dangereuse nécessite confirmation.
- Toute écriture Spotify nécessite dry-run préalable.
- Les vues complexes doivent fonctionner avec 5000+ tracks.

## Layout global

Éléments :

- sidebar navigation ;
- header statut core/Spotify ;
- zone contenu ;
- toast/alert erreurs ;
- panneau job progress global optionnel.

## Écran Settings (phase 1.5)

- runtime config (`GET /runtime/config`) ;
- bouton « Run Docker checks » + liste checks persistés ;
- diagnostics legacy (`GET /diagnostics`) ;
- états loading / error / offline.

## Écran 1 — Accueil

Objectif : afficher état général.

Contenu :

- statut core API ;
- statut Docker ;
- statut Spotify ;
- nombre tracks importées ;
- dernier snapshot ;
- coverage features ;
- derniers jobs ;
- raccourcis vers Import, Bibliothèque, Enrichissement.

## Écran 2 — Connexion Spotify

Fonctions :

- afficher scopes ;
- bouton connexion ;
- bouton déconnexion ;
- statut token ;
- profil utilisateur ;
- message si client id absent ;
- lien d’aide configuration.

États :

- non configuré ;
- non connecté ;
- connecté ;
- token expiré ;
- erreur callback.

## Écran 3 — Import bibliothèque

Fonctions :

- importer liked tracks ;
- importer playlists ;
- import full library ;
- créer snapshot ;
- lister snapshots ;
- comparer deux snapshots ;
- exporter liked/playlists/snapshot/diff ;
- afficher progression jobs.

UI minimale :

- cartes de résumé ;
- boutons d’action ;
- table snapshots ;
- panneau diff ;
- état erreurs.

## Écran 4 — Gestion bibliothèque

Phase 2.

### Objectif

Explorer les titres importés, détecter doublons/absents et préparer des actions dry-run.

### Table tracks

Colonnes minimales :

- sélection ;
- titre ;
- artistes ;
- album ;
- durée ;
- date ajout likes ;
- playlists ;
- ISRC ;
- disponibilité ;
- doublon ;
- actions.

### Filtres

- recherche texte ;
- artiste ;
- album ;
- ISRC ;
- liked oui/non ;
- playlist source ;
- présent dans au moins une playlist ;
- absent des playlists ;
- disponibilité ;
- statut snapshot ;
- durée min/max ;
- date ajout avant/après ;
- doublons uniquement.

### Sélection

- sélection ligne ;
- sélection page ;
- vider sélection ;
- compteur sélection ;
- actions sur sélection.

### Doublons

Vue :

- groupes de doublons ;
- raison ;
- confiance ;
- tracks du groupe ;
- bouton filtrer ces tracks dans table.

### Absents/disparus

Vue :

- résumé par statut ;
- liste tracks ;
- filtre snapshot ;
- sélection pour action dry-run.

### Actions dry-run

Actions phase 2 :

- unlike_tracks ;
- restore_liked_tracks ;
- create_backup_playlist.

Modale dry-run :

- action ;
- nombre titres ;
- exemples ;
- warnings ;
- indication scopes requis ;
- bouton confirmer dry-run ;
- pas d’application réelle par défaut.

### Historique actions

- liste actions ;
- type ;
- date ;
- affected_count ;
- dry-run ;
- status ;
- détail résultat.

## Écran 5 — Enrichissement features

Phase 3/4/7.

Fonctions :

- coverage features ;
- lancer ReccoBeats ;
- relancer failed ;
- relancer missing ;
- voir statuts ;
- comparer sources ;
- lancer analyse locale ;
- voir cleanup audio ;
- debug raw payload.

Sections :

- coverage globale ;
- coverage par champ ;
- jobs enrichissement ;
- tracks sans features ;
- erreurs récentes ;
- actions relance.

## Écran 6 — Explorateur musical

Phase 5+.

Fonctions :

- table avec features ;
- colonnes BPM, energy, valence, danceability ;
- key/Camelot ;
- tags ;
- scores ;
- ajout à playlist candidate ;
- exclusion manuelle.

## Écran 7 — Carte de similarité

Phase 6.

Fonctions :

- projection UMAP ;
- clusters HDBSCAN ;
- zoom/pan ;
- sélection points ;
- coloration par feature ;
- coloration par playlist ;
- coloration par cluster ;
- couleur par source features ;
- création playlist depuis sélection ;
- renommage cluster.

Performance :

- 5000 points minimum ;
- canvas ou SVG optimisé ;
- tooltip léger ;
- pagination non applicable mais filtrage client/serveur.

## Écran 8 — Générateur de playlists

Phase 5/8.

Fonctions :

- presets ;
- éditeur visuel règles ;
- éditeur YAML avancé ;
- validation ;
- preview ;
- score details ;
- exclusions ;
- ordering ;
- dry-run sync.

États :

- règle invalide ;
- features insuffisantes ;
- preview vide ;
- sync dry-run prête ;
- write scope absent.

## Écran 9 — Synchronisation Spotify

Phase 5/9.

Fonctions :

- choisir playlist cible ;
- créer playlist ;
- remplacer contenu ;
- ajouter seulement nouveaux ;
- retirer obsolètes ;
- afficher diff ;
- confirmer application ;
- historique sync ;
- rollback local si possible.

## Écran 10 — Paramètres

Fonctions :

- configuration Spotify ;
- statut Docker ;
- diagnostics ;
- chemins data/cache/models/logs/exports ;
- nettoyage cache ;
- backup/restore ;
- mode debug ;
- informations versions ;
- smoke tests Essentia.

## Composants communs

- `StatusBadge`
- `ErrorAlert`
- `JobProgressCard`
- `ConfirmDialog`
- `DataTable`
- `PaginationControls`
- `FilterPanel`
- `TrackListTable`
- `DryRunModal`
- `SnapshotSelector`
- `ExportButton`

## Accessibilité minimale

- boutons nommés ;
- états disabled explicites ;
- contraste suffisant ;
- navigation clavier sur tables si possible ;
- messages d’erreur lisibles.

## Tests UI

- navigation ;
- core offline ;
- auth status ;
- import job polling ;
- table filters ;
- selection ;
- confirmation dry-run ;
- coverage display ;
- playlist preview ;
- clustering map smoke.
