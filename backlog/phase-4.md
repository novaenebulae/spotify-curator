# Phase 4 — yt-dlp + analyse locale

Tags: #backlog #phase-4 #spotify-curator

## But

Analyser des segments temporaires.

## Definition of Done phase

- Les livrables de phase sont présents.
- Les tests minimum passent.
- Les commandes de validation sont documentées.
- La documentation est à jour.
- Aucun secret, cache, modèle lourd ou fichier audio n’est commité.

---

## 4.1 — AudioProvider

Statut : TODO

### Sous-tâches

- resolve
- get_segments
- cleanup

### Critères d’acceptation

- interface testée

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.2 — Stratégie segments

Statut : TODO

### Sous-tâches

- A/B/C
- <=30s
- titres courts

### Critères d’acceptation

- tests limites

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.3 — YtDlpSegmentProvider

Statut : TODO

### Sous-tâches

- download_ranges
- noplaylist
- FFmpeg

### Critères d’acceptation

- segments uniquement

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.4 — audio_download_jobs

Statut : TODO

### Sous-tâches

- statuts
- attempts
- errors

### Critères d’acceptation

- persisté

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.5 — track_segments

Statut : TODO

### Sous-tâches

- start/end
- hash
- deleted_at

### Critères d’acceptation

- contrainte <=30

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.6 — Essentia low-level

Statut : TODO

### Sous-tâches

- service Docker
- profiles
- JSON

### Critères d’acceptation

- smoke OK

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.7 — Parser JSON

Statut : TODO

### Sous-tâches

- BPM
- key
- loudness
- MFCC

### Critères d’acceptation

- features extraites

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.8 — Merge features

Statut : TODO

### Sous-tâches

- priorités
- confidence

### Critères d’acceptation

- merge testé

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.

## 4.9 — Cleanup

Statut : TODO

### Sous-tâches

- delete
- deleted_at
- logs

### Critères d’acceptation

- pas d’audio résiduel

### Tests minimum

- Tests adaptés à la tâche.
- Commande de validation documentée.
- Pas de régression sur les tâches précédentes.
