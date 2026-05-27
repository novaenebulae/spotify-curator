# 11 — Sécurité et contraintes légales

Tags: #security #oauth #spotify #audio

## Spotify

- OAuth PKCE.
- Scopes minimaux.
- Aucun secret dans le repo.
- Dry-run avant écriture.
- Historique sync.

## Audio

- Segments temporaires <= 30 secondes.
- Pas de téléchargement complet standard.
- Pas de stockage permanent.
- Suppression après analyse.
- Pas de fichiers audio committés.

## API locale

- `127.0.0.1` uniquement.
- Pas de port public.
