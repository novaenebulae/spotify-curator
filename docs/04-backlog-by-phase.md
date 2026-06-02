# 04 — Backlog synthétique par phase

Tags: #backlog #roadmap #phases

## Vue globale

| Phase | Objectif | Livrables clés | Dépendances |
|---:|---|---|---|
| 0 | Socle technique | monorepo, Tauri vide, core Docker, healthcheck, SQLite, diagnostics | aucune |
| 1 | Spotify backup | OAuth PKCE, import liked/playlists, snapshots, diff, exports | phase 0 |
| 2 | Gestion bibliothèque | recherche, table, doublons, absents, dry-run actions, historique | phase 1 |
| 3 | ReccoBeats | tables features, client, normalisation, jobs, coverage, UI enrichment | phase 2 |
| 3.5 | ReccoBeats batch | `GET /v1/audio-features?ids=` (≤40), enrichissement par chunks, tests mock | phase 3 **DONE** |
| 4 | Analyse locale | AudioProvider, hybrid Deezer+YT, previews resolve, workers, Essentia low-level, merge, UI features/library | phase 3 **DONE** |
| 5 | Playlist v1 | règles simples, filtres, scoring, diversité, preview, sync dry-run | phase 3, phase 2 |
| 6 | Clustering visuel | feature profiles, matrice, UMAP, HDBSCAN, carte 2D | phase 3/4/5 |
| 7 | Analyse avancée | Essentia TF, embeddings, moods, voice/instrumental | phase 4 |
| 8 | Playlist avancée | seeds, curves, harmonic, discovery, explications | phase 5/6/7 |
| 9 | Packaging | build Windows, Docker guide, backup/restore, cleanup, docs utilisateur | toutes |

## Phase gates

### Gate phase 0

Le projet démarre avec :

- core API accessible ;
- SQLite initial ;
- Docker Compose fonctionnel ;
- Tauri/Svelte visible ;
- diagnostics Docker ;
- smoke Essentia low-level.

### Gate phase 1

Avant phase 2 :

- OAuth fonctionne ;
- tokens locaux hors Git ;
- liked tracks importés ;
- playlists importées ;
- snapshots créés ;
- diff snapshot disponible ;
- exports fonctionnels.

### Gate phase 2

Avant phase 3 :

- bibliothèque explorable ;
- filtres et pagination ;
- doublons listés ;
- absents/disparus listés ;
- actions dry-run historisées ;
- aucune action Spotify réelle non confirmée.

### Gate phase 3

Avant phase 4 :

- features ReccoBeats stockées ;
- coverage visible ;
- jobs enrichissement relançables ;
- raw payloads conservés ;
- statuts d’enrichissement exploitables.

### Gate phase 4

**Livré (2026-06)** pour le périmètre MVP local :

- segments <= 30 s ;
- aucun téléchargement complet standard ;
- Essentia low-level produit JSON ;
- parser testé ;
- merge features testé (`POST /features/merge/recompute`) ;
- cleanup audio vérifié ;
- workers profil `audio` + `job_items` ;
- previews Deezer (metadata) + stratégie hybride ;
- UI library/features (coverage, failures, last runs).

**Validation 4V (juin 2026) : GO phase 5** — voir [`backlog/phase-4-validation.md`](../backlog/phase-4-validation.md) section 4V.9 (171 pytest, workers `audio`, proxy preview stream, merge features).

### Gate phase 5

Avant phase 8 :

- règles playlist validées ;
- filtres stricts ;
- scoring explicable ;
- contraintes de diversité ;
- preview ;
- dry-run sync.

### Gate phase 6

Avant phase 8 :

- profils features ;
- UMAP persisté ;
- HDBSCAN persisté ;
- carte UI utilisable ;
- playlist depuis cluster.

### Gate phase 7

Avant phase 8 :

- embeddings persistés ;
- modèles versionnés ;
- features avancées ajoutées ;
- image TensorFlow buildable ;
- pas de modèles commités.

### Gate phase 8

Avant phase 9 :

- seed tracks ;
- courbes énergie ;
- ordering avancé ;
- explications ;
- presets avancés.

### Gate phase 9

MVP stable :

- build Windows ;
- guide installation ;
- backup/restore ;
- nettoyage cache ;
- tests finaux ;
- documentation utilisateur.

## Priorités transverses

1. sécurité des données utilisateur ;
2. fiabilité snapshots ;
3. dry-run avant modification ;
4. traçabilité des jobs ;
5. reproductibilité Docker ;
6. documentation à jour ;
7. tests de non-régression.
