# 08 — Moteur de playlists

Tags: #playlist #rules #scoring

## Pipeline

```text
source selection → strict filters → weighted scoring → diversity constraints
→ deduplication → ordering → preview → dry-run Spotify → sync
```

## Filtres stricts

BPM, énergie, valence, confiance features, playlists sources, artistes exclus, doublons ISRC, disponibilité Spotify.

## Scoring

Score entre 0 et 1.

```text
final_score =
  0.25 * playlist_fit_score
+ 0.20 * similarity_score
+ 0.15 * energy_match_score
+ 0.15 * mood_match_score
+ 0.10 * cluster_score
+ 0.10 * user_preference_score
+ 0.05 * freshness_score
```

## Contraintes

- max titres par artiste ;
- max titres par album ;
- éviter même artiste consécutif ;
- diversité clusters ;
- équilibre vocal/instrumental ;
- éviter doublons.

## Sync Spotify

Dry-run obligatoire avant apply.
