# Phase 5 — Playlist generator v1

Tags: #backlog #phase-5 #playlist-engine #feature-registry #dry-run

## But

Générer des playlists simples à partir de règles explicites, avec scoring explicable, diversité, preview locale et synchronisation Spotify en dry-run.

La phase 5 doit être conçue pour rester compatible avec :

- phase 6 — clusters UMAP/HDBSCAN ;
- phase 7 — embeddings, moods, voice/instrumental, Essentia TensorFlow ;
- phase 8 — playlist engine avancé.

---

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n'est commité.
- Aucune régression sur les phases précédentes.
- Le moteur ne dépend pas des payloads bruts ReccoBeats / Essentia.
- Les features futures phase 7 peuvent être déclarées ou mentionnées avec warning, sans crash.
- Le dry-run sync n'écrit pas dans Spotify.

---

## 5.0 — Préparation architecture features

Statut : DONE

### Audit juin 2026 (socle phases 0–4)

- Alembic head `0007` : `audio_features`, `track_previews`, jobs audio OK.
- Merge features : source gagnante par piste (`FeatureMergeService`), pas merge champ à champ.
- Priorité resolver phase 5 : BPM/key/mode/loudness → Essentia si actif + confidence ; energy/valence/danceability → ReccoBeats ; métadonnées → `tracks` / `spotify_tracks` / `liked_tracks` / `playlist_tracks`.
- Dry-run pattern existant : `library/actions.py`, `POST /library/actions/dry-run`.
- Tables phase 5 (`playlist_rules`, `generated_*`, `sync_*`) : absentes avant migration `0008`.

### Sous-tâches

- Créer `FeatureRegistry`.
- Déclarer les features phase 5 disponibles.
- Déclarer les features phase 7 futures.
- Ajouter alias `tempo -> bpm`, `valence_inverse`, etc.
- Créer `FeatureResolver`.
- Créer `TrackFeatureView`.
- Ajouter tests features connues, inconnues, futures, manquantes, low confidence.

### Critères

- Le playlist engine consomme `TrackFeatureView`, pas les payloads bruts.
- Une feature future retourne `FEATURE_NOT_AVAILABLE_YET`.
- Une feature absente required peut exclure une piste.
- Une feature absente optional produit un warning.

---

## 5.1 — Schéma PlaylistRule

Statut : DONE

### Sous-tâches

- Pydantic schema.
- Support JSON.
- Support YAML si dépendance acceptable ; sinon YAML éditeur UI différé mais schéma JSON complet.
- Validation structurelle.
- Validation features via `FeatureRegistry`.
- Validation des ranges.
- Validation des sources.
- Endpoint `POST /playlist-rules/validate`.
- Tests schéma valide/invalide.

### Critères

- Une règle valide passe.
- Une règle invalide retourne erreurs structurées.
- Une règle avec feature future optional retourne warning.
- Une règle avec feature inconnue retourne erreur.

---

## 5.2 — CRUD minimal règles

Statut : DONE

### Sous-tâches

- Migration `playlist_rules` si absente.
- Repository.
- Service.
- Endpoints :
  - `POST /playlist-rules`
  - `GET /playlist-rules`
  - `GET /playlist-rules/{rule_id}`
  - `PUT /playlist-rules/{rule_id}`
  - `DELETE` logique ou `enabled=false`
- Versionner les règles.
- Stocker `rule_json` et éventuellement `rule_yaml`.

### Critères

- CRUD fonctionne.
- Validation exécutée avant création/update.
- Les règles désactivées ne sont pas proposées par défaut.

---

## 5.3 — Source selection

Statut : DONE

### Sous-tâches

- Liked tracks.
- Playlists incluses.
- Playlists exclues.
- Tracks incluses explicitement.
- Tracks exclues explicitement.
- Déduplication `track_id`.
- Préparer champs `clusters_include/exclude` pour phase 6 avec warning si utilisé.

### Critères

- La sélection source est déterministe.
- Les exclusions playlist fonctionnent.
- Les sources phase 6 retournent warning en phase 5.

---

## 5.4 — Filtres stricts

Statut : DONE

### Sous-tâches

- BPM.
- Energy.
- Valence.
- Danceability.
- Loudness.
- Key/mode.
- Feature confidence.
- Availability status.
- Market status.
- Exclusions artistes/albums/tags si disponible.
- Dedup ISRC.
- Feature missing policy.
- Exclusion reasons.

### Critères

- Chaque exclusion a un code.
- Les features manquantes sont gérées selon `required`.
- Les features futures ne cassent pas l'exécution.

---

## 5.5 — Scoring v1

Statut : DONE

### Sous-tâches

- Pondérations.
- Normalisation.
- Alias `valence_inverse`.
- Composants `freshness_score`, `playlist_fit_score`, `diversity_bonus` simples.
- Renormalisation des poids si composante manquante.
- `SCORE_NOT_COMPUTABLE` si aucune composante utilisable.
- `score_details_json` complet.

### Critères

- Score final `0..1`.
- Score explicable par composante.
- Poids initial et poids effectif stockés.
- Tests avec composante manquante.

---

## 5.6 — Diversité

Statut : DONE

### Sous-tâches

- Max tracks per artist.
- Max tracks per album.
- Dedup ISRC.
- Avoid same artist consecutive.
- Sélection stable.
- Random seed si ordering random.
- Préparer `cluster_diversity` phase 6 comme champ désactivé.

### Critères

- Les contraintes ne produisent pas d'ordre instable.
- Les suppressions par diversité sont expliquées.
- Les contraintes phase 6 retournent warning si activées trop tôt.

---

## 5.7 — Preview persistée

Statut : DONE

### Sous-tâches

- Migration `generated_playlists` si absente.
- Migration `generated_playlist_items` si absente.
- Service preview.
- Endpoint `POST /generated-playlists/preview`.
- Endpoints read/list previews.
- Stocker config utilisée.
- Stocker score summary.
- Stocker score details par item.
- Stocker selected reason.
- Stocker warnings.
- Export preview CSV/JSON si simple.

### Critères

- La preview ne modifie jamais Spotify.
- La preview est relisible.
- Les explications sont persistées.

---

## 5.8 — Dry-run sync

Statut : DONE

### Sous-tâches

- Migration `sync_jobs` si absente.
- Migration `sync_logs` si absente.
- Endpoint `POST /sync/dry-run`.
- Lire playlist cible Spotify si nécessaire.
- Modes : create, replace, add_only, remove_obsolete, replace_after_dry_run.
- Diff `to_add`, `to_remove`, `unchanged`.
- Warning si write scope absent.
- Aucun endpoint apply en phase 5 sans validation explicite.

### Critères

- Aucun write Spotify.
- Dry-run fonctionne sans scope write.
- Diff lisible.
- Erreurs Spotify gérées.

---

## 5.9 — UI Playlist Builder

Statut : DONE

### Sous-tâches

- Route `/playlists`.
- Navigation shell.
- Presets initiaux.
- Rule editor simple.
- YAML/JSON advanced editor.
- Validation panel.
- Preview table.
- Score details drawer/panel.
- Exclusions panel.
- Dry-run sync panel.
- Empty/loading/error/offline states.

### Critères

- L'utilisateur peut générer une preview depuis un preset.
- Les warnings features futures sont lisibles.
- Les scores sont inspectables.
- Aucune action réelle Spotify visible.

---

## 5.10 — Tests et documentation

Statut : DONE

### Sous-tâches

- Tests unitaires FeatureRegistry.
- Tests unitaires FeatureResolver.
- Tests PlaylistRule.
- Tests filters.
- Tests scoring.
- Tests diversity.
- Tests preview persistence.
- Tests sync dry-run.
- Tests API.
- Build frontend.
- Mise à jour docs.
- Revue de phase.

### Critères

- `uv run pytest -q` passe.
- `npm run check` passe.
- `npm run build` passe.
- Documentation synchronisée.

---

## Critères phase

- Une règle simple génère une preview.
- Les scores sont explicables.
- Les exclusions sont explicables.
- Dry-run sync n'écrit pas dans Spotify.
- Le moteur accepte des features futures phase 7 sans réécriture.
- Le clustering phase 6 pourra réutiliser `FeatureResolver`.
