# 00 — Brief projet

Tags: #brief #produit #spotify #curation

## Vision

Spotify Library Curator & Playlist Engine est une application desktop locale destinée à transformer une grande bibliothèque Spotify en base musicale sauvegardée, explorable, enrichie et actionnable.

Le projet répond à trois problèmes :

1. Spotify ne fournit plus de manière stable les anciennes audio features.
2. Une bibliothèque de plusieurs milliers de titres devient difficile à trier manuellement.
3. Les titres likés ou playlists peuvent évoluer, disparaître ou devenir indisponibles sans historique local fiable.

L’application n’est pas un clone de Spotify. Elle agit comme un outil personnel de sauvegarde, audit, curation, clustering, génération de playlists et synchronisation contrôlée.

## Utilisateur cible

Utilisateur avancé possédant une grande bibliothèque Spotify et souhaitant :

- auditer ses likes ;
- retrouver des titres disparus ;
- classer des milliers de titres ;
- enrichir les morceaux avec des features ;
- générer des playlists selon des règles précises ;
- visualiser la similarité musicale ;
- garder un contrôle total avant modification Spotify.

## Fonctionnalités finales

### Sauvegarde

- OAuth Spotify PKCE.
- Import liked tracks.
- Import playlists.
- Import playlist items.
- Stockage SQLite.
- Snapshots datés.
- Diff entre snapshots.
- Exports CSV/JSON.

### Gestion bibliothèque

- Recherche globale.
- Filtres avancés.
- Table paginée.
- Détection doublons.
- Détection absents/disparus.
- Sélection multiple.
- Actions dry-run.
- Historique actions.

### Enrichissement features

- ReccoBeats pour les features simples.
- Analyse locale pour features avancées.
- Stockage multi-source.
- Confiance par feature.
- Raw payloads versionnés.
- Coverage et relance des échecs.

### Analyse audio locale

- Résolution source audio.
- Segments temporaires via yt-dlp.
- FFmpeg pour conversion/découpe.
- Essentia low-level.
- Essentia TensorFlow.
- Embeddings OpenL3 ou Discogs EffNet.
- all-in-one pour structure musicale si intégré.

### Clustering

- Profils de features.
- Normalisation/imputation.
- UMAP 2D.
- HDBSCAN.
- Carte interactive.
- Sélection par cluster.
- Playlist depuis cluster.

### Playlist engine

- Règles YAML/JSON.
- Filtres stricts.
- Scoring pondéré.
- Contraintes de diversité.
- Ordonnancement.
- Preview.
- Dry-run sync.
- Explications par track.

## Périmètre non retenu

- Application web hébergée.
- Multi-utilisateur.
- Back-office Django.
- PostgreSQL.
- Streaming audio complet.
- Stockage permanent des fichiers audio.
- Entraînement de modèles propriétaires.
- Distribution commerciale immédiate.

## Définition du MVP stable

Un MVP stable existe lorsque l’utilisateur peut :

1. lancer l’application desktop ;
2. vérifier le core Docker ;
3. se connecter à Spotify ;
4. importer ses likes/playlists ;
5. créer des snapshots ;
6. rechercher et filtrer sa bibliothèque ;
7. détecter les doublons et absents ;
8. enrichir les titres via ReccoBeats ;
9. analyser certains segments localement ;
10. générer une playlist simple ;
11. prévisualiser un dry-run Spotify ;
12. exporter/backup la base.
