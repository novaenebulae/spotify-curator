# 09 — Spécification UI

Tags: #ui #svelte #tauri #screens

## Principes UI

- Application desktop claire, locale, non web SaaS.
- Navigation par écrans principaux.
- États visibles : loading, empty, error, offline core, retry, progression job.
- Toute action dangereuse nécessite confirmation.
- Toute écriture Spotify nécessite dry-run préalable.
- Les vues complexes doivent fonctionner avec 5000+ tracks.

## Layout global (phase 2 UI polish)

- barre de navigation top (`.app-shell`) : Accueil, Import, Library, Settings ;
- zone contenu `.layout-main` (max-width ~1200px sur Library) ;
- tokens CSS dans `app.css` (`--color-*`, `--space-*`, `.card`, `.badge`, `.btn`, `.table-sticky`) ;
- pas de sidebar lourde en phase 2.

Composants communs :

- `AlbumCover` : lazy-load, fallback, lien Spotify optionnel ;
- `StatusBadge` : liked, unavailable, duplicate, missing, neutral.

## Écran Settings (phase 2 UI)

Sections en cartes :

1. Core API — badge statut, URL, version, Refresh ;
2. Spotify — auth, scopes, expiry ;
3. Storage — `data_dir`, `export_dir`, `cache_dir` ;
4. Docker runtime — Run checks + tableau nom / OK / message ;
5. Developer diagnostics — `<details>` replié avec JSON `diagnostics` + `runtime/config`.

États : loading, error, offline core.

## Écran 1 — Accueil (`/`)

Objectif : tableau de bord local.

Contenu implémenté :

- cartes statut (Core health, Spotify auth, tracks total, playlists total, dernier snapshot via `GET /library/summary`) ;
- actions rapides : Open Library, Import Library, Settings ;
- message « next steps » si `tracks_total === 0`.

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

UI :

- cartes de résumé ;
- boutons d’action ;
- table snapshots ;
- panneau diff ;
- **`ExportPanel`** : sélecteur cible (liked, playlists, snapshot, diff) + format (csv/json) + un bouton Export ;
- état erreurs.

## Écran 4 — Gestion bibliothèque (phase 2)

Route : `/library`.

Onglets : Titres, Doublons, Absents/disparus, Historique actions.

États obligatoires : loading, empty, error, offline core.

Limites phase 2 :

- UI in English (`/library`) ;
- sélection multi-page non conservée (page courante uniquement) ;
- pas de bouton « appliquer » Spotify ;
- dry-run obligatoire avec warnings scopes write ;
- pas de tests Vitest automatisés (validation manuelle + build).

## Écran 4 — Gestion bibliothèque (spec détaillée)

### Objectif

Explorer les titres importés, détecter doublons/absents et préparer des actions dry-run.

### Table tracks (`LibraryTable`)

Colonnes :

- sélection ;
- cover album (thumbnail) ;
- track (titre lien `external_url`, artistes, album en muted) ;
- durée ;
- liked date ;
- playlist count ;
- ISRC ;
- badges disponibilité / liked / duplicate (`StatusBadge`).

`thead` sticky ; stale-while-revalidate et `AbortController` conservés (phase 2.5).

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

### Doublons (`DuplicateGroupCard`)

- en-tête : `reason_label`, ISRC, `occurrence_count · unique_track_count · confidence` ;
- bandeau si `is_repeated_occurrence` ;
- une carte par track unique (cover, métadonnées, lien Spotify) ;
- `contexts[]` playlists si présents.

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
