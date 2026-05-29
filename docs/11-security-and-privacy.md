# 11 — Sécurité et confidentialité

Tags: #security #privacy #spotify #tokens #audio

## Données sensibles

Le projet manipule :

- bibliothèque Spotify personnelle ;
- playlists privées ;
- tokens OAuth ;
- historiques de likes ;
- exports CSV/JSON ;
- logs contenant potentiellement des IDs Spotify ;
- segments audio temporaires.

## Secrets interdits dans Git

Ne jamais commiter :

- `SPOTIFY_CLIENT_ID` si l’utilisateur préfère le garder privé ;
- tokens OAuth ;
- refresh tokens ;
- `.env` ;
- SQLite personnelle ;
- exports ;
- segments audio ;
- modèles lourds sous licence ;
- logs détaillés.

## OAuth

- Utiliser PKCE.
- Ne pas utiliser Client Secret.
- Ne jamais exposer access/refresh token à l’UI.
- Ne jamais logger les tokens.
- Stockage SQLite accepté en développement local uniquement.
- Prévoir migration future vers OS keychain ou stockage chiffré.

## Scopes minimaux

Demander seulement les scopes nécessaires à la phase.

- Phase 1/2 : read-only.
- Phase 5+ : playlist write si sync réelle.
- Restauration likes : `user-library-modify` seulement si action réelle.

## Audio

Règles :

- pas de téléchargement complet standard ;
- segments 30s maximum ;
- suppression après analyse ;
- `cache/` ignoré par Git ;
- bouton cleanup ;
- diagnostic audio résiduel.

## Logs

Les logs ne doivent pas contenir :

- tokens ;
- URL d’autorisation complète avec code ;
- chemins personnels non nécessaires ;
- payloads complets si debug désactivé.

Redaction recommandée :

```text
access_token=***
refresh_token=***
code=***
state=***
```

## Actions Spotify

Toute action write doit :

1. vérifier scope ;
2. créer dry-run ;
3. afficher diff ;
4. demander confirmation ;
5. journaliser action ;
6. gérer erreurs partielles.

## Backup/restore

Les backups peuvent contenir toute la bibliothèque. Ils doivent être :

- stockés dans `data/backups` ou chemin utilisateur ;
- non commités ;
- validés avant restore ;
- versionnés avec schéma DB.

## Rapport système

Le rapport système ne doit pas inclure :

- tokens ;
- secrets ;
- raw payloads complets ;
- chemins sensibles si non nécessaires.

Il peut inclure :

- versions ;
- services Docker ;
- présence des modèles ;
- taille cache ;
- nombre jobs failed ;
- dernier statut health.
