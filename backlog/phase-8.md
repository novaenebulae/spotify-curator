# Phase 8 — Playlist engine avancé

Tags: #backlog #phase-8 #advanced-playlists #embeddings #clusters

## But

Améliorer musicalité, ordre et explications du moteur de playlists grâce aux features phase 6 et aux clusters phase 7.

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n'est commité.
- Aucune régression sur les phases précédentes.

## 8.1 — Seed tracks

Statut : TODO

### Sous-tâches

- Similarité embeddings.
- Similarité features.
- Même cluster.
- Seed weights.
- Exclusion seeds si demandé.

## 8.2 — Energy curves

Statut : TODO

### Sous-tâches

- Progressive.
- Warmup peak cooldown.
- Calm to intense.
- High energy start.
- Tests ordering.
- Support `energy` ReccoBeats + `energy_proxy`.

## 8.3 — Harmonic optionnel

Statut : TODO

### Sous-tâches

- Camelot.
- Compatibilité.
- Pénalité incompatibilité.
- Option désactivable.
- Fallback key/mode low-level si ReccoBeats absent.

## 8.4 — Discovery mode

Statut : TODO

### Sous-tâches

- Forgotten likes.
- Recently added.
- Rarely playlisted.
- Balance familiarity/discovery.
- Bonus clusters sous-représentés.
- Bonus genres/styles rares.

## 8.5 — Explications avancées

Statut : TODO

### Sous-tâches

- Why selected.
- Why excluded.
- Score details UI.
- Filter reasons.
- Constraint reasons.
- Ordering reasons.
- Similarity reasons.

## Critères phase

- Les playlists sont plus musicales.
- Chaque sélection est explicable.
- Les presets avancés fonctionnent.
- Les features phase 6 et les clusters phase 7 sont utilisés sans accès aux payloads raw.
