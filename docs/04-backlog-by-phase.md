# 04 — Backlog synthétique par phase

Tags: #backlog #roadmap #phases

## Décision juin 2026

La phase 5 est terminée. L'ordre initial prévoyait :

```text
phase 6 = clustering visuel
phase 7 = analyse avancée Essentia TensorFlow
```

L'ordre est modifié pour éviter de construire une carte UMAP/HDBSCAN sur un espace de features incomplet, puis de devoir la refondre après l'arrivée des embeddings et modèles TensorFlow.

Nouvel ordre :

```text
phase 6 = pipeline d'analyse parallèle + features avancées Essentia TensorFlow
phase 7 = clustering visuel
phase 8 = playlist engine avancé
phase 9 = packaging / maintenance / polish
```

## Vue globale

| Phase | Objectif | Livrables clés | Dépendances |
|---:|---|---|---|
| 0 | Socle technique | monorepo, Tauri vide, core Docker, healthcheck, SQLite, diagnostics | aucune |
| 1 | Spotify backup | OAuth PKCE, import liked/playlists, snapshots, diff, exports | phase 0 |
| 2 | Gestion bibliothèque | recherche, table, doublons, absents, dry-run actions, historique | phase 1 |
| 3 | ReccoBeats | tables features, client, normalisation, jobs, coverage, UI enrichment | phase 2 |
| 3.5 | ReccoBeats batch | `GET /v1/audio-features?ids=` ≤40, enrichissement par chunks, tests mock | phase 3 **DONE** |
| 4 | Analyse locale low-level | AudioProvider, Deezer+YouTube, previews, workers, Essentia low-level, cleanup | phase 3 **DONE** |
| 5 | Playlist v1 | règles simples, filtres, scoring, diversité, preview, sync dry-run | phase 3/4 **DONE** |
| 6 | Analyse parallèle + Essentia TensorFlow | pipeline segment_ready → low-level/TF, modèles, embeddings, genres, moods, fallbacks avancés | phase 4/5 |
| 7 | Clustering visuel | feature profiles, matrice, UMAP, HDBSCAN, carte 2D, playlist depuis cluster | phase 6 |
| 8 | Playlist avancée | seeds, curves, harmonic, discovery, explications avancées | phase 5/6/7 |
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
- statuts d'enrichissement exploitables.

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

**Validation 4V (juin 2026) : GO phase 5** — voir [`backlog/phase-4-validation.md`](../backlog/phase-4-validation.md) section 4V.9.

### Gate phase 5

Avant phase 6 :

- règles playlist validées ;
- filtres stricts ;
- scoring explicable ;
- contraintes de diversité ;
- preview ;
- dry-run sync.

### Gate phase 6

Avant phase 7 :

- Le téléchargement de segments et les analyses low-level / TensorFlow peuvent tourner en pipeline, sans attendre la fin de tout le téléchargement.
- Les workers restent persistants.
- Aucun conteneur n'est créé/détruit par piste.
- Les segments temporaires restent `<= 30s`.
- Le cleanup audio est exécuté uniquement quand tous les consommateurs d'un segment sont terminés.
- Les jobs sont observables depuis l'UI et l'API.
- `FeatureRegistry`, `FeatureResolver` et `TrackFeatureView` exposent les nouvelles features avancées.
- Les modèles TensorFlow sont déclarés, versionnés, hashés, stockés hors Git.
- Les embeddings sont persistés avec dimension, modèle, version et hash.
- Les features suivantes sont disponibles ou explicitement marquées `model_missing` / `not_available` :
  - `genre_discogs_519`
  - `approachability`
  - `engagement`
  - `mood_aggressive_score`
  - `mood_happy_score`
  - `mood_party_score`
  - `mood_relaxed_score`
  - `mood_sad_score`
  - `electronic_profile_score`
  - `danceability_tf`
  - `valence_tf`
  - `instrumental_focus_score`
  - `acoustic_profile_score`
  - `energy_proxy`
- ReccoBeats reste prioritaire pour les features déjà fiables quand disponible.
- Les fallbacks locaux sont documentés et stockent `source`, `confidence`, `model_name`, `pipeline_version`.
- Tests backend, migrations, API, worker smoke et frontend impacté passent.

### Gate phase 7

Avant phase 8 :

- Les profils features existent (`generalist`, `mood`, `timbre`, `rhythm`, `embedding`).
- La matrice est construite via `TrackFeatureView`, pas via les payloads bruts.
- UMAP est persisté.
- HDBSCAN est persisté.
- Les outliers sont visibles.
- La carte UI supporte environ 5000 titres.
- Une sélection de cluster peut être envoyée vers le moteur de playlist phase 5.

### Gate phase 8

Avant phase 9 :

- Seed tracks.
- Similarité embeddings/features.
- Courbes d'énergie.
- Mode discovery.
- Harmonic optionnel.
- Explications avancées sélection/exclusion/ordering.
- Presets avancés exploitent les features phase 6 et les clusters phase 7.

### Gate phase 9

MVP stable :

- Build Windows.
- Guide d'installation.
- Backup/restore.
- Nettoyage cache/modèles/logs.
- Rapport système sans secrets.
- Tests finaux.
- Documentation utilisateur.

## Priorités transverses

1. sécurité des données utilisateur ;
2. fiabilité snapshots ;
3. dry-run avant modification ;
4. traçabilité des jobs ;
5. reproductibilité Docker ;
6. documentation à jour ;
7. tests de non-régression.
