# 07 — Pipeline audio et features

Tags: #audio #yt-dlp #ffmpeg #essentia #reccobeats

## Sources

1. ReccoBeats.
2. Analyse locale segmentée.
3. Essentia low-level.
4. Essentia TensorFlow.
5. librosa.
6. all-in-one.
7. OpenL3 / Discogs EffNet.
8. Spotify metadata.
9. Tags utilisateur.

## Règles strictes

- Pas de téléchargement complet standard.
- Segment temporaire uniquement.
- Segment <= 30 secondes.
- Suppression après analyse.
- Pas de commit audio.
- Pas de stockage permanent par défaut.

## Stratégie segments

```text
A : 10–25 %
B : 45–60 %
C : 70–85 %
```

## AudioProvider

```text
AudioProvider
  resolve(track)
  get_segments(track, segment_strategy)
  cleanup(job)
```

Implémentations : `YtDlpSegmentProvider`, `CachedSegmentProvider`, `TestAudioProvider`.

## Fusion des features

Priorité générale :

1. valeur manuelle ;
2. local multi-segments ;
3. local segment unique ;
4. ReccoBeats ;
5. metadata ;
6. inconnu.
