# Phase 4 — yt-dlp + analyse locale low-level

Tags: #backlog #phase-4 #audio #yt-dlp #essentia

## But

Analyser des segments audio temporaires pour compléter les features locales low-level.


## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.
- Aucune régression sur les phases précédentes.


## 4.1 — AudioProvider

Statut : TODO

### Sous-tâches

- Interface `AudioProvider`.
- `resolve(track)`.
- `get_segments(track, strategy)`.
- `cleanup(job)`.
- `TestAudioProvider`.

### Critères d’acceptation

- Interface testée sans yt-dlp réel.

## 4.2 — Stratégie segments

Statut : TODO

### Sous-tâches

- A 10–25 %.
- B 45–60 %.
- C 70–85 %.
- Limite 30s.
- Gestion titres courts.
- Tests limites.

### Critères d’acceptation

- Aucun segment > 30s.

## 4.3 — YtDlpSegmentProvider

Statut : TODO

### Sous-tâches

- Résolution source.
- Matching titre/artiste/durée.
- `download_ranges`.
- `noplaylist`.
- FFmpeg WAV.
- Logs.

### Critères d’acceptation

- Segments uniquement.
- Pas de playlist entière.

## 4.4 — audio_download_jobs

Statut : TODO

### Sous-tâches

- Persister jobs download.
- Statuts.
- Attempts.
- Errors.
- Rate limits.

## 4.5 — track_segments

Statut : TODO

### Sous-tâches

- Stocker start/end/duration.
- Hash fichier.
- Source hash.
- deleted_at.
- Contrainte DB <=30.

## 4.6 — Essentia low-level

Statut : TODO

### Sous-tâches

- Service Docker/profile.
- Command wrapper.
- Profiles YAML.
- Smoke test.
- JSON output.

### Critères d’acceptation

- Essentia traite WAV court.

## 4.7 — Parser JSON

Statut : TODO

### Sous-tâches

- Parser BPM.
- Parser key.
- Parser loudness.
- Parser MFCC/HPCP/spectral.
- Tests fixtures JSON.

## 4.8 — Merge features

Statut : TODO

### Sous-tâches

- Priorités sources.
- Confidence.
- Multi-segments aggregation.
- Recompute active features.

## 4.9 — Cleanup

Statut : TODO

### Sous-tâches

- Delete audio.
- deleted_at.
- Logs cleanup.
- UI nettoyage.

### Critères d’acceptation

- Pas d’audio résiduel après job normal.
