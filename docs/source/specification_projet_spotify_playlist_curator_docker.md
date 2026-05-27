# Spécification projet — Spotify Library Curator & Playlist Engine

Tags: #projet #spotify #tauri #svelte #python #sqlite #docker #docker-compose #wsl2 #audio-analysis #music-information-retrieval #playlist-generation #yt-dlp #ffmpeg #essentia #tensorflow

## 1. Vision du projet

Le projet consiste à développer une application desktop standalone permettant de sauvegarder, explorer, enrichir, analyser et trier automatiquement une bibliothèque Spotify personnelle, en particulier les titres likés et les playlists de l’utilisateur.

L’objectif n’est pas de reproduire Spotify, mais de construire un moteur personnel de curation musicale beaucoup plus configurable, capable de générer des playlists selon des règles fines définies par l’utilisateur : BPM, tonalité, énergie, valence, genres, clusters sonores, période, artistes, albums, tags, playlists sources, similarité, exclusions, seed tracks, ambiance, niveau vocal, cohérence sonore, structure musicale, etc.

Le besoin initial est concret : l’utilisateur possède plus de 5000 titres likés sur Spotify et souhaite :

* sauvegarder localement sa bibliothèque Spotify ;
* détecter les titres absents, supprimés ou disparus entre deux synchronisations ;
* gérer les titres likés en masse ;
* enrichir les titres avec des features audio ;
* récupérer automatiquement des segments audio temporaires lorsque l’analyse locale est nécessaire ;
* analyser localement ces segments avec Essentia, librosa, modèles TensorFlow ou embeddings via Docker/WSL2 ;
* visualiser la bibliothèque musicalement ;
* générer des playlists personnalisées ;
* synchroniser ces playlists vers Spotify ;
* conserver un historique local fiable et restaurable.

L’application doit être un logiciel desktop visuel dès le MVP. Une CLI n’est pas retenue comme interface principale, même pour la première version.

---

## 2. Objectifs fonctionnels

### 2.1 Sauvegarder la bibliothèque Spotify

L’application doit permettre d’importer et de sauvegarder localement :

* les titres likés ;
* les playlists de l’utilisateur ;
* les contenus des playlists ;
* les métadonnées des titres ;
* les artistes ;
* les albums ;
* les identifiants Spotify ;
* les ISRC lorsque disponibles ;
* les dates d’ajout ;
* les snapshots de bibliothèque.

Chaque synchronisation doit produire un snapshot daté. Ce snapshot permettra de comparer l’état actuel de la bibliothèque avec les états précédents.

### 2.2 Détecter les titres absents ou disparus

Le système doit détecter :

* les titres likés présents dans un ancien snapshot mais absents du snapshot actuel ;
* les titres supprimés volontairement ;
* les titres indisponibles sur Spotify ;
* les doublons potentiels ;
* les titres remplacés par une autre version ;
* les titres présents dans les playlists mais non likés ;
* les titres likés mais non présents dans aucune playlist personnelle.

L’objectif est de répondre à la crainte de pertes silencieuses dans la bibliothèque Spotify.

### 2.3 Gérer les titres likés

Un écran spécifique de gestion de bibliothèque doit permettre de gérer les titres likés en masse.

Fonctionnalités attendues :

* recherche par titre ;
* recherche par artiste ;
* recherche par album ;
* recherche par ISRC ;
* filtre par date d’ajout ;
* filtre par durée ;
* filtre par genre ;
* filtre par playlist d’origine ;
* filtre par statut d’analyse ;
* filtre par présence ou absence dans Spotify ;
* filtre par doublons ;
* filtre par score de confiance features ;
* suppression de titres likés selon critères ;
* restauration de titres likés depuis un snapshot ;
* ajout de titres à une playlist de sauvegarde ;
* export CSV/JSON d’une sélection ;
* actions groupées avec confirmation ;
* mode dry-run avant toute modification Spotify.

Exemples d’actions :

* supprimer tous les titres likés d’un artiste complet ;
* supprimer tous les titres d’un album ;
* supprimer les titres correspondant à une recherche textuelle ;
* créer une playlist de secours avec tous les titres disparus ;
* restaurer tous les titres présents dans le snapshot N mais absents aujourd’hui ;
* identifier les titres likés qui ne sont présents dans aucune playlist.

### 2.4 Enrichir les titres avec des features audio

L’application doit pouvoir récupérer ou calculer des features audio à partir de plusieurs sources.

Sources prévues :

1. ReccoBeats API ;
2. segments audio temporaires récupérés avec yt-dlp ;
3. conversion et découpe via FFmpeg ;
4. analyse locale avec Essentia ;
5. analyse complémentaire avec librosa ;
6. modèles Essentia TensorFlow ;
7. all-in-one Music Structure Analyzer ;
8. embeddings OpenL3 ou Discogs EffNet ;
9. métadonnées Spotify ;
10. métadonnées externes éventuelles ;
11. tags utilisateur.

ReccoBeats fournit certaines features proches des anciennes audio features Spotify :

* acousticness ;
* danceability ;
* energy ;
* instrumentalness ;
* key ;
* liveness ;
* loudness ;
* mode ;
* speechiness ;
* tempo ;
* valence.

Ces valeurs doivent être utilisées lorsqu’elles sont disponibles. Cependant, ReccoBeats ne fournit pas toutes les informations nécessaires pour le projet. Dans la plupart des cas, une analyse locale complémentaire sera nécessaire, en particulier pour :

* structure du morceau ;
* intro ;
* outro ;
* couplet ;
* refrain ;
* bridge ;
* beats ;
* downbeats ;
* stabilité du tempo ;
* embeddings audio ;
* similarité sonore ;
* clusters ;
* analyse de timbre ;
* densité vocale ;
* profils d’ambiance ;
* caractéristiques spectrales ;
* scores dérivés généralistes.

Lorsque ReccoBeats ne trouve pas un titre ou ne fournit pas les valeurs nécessaires, le système doit récupérer un ou plusieurs segments audio temporaires avec yt-dlp, puis lancer l’analyse locale. Il ne faut pas télécharger le morceau complet : seuls des segments courts doivent être récupérés.

### 2.5 Générer des playlists personnalisées

L’application doit permettre de générer des playlists selon une configuration utilisateur détaillée.

Critères possibles :

* BPM minimum / maximum ;
* tonalité ;
* mode majeur / mineur ;
* Camelot key ;
* energy ;
* danceability ;
* valence ;
* acousticness ;
* instrumentalness ;
* speechiness ;
* liveness ;
* loudness ;
* genre ;
* artiste ;
* album ;
* année de sortie ;
* date d’ajout ;
* playlists sources ;
* exclusions ;
* tags utilisateur ;
* clusters UMAP/HDBSCAN ;
* proximité à des seed tracks ;
* compatibilité harmonique ;
* similarité d’embeddings ;
* scores dérivés généralistes.

Le moteur doit supporter :

* filtres stricts ;
* scoring pondéré ;
* contraintes de diversité ;
* limites par artiste ;
* exclusion de titres déjà présents dans certaines playlists ;
* génération par seed tracks ;
* génération par cluster ;
* génération par sélection visuelle sur carte 2D ;
* ordering BPM ;
* ordering harmonique ;
* courbe d’énergie ;
* mode découverte ;
* mode ambiance ;
* mode focus ;
* mode vocal/instrumental ;
* mode haute énergie ;
* mode calme ;
* mode nettoyage de bibliothèque ;
* mode mix/DJ optionnel, sans être l’axe central du projet.

### 2.6 Synchroniser vers Spotify

L’application doit pouvoir :

* créer une playlist Spotify ;
* mettre à jour une playlist existante ;
* remplacer le contenu d’une playlist ;
* ajouter uniquement les nouveaux titres ;
* supprimer les titres sortis du résultat ;
* effectuer un dry-run ;
* afficher un diff avant synchronisation ;
* conserver un historique de synchronisation ;
* rollback vers un snapshot précédent lorsque possible.

---

## 3. Périmètre retenu

### 3.1 Inclus dans le MVP

Le MVP inclut :

* application desktop visuelle ;
* environnement Windows + Docker Desktop + WSL2 ;
* Docker Compose pour le core technique ;
* connexion Spotify OAuth ;
* import des titres likés ;
* import des playlists ;
* base SQLite locale ;
* snapshots datés ;
* écran de gestion bibliothèque ;
* récupération de features ReccoBeats ;
* récupération de segments audio temporaires avec yt-dlp lorsque l’analyse locale est nécessaire ;
* découpe, extraction et conversion audio avec FFmpeg ;
* contrainte stricte : chaque segment audio doit durer 30 secondes maximum ;
* analyse locale avec Essentia/librosa via Docker ;
* analyse avancée avec Essentia TensorFlow via image Docker custom ;
* cache de features ;
* explorateur musical filtrable ;
* UMAP/HDBSCAN ;
* générateur de playlists configurable ;
* preview de playlist ;
* synchronisation Spotify avec dry-run.

### 3.2 Exclu du MVP

Le MVP n’inclut pas :

* application web hébergée ;
* multi-utilisateur ;
* back-office Django ;
* authentification locale complexe ;
* serveur distant ;
* stockage permanent de fichiers audio ;
* entraînement de modèles ML propriétaires ;
* distribution commerciale ;
* installation native Windows d’Essentia ;
* téléchargement complet systématique des morceaux ;
* dépendance à un service tiers de scraping musical.

---

## 4. Stack technique validée

### 4.1 Application desktop

* Tauri ;
* Svelte / SvelteKit en mode SPA/static ;
* TypeScript ;
* composants UI légers ;
* graphiques interactifs pour UMAP/clusters ;
* communication avec le core Python via sidecar ou protocole local.

Tauri est retenu pour produire une application desktop légère, moderne et distribuable. Svelte est retenu pour limiter la complexité frontend par rapport à Angular ou React.

### 4.2 Core applicatif

* Python exécuté dans Docker ;
* uv pour la gestion d’environnement ;
* FastAPI ou API locale équivalente pour exposer le core sur `127.0.0.1` ;
* SQLAlchemy ou SQLModel ;
* Pydantic pour la validation des configurations ;
* httpx ou spotipy pour l’API Spotify ;
* requests/httpx pour ReccoBeats ;
* yt-dlp pour la récupération de segments audio temporaires ;
* FFmpeg pour découpe, extraction, conversion et normalisation audio ;
* pandas/numpy pour les traitements ;
* scikit-learn pour normalisation, scoring, préparation clustering ;
* UMAP pour réduction dimensionnelle ;
* HDBSCAN pour clustering ;
* rapidfuzz pour matching textuel ;
* tenacity ou backoff pour retries avec exponential backoff ;
* networkx optionnel pour graphes artistes/titres/playlists.

### 4.3 Base locale

* SQLite ;
* migrations locales via Alembic si SQLAlchemy est retenu ;
* stockage dans un dossier applicatif local ;
* export JSON/CSV ;
* backup de base possible.

SQLite est suffisant pour une bibliothèque de 5000 à 100000 titres. L’application étant personnelle et locale, PostgreSQL serait inutilement lourd.

### 4.4 Analyse audio

* yt-dlp ;
* FFmpeg ;
* Essentia ;
* essentia_streaming_extractor_music ;
* librosa en complément ;
* all-in-one Music Structure Analyzer ;
* OpenL3 ou Discogs EffNet pour embeddings ;
* modèles TensorFlow Essentia.

Essentia constitue la brique principale pour l’analyse musicale locale. Sous Windows, Essentia doit être exécuté via Docker/WSL2, pas installé nativement. librosa peut compléter pour des expérimentations ou des features spécifiques. yt-dlp et FFmpeg constituent la brique d’obtention et de préparation des segments audio temporaires.

### 4.5 Clustering et visualisation

* UMAP pour projection 2D ;
* HDBSCAN pour clusters naturels ;
* scikit-learn pour preprocessing ;
* Svelte pour affichage interactif ;
* éventuellement Canvas/WebGL si la carte devient lourde.


### 4.6 Environnement Windows et Docker

L’environnement cible de développement est Windows avec Docker Desktop et backend WSL2.

Contraintes validées :

* Essentia ne doit pas être installé ni compilé directement sur Windows ;
* les dépendances audio lourdes doivent tourner dans des conteneurs Linux ;
* le core Python applicatif doit être dockerisé pour garantir la reproductibilité ;
* Tauri reste exécuté côté Windows pour l’interface desktop ;
* Docker Compose orchestre les services techniques ;
* les données persistantes sont stockées dans des volumes montés depuis le projet.

Outils système requis côté Windows :

* Windows 10/11 ;
* Docker Desktop ;
* backend WSL2 activé ;
* PowerShell ;
* Node.js pour le développement frontend/Tauri ;
* Rust toolchain pour Tauri ;
* Git ;
* navigateur pour OAuth Spotify.

Outils fournis par Docker :

* Python ;
* uv ;
* yt-dlp ;
* FFmpeg ;
* Essentia ;
* essentia-tensorflow ;
* dépendances de clustering ;
* dépendances de tests.

---

## 5. Architecture générale validée

### 5.1 Décision d’architecture

L’architecture retenue est hybride :

```text
Windows
  └── Application desktop Tauri / Svelte
          ↓ HTTP localhost / Tauri commands
Docker Desktop avec backend WSL2
  └── Docker Compose
          ├── core-api Python
          ├── audio-downloader : yt-dlp + FFmpeg
          ├── essentia-lowlevel : Essentia CLI
          ├── essentia-tensorflow : Essentia + modèles TensorFlow
          ├── jobs / workers
          └── volumes SQLite + cache temporaire
```

L’application desktop reste exécutée sur Windows afin de conserver une vraie expérience desktop : WebView2, fenêtres natives, OAuth Spotify, accès aux paramètres utilisateur, file dialogs et packaging Windows.

Le cœur technique est exécuté dans Docker afin d’obtenir un environnement Linux reproductible, compatible avec Essentia, yt-dlp, FFmpeg, les modèles TensorFlow et les dépendances lourdes de music information retrieval.

### 5.2 Ce qui tourne hors Docker

Hors Docker :

* application Tauri ;
* frontend Svelte / SvelteKit statique ;
* WebView2 Windows ;
* éventuel lanceur de services Docker ;
* configuration utilisateur minimale ;
* ouverture de l’interface desktop ;
* dialogue OAuth Spotify côté application.

Raison : Tauri est destiné à produire une application desktop native. Le conteneuriser compliquerait inutilement l’interface graphique, le packaging Windows, l’intégration WebView2 et les interactions système.

### 5.3 Ce qui tourne dans Docker

Dans Docker :

* core Python ;
* API locale du core ;
* jobs longs ;
* accès Spotify API ;
* accès ReccoBeats ;
* récupération de segments avec yt-dlp ;
* découpe/conversion/normalisation avec FFmpeg ;
* analyse Essentia niveau 1 ;
* analyse Essentia TensorFlow niveau 2 ;
* all-in-one Music Structure Analyzer si intégré ;
* génération d’embeddings ;
* UMAP/HDBSCAN ;
* migrations SQLite ;
* tests d’intégration audio.

### 5.4 Communication Tauri ↔ Docker

Choix recommandé : API locale HTTP exposée uniquement sur `127.0.0.1`.

```text
Tauri Desktop App
        ↓
Svelte UI
        ↓
Tauri commands / fetch localhost
        ↓
http://127.0.0.1:8765
        ↓
core-api Python dans Docker
        ↓
SQLite + workers + services métier
```

Le core peut être implémenté avec FastAPI ou une API Python équivalente. L’API ne doit pas être exposée sur le réseau local : uniquement `127.0.0.1`.

Avantages :

* découplage clair entre UI et core ;
* compatibilité Windows ;
* meilleure observabilité ;
* possibilité de tester le core sans lancer l’interface ;
* intégration plus simple avec Docker Compose ;
* jobs longs faciles à suivre par polling ou événements.

Alternative acceptable pour plus tard : Tauri peut lancer/arrêter Docker Compose ou vérifier l’état des services via des commandes système encadrées.

### 5.5 Services Docker Compose cibles

Services recommandés :

```text
docker-compose.yml
  core-api
  audio-downloader
  essentia-lowlevel
  essentia-tensorflow
  clustering-worker
  job-worker
```

Rôle des services :

| Service | Rôle |
|---|---|
| `core-api` | API locale, orchestration, SQLite, règles métier |
| `audio-downloader` | yt-dlp, résolution des segments, FFmpeg |
| `essentia-lowlevel` | Essentia CLI, `essentia_streaming_extractor_music` |
| `essentia-tensorflow` | modèles TensorFlow Essentia, embeddings, moods, styles |
| `clustering-worker` | UMAP, HDBSCAN, normalisation des feature sets |
| `job-worker` | exécution des jobs longs, retries, cleanup |

Pour le MVP, certains services peuvent être fusionnés afin de réduire la complexité. Par exemple, `core-api` et `job-worker` peuvent partager la même image Python. En revanche, il est préférable de garder les workers Essentia séparés car leurs dépendances sont plus lourdes.

### 5.6 Volumes et stockage local

Volumes recommandés :

```text
data/
  spotify_curator.sqlite
  backups/

cache/
  audio_segments/
  essentia_lowlevel_json/
  essentia_tensorflow_json/
  clustering/

models/
  essentia/
  tensorflow/
  openl3/
  discogs_effnet/

logs/
  core/
  jobs/
  docker/
```

Règles :

* SQLite est stocké dans un volume local persistant ;
* les segments audio sont temporaires ;
* les JSON de features peuvent être conservés comme cache technique ;
* les modèles TensorFlow peuvent être persistés dans `models/` pour éviter des téléchargements répétés ;
* les logs doivent permettre de diagnostiquer les erreurs de jobs ;
* les chemins Windows ne doivent pas être codés en dur dans le core.

### 5.7 Images Docker Essentia

Deux niveaux d’analyse sont nécessaires.

#### Niveau 1 — Essentia low-level

Image recommandée :

```text
ghcr.io/mtg/essentia:bullseye-v2.1_beta5
```

Usage :

* extraction low-level ;
* rhythm ;
* tonal ;
* BPM ;
* loudness ;
* key ;
* MFCC ;
* HPCP ;
* spectral centroid / rolloff / contrast ;
* JSON standard via `essentia_streaming_extractor_music`.

Cette image est utilisée comme runtime Linux reproductible pour contourner l’absence de build Essentia fiable sous Windows.

#### Niveau 2 — Essentia TensorFlow

Image projet custom recommandée :

```text
spotify-curator-essentia-tensorflow:<version>
```

Base possible :

```dockerfile
FROM python:3.11-slim-bookworm
```

Dépendances principales :

* FFmpeg ;
* libsndfile ;
* libgomp ;
* numpy ;
* essentia-tensorflow ;
* modèles TensorFlow Essentia ;
* modèles Discogs EffNet ;
* modèles de mood/style/voice selon disponibilité.

Usage :

* embeddings audio ;
* similarité sonore ;
* classification style/genre approximative ;
* mood ;
* arousal / valence ;
* voice / instrumental ;
* electronic / acoustic ;
* timbre ;
* features avancées non fournies par ReccoBeats.

### 5.8 Exemple de Docker Compose cible

```yaml
services:
  core-api:
    build:
      context: .
      dockerfile: docker/core/Dockerfile
    ports:
      - "127.0.0.1:8765:8765"
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache
      - ./models:/app/models
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=sqlite:////app/data/spotify_curator.sqlite
      - CACHE_DIR=/app/cache
      - MODELS_DIR=/app/models

  audio-downloader:
    build:
      context: .
      dockerfile: docker/audio-downloader/Dockerfile
    volumes:
      - ./cache/audio_segments:/work/audio_segments
      - ./logs:/work/logs

  essentia-lowlevel:
    image: ghcr.io/mtg/essentia:bullseye-v2.1_beta5
    volumes:
      - ./cache/audio_segments:/input
      - ./cache/essentia_lowlevel_json:/output
      - ./profiles:/profiles

  essentia-tensorflow:
    build:
      context: docker/essentia-tensorflow-worker
      dockerfile: Dockerfile
    volumes:
      - ./cache/audio_segments:/input
      - ./cache/essentia_tensorflow_json:/output
      - ./models:/models
      - ./logs:/logs
```

### 5.9 Structure de dépôt recommandée

```text
spotify-curator/
  app/
    frontend/
    src-tauri/

  core/
    spotify/
    library/
    sync/
    reccobeats/
    audio_sources/
    audio_download/
    audio_segments/
    audio_analysis/
    features/
    clustering/
    playlist_engine/
    rules/
    database/
    jobs/
    settings/

  docker/
    core/
      Dockerfile
    audio-downloader/
      Dockerfile
    essentia-tensorflow-worker/
      Dockerfile
      analyze_effnet.py
    clustering-worker/
      Dockerfile

  profiles/
    essentia_lowlevel_basic.yaml
    essentia_lowlevel_extended.yaml

  models/
    .gitkeep

  data/
    .gitkeep

  cache/
    .gitkeep

  logs/
    .gitkeep

  docker-compose.yml
  docker-compose.dev.yml
  docker-compose.test.yml
  README.md
```

### 5.10 Gestion des jobs longs

Les jobs longs ne doivent pas bloquer l’interface.

Jobs concernés :

* import Spotify ;
* enrichissement ReccoBeats ;
* résolution de sources audio ;
* téléchargement de segments ;
* analyse Essentia low-level ;
* analyse Essentia TensorFlow ;
* génération d’embeddings ;
* clustering ;
* génération de playlists ;
* synchronisation Spotify.

L’UI doit interroger régulièrement le core pour afficher :

* statut ;
* progression ;
* étape courante ;
* nombre d’éléments traités ;
* erreurs ;
* jobs relançables ;
* jobs rate-limited ;
* bouton d’annulation ;
* bouton de retry.

---

## 6. Pipeline de données

### 6.1 Import Spotify

Étapes :

1. connexion OAuth ;
2. récupération du profil utilisateur ;
3. récupération des titres likés ;
4. récupération des playlists ;
5. récupération des items de playlists ;
6. normalisation des artistes/albums/titres ;
7. sauvegarde SQLite ;
8. création d’un snapshot ;
9. comparaison avec le snapshot précédent ;
10. génération d’un rapport de diff.

Données minimales à stocker pour un track Spotify :

* spotify_track_id ;
* spotify_uri ;
* href ;
* title ;
* duration_ms ;
* explicit ;
* popularity si disponible ;
* preview_url si disponible ;
* external_url ;
* isrc ;
* album_id ;
* album_name ;
* album_release_date ;
* artist_ids ;
* artist_names ;
* added_at ;
* source context.

### 6.2 Snapshot local

Chaque snapshot doit stocker :

* identifiant du snapshot ;
* date de création ;
* type : liked_tracks, playlists, full_library ;
* nombre de titres ;
* nombre de playlists ;
* hash global éventuel ;
* diff avec le snapshot précédent ;
* statut de synchronisation.

Le snapshot doit permettre :

* comparaison historique ;
* restauration ;
* audit ;
* export ;
* détection de suppressions.

### 6.3 Enrichissement ReccoBeats

Étapes :

1. sélectionner les tracks sans features ou avec features expirées ;
2. requêter ReccoBeats par identifiant disponible ;
3. appliquer retry/backoff si la requête échoue temporairement ou si un rate limit est rencontré ;
4. stocker la réponse brute ;
5. normaliser les champs ;
6. calculer la confiance ;
7. marquer les tracks trouvées/non trouvées ;
8. identifier les features manquantes ou insuffisantes ;
9. planifier l’analyse locale pour les titres nécessitant des features supplémentaires ;
10. relancer uniquement les échecs si nécessaire.

Features ReccoBeats à stocker :

* acousticness ;
* danceability ;
* energy ;
* instrumentalness ;
* key ;
* liveness ;
* loudness ;
* mode ;
* speechiness ;
* tempo ;
* valence.

### 6.4 Analyse locale complémentaire

L’analyse locale doit être utilisée :

* si ReccoBeats ne trouve pas le titre ;
* si certaines features sont manquantes ;
* si les features nécessaires au clustering ne sont pas couvertes ;
* si l’on veut obtenir des embeddings ;
* si l’on veut calculer la structure musicale ;
* si l’on veut mesurer la stabilité temporelle d’un titre ;
* si l’on veut produire des scores dérivés plus robustes.

Pipeline :

```text
Track Spotify
        ↓
Métadonnées : titre / artistes / album / ISRC / durée
        ↓
Résolution d’une URL vidéo ou audio exploitable
        ↓
yt-dlp : téléchargement direct d’un ou plusieurs segments temporaires
        ↓
FFmpeg : extraction/conversion PCM ou WAV
        ↓
Worker Docker essentia-lowlevel
        ↓
Essentia streaming_extractor_music
        ↓
Descripteurs bas niveau
        ↓
Worker Docker essentia-tensorflow
        ↓
Modèles TensorFlow Essentia
        ↓
all-in-one structure analyzer si nécessaire
        ↓
Embeddings OpenL3 ou Discogs EffNet
        ↓
Normalisation features
        ↓
Fusion avec ReccoBeats selon confiance
        ↓
Stockage SQLite
        ↓
Suppression des fichiers audio temporaires
```

Le système ne doit pas conserver de fichier audio permanent par défaut. Les fichiers temporaires doivent être supprimés après extraction des features.

### 6.5 Récupération de segments avec yt-dlp

Le téléchargement audio doit se faire par segments, jamais par téléchargement complet du morceau lorsque l’objectif est l’analyse de features.

Contraintes obligatoires :

* durée maximale d’un segment : 30 secondes ;
* un segment doit être identifié par `track_id`, `start_seconds`, `end_seconds`, `source_url` et `analysis_job_id` ;
* un segment doit être stocké temporairement ;
* le fichier segmenté doit être supprimé après analyse ;
* les erreurs doivent être stockées dans la base avec un statut relançable ;
* le système doit éviter de télécharger plusieurs fois le même segment si les features sont déjà en cache.

Exemple de logique Python :

```python
from pathlib import Path

import yt_dlp
from yt_dlp.utils import download_range_func


MAX_SEGMENT_SECONDS = 30.0


def download_audio_segment(
    url: str,
    start: float,
    end: float,
    output_dir: str = "segments",
    filename: str = "segment",
    audio_format: str = "wav",
) -> Path:
    """
    Télécharge un segment audio depuis une URL compatible yt-dlp.

    start et end sont en secondes.
    Le segment ne doit jamais dépasser 30 secondes.
    Exemple : start=90, end=115.5.
    """

    if start < 0:
        raise ValueError("start doit être supérieur ou égal à 0.")

    if end <= start:
        raise ValueError("end doit être supérieur à start.")

    if (end - start) > MAX_SEGMENT_SECONDS:
        raise ValueError("Un segment audio ne doit pas dépasser 30 secondes.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_path / f"{filename}.%(ext)s"),
        "download_ranges": download_range_func(None, [(start, end)]),
        "force_keyframes_at_cuts": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        ],
        "noplaylist": True,
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_path / f"{filename}.{audio_format}"
```

### 6.6 Analyse par segments

L’analyse par segments est utile afin d’éviter les biais d’une preview unique.

Stratégie proposée :

* segment A : environ 10–25 % de la durée ;
* segment B : environ 45–60 % de la durée ;
* segment C : environ 70–85 % de la durée.

Chaque segment doit durer 30 secondes maximum. Pour des morceaux courts, le moteur peut réduire automatiquement la durée des segments ou n’en utiliser qu’un seul.

Éviter :

* les premières secondes ;
* les silences ;
* les intros trop longues ;
* les dernières secondes ;
* les fade-outs ;
* les passages non représentatifs lorsque détectables.

Agrégation :

* tempo : médiane ;
* loudness : moyenne ou médiane ;
* key : vote pondéré par confiance ;
* energy : moyenne pondérée ou percentile 75 ;
* danceability : moyenne pondérée ;
* valence : moyenne ;
* densité vocale : moyenne ou percentile selon usage ;
* embeddings : moyenne, pooling ou centroïde ;
* structure : analyse dédiée si nécessaire.

### 6.7 Fusion des features ReccoBeats et locales

Les features doivent être fusionnées avec traçabilité.

Principe :

```text
Pour chaque feature :
  1. vérifier si une valeur utilisateur existe ;
  2. vérifier si ReccoBeats fournit une valeur fiable ;
  3. vérifier si l’analyse locale fournit une valeur fiable ;
  4. comparer les sources si plusieurs valeurs existent ;
  5. choisir la valeur active selon la priorité configurée ;
  6. conserver toutes les valeurs sources ;
  7. stocker la valeur active et sa confiance.
```

Exemples :

* tempo : la valeur locale peut être prioritaire si la confiance Essentia/all-in-one est élevée ;
* key : comparer ReccoBeats, Essentia et éventuellement une méthode dédiée ;
* danceability : ReccoBeats peut rester prioritaire si la valeur locale est expérimentale ;
* embeddings : source locale obligatoire ;
* structure : source locale obligatoire ;
* loudness : local peut fournir une mesure plus contrôlée si les segments sont normalisés.


### 6.8 Pipeline Docker d’analyse audio

Le pipeline d’analyse doit être orchestré par le core, mais exécuté par des workers spécialisés.

```text
core-api
  ↓ crée un job
job-worker
  ↓ demande un segment
audio-downloader
  ↓ écrit WAV temporaire ≤ 30 s
essentia-lowlevel
  ↓ écrit JSON low-level
essentia-tensorflow
  ↓ écrit JSON embeddings / modèles avancés
core-api
  ↓ parse et fusionne
SQLite
```

Chaque worker doit être idempotent : si le fichier de sortie existe déjà et correspond à la version de pipeline attendue, le job peut être marqué comme déjà traité.

### 6.9 Deux niveaux Essentia

Niveau 1 — Essentia low-level :

* BPM ;
* beats ;
* tonalité ;
* mode ;
* loudness ;
* MFCC ;
* HPCP ;
* spectral centroid ;
* spectral rolloff ;
* spectral contrast ;
* dynamic complexity ;
* descripteurs rythmiques et tonals.

Niveau 2 — Essentia TensorFlow :

* embeddings Discogs EffNet ;
* embeddings utiles à la similarité sonore ;
* prédictions style/genre lorsque disponibles ;
* mood ;
* arousal / valence ;
* voice / instrumental ;
* electronic / acoustic ;
* timbre ;
* descripteurs avancés nécessaires au clustering généraliste.

Ces deux niveaux doivent être versionnés séparément dans les tables de features afin de pouvoir recalculer l’un sans invalider l’autre.

---

## 7. Scores dérivés généralistes

### 7.1 Principe

Les scores dérivés ne doivent pas être uniquement orientés DJ ou musique électronique. La bibliothèque peut contenir des styles très variés : électronique, rock, pop, ambient, rap, expérimental, musique vocale, musique instrumentale, morceaux calmes, morceaux agressifs, morceaux lents, titres acoustiques, etc.

Le moteur doit donc fournir des scores plus généraux, utilisables pour différents genres et différents usages d’écoute.

### 7.2 Scores proposés

Scores généralistes :

* energy_profile_score ;
* calm_score ;
* intensity_score ;
* mood_positive_score ;
* mood_dark_score ;
* mood_melancholic_score ;
* focus_score ;
* background_score ;
* vocal_presence_score ;
* instrumental_focus_score ;
* acoustic_profile_score ;
* electronic_profile_score ;
* rhythmic_stability_score ;
* tempo_stability_score ;
* groove_score ;
* structure_clarity_score ;
* similarity_score ;
* discovery_score ;
* freshness_score ;
* user_affinity_score ;
* playlist_fit_score.

Scores optionnels pour usages de mix ou DJ :

* mixability_score ;
* harmonic_compatibility_score ;
* intro_outro_usability_score ;
* transition_smoothness_score ;
* peak_energy_score.

Ces scores optionnels ne doivent pas dominer le modèle global. Ils doivent être activables seulement dans des presets adaptés.

### 7.3 Exemple de score généraliste

Exemple de score `playlist_fit_score` :

```text
playlist_fit_score =
  0.25 * similarity_to_seed
+ 0.20 * target_energy_match
+ 0.15 * mood_match
+ 0.15 * genre_or_cluster_match
+ 0.10 * user_affinity_score
+ 0.10 * diversity_bonus
+ 0.05 * feature_confidence
```

Exemple de score `focus_score` :

```text
focus_score =
  0.25 * instrumental_focus_score
+ 0.20 * low_vocal_presence
+ 0.20 * moderate_energy_match
+ 0.15 * rhythmic_stability
+ 0.10 * low_aggressiveness
+ 0.10 * low_loudness_variance
```

Exemple de score `intensity_score` :

```text
intensity_score =
  0.30 * energy
+ 0.20 * loudness_normalized
+ 0.15 * spectral_density
+ 0.15 * arousal
+ 0.10 * tempo_activity
+ 0.10 * dynamic_profile
```

---

## 8. Modèle de données SQLite

### 8.1 Tables principales

```text
tracks
artists
albums
track_artists
spotify_tracks
spotify_albums
spotify_artists
liked_tracks
liked_track_snapshots
playlists
playlist_snapshots
playlist_tracks
external_ids
feature_sources
audio_features
audio_feature_raw_payloads
audio_analysis_jobs
audio_download_jobs
track_segments
track_embeddings
clusters
cluster_memberships
user_tags
track_user_tags
playlist_rules
generated_playlists
generated_playlist_items
sync_jobs
sync_logs
library_actions
settings
```

### 8.2 Table tracks

Champs :

* id ;
* canonical_title ;
* normalized_title ;
* duration_ms ;
* explicit ;
* created_at ;
* updated_at.

### 8.3 Table spotify_tracks

Champs :

* id ;
* track_id ;
* spotify_track_id ;
* spotify_uri ;
* href ;
* external_url ;
* popularity ;
* is_playable ;
* market_status ;
* raw_json ;
* created_at ;
* updated_at.

### 8.4 Table external_ids

Champs :

* id ;
* track_id ;
* source ;
* external_type ;
* external_value ;
* confidence ;
* created_at.

Exemples :

* source = spotify, external_type = isrc ;
* source = reccobeats, external_type = reccobeats_id ;
* source = musicbrainz, external_type = recording_id ;
* source = youtube, external_type = video_id.

### 8.5 Table audio_features

Champs :

* id ;
* track_id ;
* source ;
* source_version ;
* confidence ;
* acousticness ;
* danceability ;
* energy ;
* instrumentalness ;
* key ;
* key_confidence ;
* camelot_key ;
* liveness ;
* loudness ;
* mode ;
* speechiness ;
* tempo ;
* tempo_confidence ;
* valence ;
* spectral_centroid ;
* spectral_rolloff ;
* spectral_contrast ;
* mfcc_summary_json ;
* chroma_summary_json ;
* hpcp_summary_json ;
* onset_rate ;
* dynamic_range ;
* integrated_loudness ;
* vocal_presence ;
* electronic_acoustic_score ;
* arousal ;
* mood_happy ;
* mood_sad ;
* mood_aggressive ;
* mood_relaxed ;
* mood_party ;
* energy_profile_score ;
* calm_score ;
* intensity_score ;
* focus_score ;
* background_score ;
* playlist_fit_score ;
* discovery_score ;
* created_at ;
* updated_at.

### 8.6 Table feature_sources

Champs :

* id ;
* name ;
* type ;
* priority ;
* enabled ;
* requires_audio ;
* requires_api_key ;
* created_at.

Exemples :

* reccobeats ;
* local_essentia ;
* local_librosa ;
* local_allinone ;
* openl3 ;
* discogs_effnet ;
* manual ;
* inferred_metadata.

### 8.7 Table audio_download_jobs

Cette table trace les récupérations de segments audio temporaires.

Champs :

* id ;
* track_id ;
* provider ;
* source_url ;
* status ;
* attempt_count ;
* max_attempts ;
* rate_limited ;
* last_error ;
* next_retry_at ;
* created_at ;
* started_at ;
* finished_at.

Statuts possibles :

* pending ;
* running ;
* success ;
* failed ;
* rate_limited ;
* skipped ;
* cancelled.

### 8.8 Table track_segments

Champs :

* id ;
* track_id ;
* analysis_job_id ;
* download_job_id ;
* start_seconds ;
* end_seconds ;
* duration_seconds ;
* segment_type ;
* source ;
* source_url_hash ;
* temporary_path ;
* features_json ;
* confidence ;
* created_at ;
* deleted_at.

Règles :

* `duration_seconds` doit être inférieur ou égal à 30 ;
* `temporary_path` ne doit pas être considéré comme stockage permanent ;
* `deleted_at` doit être renseigné après cleanup si le fichier a bien été supprimé ;
* `features_json` peut conserver les résultats d’analyse du segment même après suppression du fichier.

### 8.9 Table audio_analysis_jobs

Cette table trace les analyses locales exécutées dans Docker.

Champs :

* id ;
* track_id ;
* segment_id ;
* analysis_level ;
* docker_service ;
* image_name ;
* image_tag ;
* pipeline_version ;
* input_path ;
* output_path ;
* status ;
* attempt_count ;
* last_error ;
* started_at ;
* finished_at ;
* created_at.

Valeurs possibles pour `analysis_level` :

* essentia_lowlevel ;
* essentia_tensorflow ;
* allinone_structure ;
* openl3 ;
* clustering.

### 8.10 Table docker_runtime_checks

Cette table conserve les résultats des tests de disponibilité de l’environnement Docker.

Champs :

* id ;
* check_name ;
* service_name ;
* image_name ;
* image_tag ;
* command ;
* exit_code ;
* stdout ;
* stderr ;
* success ;
* created_at.

Exemples de checks :

* docker_available ;
* compose_available ;
* essentia_lowlevel_smoke_test ;
* essentia_tensorflow_smoke_test ;
* ffmpeg_available ;
* yt_dlp_available.

### 8.11 Table clusters

Champs :

* id ;
* algorithm ;
* feature_profile ;
* parameters_json ;
* created_at ;
* description ;
* user_label.

### 8.12 Table cluster_memberships

Champs :

* id ;
* cluster_id ;
* track_id ;
* cluster_label ;
* probability ;
* umap_x ;
* umap_y ;
* created_at.

### 8.13 Table library_actions

Cette table est importante pour tracer les actions de gestion de bibliothèque.

Champs :

* id ;
* action_type ;
* filter_json ;
* affected_count ;
* dry_run ;
* spotify_applied ;
* created_at ;
* result_json.

Exemples d’action_type :

* unlike_tracks ;
* restore_liked_tracks ;
* create_backup_playlist ;
* export_selection ;
* tag_tracks ;
* delete_local_cache ;
* delete_audio_segments_cache ;
* relaunch_failed_analysis.

---

## 9. Moteur de features

### 9.1 Principe multi-source

Chaque feature doit avoir :

* une valeur ;
* une source ;
* un score de confiance ;
* une date de calcul ;
* une version de pipeline ;
* éventuellement une réponse brute.

L’objectif est d’éviter de mélanger sans distinction :

* features ReccoBeats ;
* features Essentia ;
* features librosa ;
* features issues des modèles TensorFlow ;
* embeddings ;
* features déduites ;
* tags utilisateur ;
* valeurs manuelles.

### 9.2 Priorité des sources

Priorité proposée :

1. valeur utilisateur manuelle ;
2. analyse locale complète sur plusieurs segments ;
3. analyse locale segment unique ;
4. ReccoBeats ;
5. inférence metadata ;
6. valeur inconnue.

Cette priorité peut varier selon la feature. Par exemple :

* tempo : local Essentia/all-in-one peut être prioritaire sur ReccoBeats si confiance élevée ;
* danceability : ReccoBeats peut être prioritaire si le modèle local est encore expérimental ;
* structure : all-in-one est prioritaire ;
* key : comparer ReccoBeats, Essentia et une méthode dédiée si disponible ;
* embeddings : Discogs EffNet, OpenL3 ou modèles Essentia TensorFlow sont prioritaires.
* moods/styles/timbres : les modèles TensorFlow locaux sont prioritaires si le modèle est versionné et testé.

### 9.3 Gestion des valeurs manquantes

Cas possibles :

* ReccoBeats retourne toutes les features principales ;
* ReccoBeats retourne partiellement ;
* ReccoBeats ne trouve pas le titre ;
* l’analyse locale est nécessaire pour les features avancées ;
* le segment ne peut pas être téléchargé ;
* la feature est impossible à calculer.

Stratégie :

```text
Pour chaque track :
  1. chercher features en cache SQLite ;
  2. compléter via ReccoBeats ;
  3. identifier les champs manquants ou insuffisants ;
  4. si nécessaire, résoudre une URL compatible yt-dlp ;
  5. télécharger uniquement les segments nécessaires ;
  6. lancer l’analyse locale ;
  7. compléter ou remplacer selon confiance ;
  8. recalculer les scores dérivés ;
  9. supprimer les fichiers temporaires ;
  10. mettre à jour le statut global.
```

### 9.4 Statuts d’enrichissement

Statuts proposés :

* not_started ;
* pending ;
* reccobeats_done ;
* reccobeats_failed ;
* local_required ;
* segment_download_pending ;
* segment_download_done ;
* segment_download_failed ;
* local_pending ;
* local_done ;
* partial ;
* complete ;
* failed ;
* skipped ;
* stale.

---

## 10. Gestion des retries et rate limits

### 10.1 Principe

Les appels réseau doivent être robustes. Spotify, ReccoBeats ou la récupération de segments peuvent échouer temporairement pour plusieurs raisons :

* rate limiting ;
* timeout ;
* erreur réseau ;
* service temporairement indisponible ;
* réponse incomplète ;
* erreur de parsing ;
* quota temporaire.

Le système doit distinguer :

* erreur temporaire relançable ;
* erreur permanente ;
* ressource introuvable ;
* erreur de configuration ;
* erreur utilisateur ;
* rate limit explicite.

### 10.2 Stratégie de retry

Stratégie recommandée :

* retry avec exponential backoff ;
* jitter aléatoire pour éviter les relances simultanées ;
* respect du header `Retry-After` lorsqu’il existe ;
* nombre maximal de tentatives configurables ;
* stockage de `attempt_count` et `next_retry_at` ;
* relance manuelle possible depuis l’interface ;
* relance automatique uniquement pour les erreurs transitoires.

Exemple de politique :

```yaml
retry_policy:
  max_attempts: 5
  initial_delay_seconds: 2
  max_delay_seconds: 120
  backoff_multiplier: 2
  jitter: true
  respect_retry_after: true
```

### 10.3 File de jobs

Les opérations longues doivent passer par une file de jobs locale :

* import Spotify ;
* enrichissement ReccoBeats ;
* téléchargement de segments ;
* analyse locale ;
* embeddings ;
* clustering ;
* synchronisation Spotify.

Chaque job doit avoir :

* status ;
* progress ;
* current_step ;
* attempt_count ;
* last_error ;
* next_retry_at ;
* created_at ;
* started_at ;
* finished_at.

---

## 11. Moteur de clustering

### 11.1 Objectif

Le clustering doit permettre de découvrir des groupes naturels dans la bibliothèque, sans limiter l’analyse à la musique électronique.

Exemples de clusters possibles :

* titres vocaux pop/rock ;
* morceaux acoustiques calmes ;
* ambient/drone ;
* hip-hop/rap vocal ;
* titres expérimentaux ;
* tracks sombres et industriels ;
* EBM/industrial ;
* IDM ;
* techno ;
* morceaux rapides et énergiques ;
* morceaux lents et mélancoliques ;
* morceaux instrumentaux ;
* morceaux à forte densité vocale ;
* titres lumineux ou positifs ;
* titres bruitistes ou texturaux ;
* morceaux orientés basse/groove ;
* titres anciens ou par période ;
* clusters par similarité d’embeddings indépendamment du genre.

### 11.2 Features utilisées

Feature set minimal :

* tempo ;
* energy ;
* danceability ;
* valence ;
* acousticness ;
* instrumentalness ;
* speechiness ;
* liveness ;
* loudness ;
* key/mode encodés ;
* genre embeddings ou tags ;
* audio embeddings si disponibles.

Feature set avancé :

* OpenL3 embeddings ;
* Discogs EffNet embeddings ;
* MFCC summary ;
* chroma summary ;
* HPCP summary ;
* mood scores ;
* arousal/valence ;
* structure features ;
* scores dérivés généralistes ;
* densité vocale ;
* profil acoustique/électronique ;
* stabilité rythmique.

### 11.3 Profils de clustering

Le moteur doit permettre plusieurs profils :

* profil généraliste : adapté à toute la bibliothèque ;
* profil mood : énergie, valence, arousal, intensité, calme ;
* profil timbre : embeddings, MFCC, spectral features ;
* profil vocal/instrumental : speechiness, vocal presence, instrumentalness ;
* profil genre approximatif : tags, embeddings, métadonnées ;
* profil rythmique : BPM, onset, groove, stabilité ;
* profil mix/DJ optionnel : BPM, tonalité, énergie, structure.

### 11.4 UMAP

UMAP sert à projeter les tracks en 2D pour l’interface.

Paramètres à exposer plus tard :

* n_neighbors ;
* min_dist ;
* metric ;
* feature profile ;
* random_state.

### 11.5 HDBSCAN

HDBSCAN sert à détecter des clusters sans imposer un nombre fixe de groupes.

Paramètres à exposer plus tard :

* min_cluster_size ;
* min_samples ;
* metric ;
* cluster_selection_method.

Les tracks non assignés doivent être affichés comme bruit/outliers, sans les supprimer.

### 11.6 Labeling des clusters

L’application peut proposer des labels automatiques :

* cluster_01 : vocal / pop-rock / énergie moyenne ;
* cluster_02 : calme / acoustique / faible intensité ;
* cluster_03 : instrumental / ambient / texture ;
* cluster_04 : EBM / industrial / sombre / mid-tempo ;
* cluster_05 : IDM / expérimental / rythmique complexe ;
* cluster_06 : rap vocal / forte densité vocale ;
* cluster_07 : haute énergie / rapide / lumineux.

L’utilisateur doit pouvoir renommer les clusters manuellement.

---

## 12. Moteur de génération de playlists

### 12.1 Principe

Le générateur de playlists doit transformer une configuration utilisateur en playlist Spotify candidate.

Pipeline :

```text
Sélection source
        ↓
Filtres stricts
        ↓
Scoring pondéré
        ↓
Contraintes de diversité
        ↓
Déduplication
        ↓
Ordonnancement
        ↓
Preview
        ↓
Dry-run Spotify
        ↓
Synchronisation
```

### 12.2 Configuration de playlist

Exemple généraliste :

```yaml
name: "Dark / Intense / Mixed Genres"
target_size: 80

source:
  liked_tracks: true
  playlists_include:
    - "Liked Songs"
  playlists_exclude:
    - "Already Sorted"

filters:
  energy:
    min: 0.45
  mood_dark_score:
    min: 0.55
  vocal_presence:
    max: 0.80
  feature_confidence:
    min: 0.50

weights:
  mood_dark_score: 0.25
  intensity_score: 0.20
  similarity_to_seed: 0.20
  playlist_fit_score: 0.15
  diversity_bonus: 0.10
  user_affinity_score: 0.10

constraints:
  max_tracks_per_artist: 3
  max_tracks_per_album: 2
  avoid_duplicate_isrc: true
  avoid_existing_in_playlists:
    - "Dark Archive"
  min_feature_confidence: 0.50

ordering:
  mode: "energy_curve"
  energy_curve: "progressive"
  avoid_same_artist_consecutive: true

spotify:
  playlist_name: "Dark / Intense / Mixed Genres"
  visibility: "private"
  sync_mode: "replace_after_dry_run"
```

Exemple optionnel plus orienté mix :

```yaml
name: "EBM / Industrial — Mix Context"
target_size: 80

source:
  liked_tracks: true

filters:
  bpm:
    min: 118
    max: 145
  energy:
    min: 0.60
  mood_dark_score:
    min: 0.55

weights:
  energy: 0.20
  mood_dark_score: 0.20
  rhythmic_stability_score: 0.15
  harmonic_compatibility_score: 0.15
  similarity_to_seed: 0.15
  diversity_bonus: 0.15

ordering:
  mode: "mix_progression"
  bpm_curve: "ascending_then_plateau"
  harmonic_mixing: true
  energy_curve: "warmup_peak_cooldown"
```

### 12.3 Filtres stricts

Un filtre strict élimine les tracks avant scoring.

Exemples :

* BPM hors intervalle ;
* energy trop faible ;
* genre exclu ;
* artiste blacklisté ;
* titre déjà présent dans une playlist ;
* features insuffisamment fiables ;
* morceau indisponible sur Spotify ;
* titre déjà traité ou rejeté manuellement.

### 12.4 Scoring pondéré

Le scoring doit produire un score final normalisé entre 0 et 1.

Exemple :

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

### 12.5 Contraintes de diversité

Contraintes utiles :

* maximum N titres par artiste ;
* maximum N titres par album ;
* éviter deux titres consécutifs du même artiste ;
* diversité de genres ;
* diversité de décennies ;
* diversité de clusters ;
* conservation d’un certain nombre de titres rares ;
* conservation d’un certain nombre de titres récemment ajoutés ;
* équilibre vocal/instrumental ;
* équilibre calme/intense ;
* équilibre connu/découverte.

### 12.6 Ordonnancement

Modes d’ordering :

* none ;
* random_weighted ;
* bpm_ascending ;
* bpm_descending ;
* harmonic ;
* energy_curve ;
* mood_curve ;
* cluster_blocks ;
* seed_similarity_path ;
* discovery_flow ;
* mix_progression optionnel.

Le mode généraliste `energy_curve` doit combiner :

* progression d’énergie ;
* variation contrôlée de l’intensité ;
* diversité artiste ;
* diversité cluster ;
* équilibre vocal/instrumental ;
* cohérence sonore.

Le mode optionnel `mix_progression` peut ajouter :

* progression BPM ;
* compatibilité harmonique ;
* intro/outro usability ;
* stabilité rythmique ;
* densité vocale.

---

## 13. Interface utilisateur

### 13.1 Écran 1 — Connexion Spotify

Fonctions :

* login OAuth ;
* choix/affichage des scopes ;
* test de connexion ;
* affichage du profil ;
* statut token ;
* déconnexion ;
* gestion des erreurs OAuth.

### 13.2 Écran 2 — Import bibliothèque

Fonctions :

* importer les titres likés ;
* importer les playlists ;
* importer les contenus des playlists ;
* créer un snapshot ;
* afficher nombre de titres ;
* afficher nombre de playlists ;
* afficher progression ;
* afficher erreurs ;
* relancer un import partiel ;
* comparer au snapshot précédent.

### 13.3 Écran 3 — Gestion bibliothèque

Fonctions :

* table complète des titres likés ;
* recherche titre/artiste/album ;
* filtres avancés ;
* sélection multiple ;
* suppression de likes par critères ;
* restauration depuis snapshot ;
* création de playlist de secours ;
* détection titres disparus ;
* détection doublons ;
* actions en dry-run ;
* validation avant action Spotify ;
* historique des actions.

Exemples de filtres :

* artiste contient ;
* album contient ;
* titre contient ;
* date d’ajout avant/après ;
* BPM entre ;
* energy supérieure à ;
* mood ;
* vocal/instrumental ;
* playlist source ;
* statut absent ;
* statut features incomplètes ;
* doublon ISRC ;
* même titre/artiste avec durée proche.

### 13.4 Écran 4 — Enrichissement features

Fonctions :

* afficher couverture features ;
* lancer ReccoBeats ;
* lancer analyse locale ;
* afficher le nombre de titres nécessitant yt-dlp ;
* afficher les statuts de téléchargement de segments ;
* afficher les statuts d’analyse locale ;
* relancer uniquement les failed ;
* relancer uniquement les missing ;
* visualiser la source des features ;
* comparer ReccoBeats vs local ;
* afficher score de confiance ;
* afficher raw payload si mode debug ;
* nettoyer les fichiers temporaires résiduels.

### 13.5 Écran 5 — Explorateur musical

Fonctions :

* table filtrable ;
* colonnes configurables ;
* tri par BPM, energy, valence, danceability ;
* affichage key/Camelot ;
* affichage genres ;
* affichage tags ;
* affichage cluster ;
* affichage scores généralistes ;
* édition tags utilisateur ;
* ajout à une playlist candidate ;
* exclusion manuelle.

### 13.6 Écran 6 — Carte de similarité

Fonctions :

* projection UMAP 2D ;
* clusters HDBSCAN ;
* zoom/pan ;
* sélection de points ;
* sélection de cluster ;
* coloration par feature ;
* coloration par playlist ;
* coloration par genre ;
* coloration par année ;
* coloration par source features ;
* coloration par profil : énergie, mood, vocal, acoustique/électronique ;
* création de playlist depuis sélection ;
* renommage cluster.

### 13.7 Écran 7 — Générateur de playlists

Fonctions :

* éditeur visuel de règles ;
* éditeur YAML avancé ;
* presets ;
* seed tracks ;
* filtres stricts ;
* pondérations ;
* contraintes ;
* ordering ;
* preview ;
* explication du score par track ;
* export local ;
* préparation sync Spotify.

### 13.8 Écran 8 — Synchronisation Spotify

Fonctions :

* créer playlist ;
* mettre à jour playlist ;
* remplacer contenu ;
* ajouter seulement nouveaux titres ;
* retirer titres obsolètes ;
* dry-run ;
* diff avant/après ;
* confirmation ;
* historique ;
* rollback via snapshot lorsque possible.

### 13.9 Écran Paramètres

Fonctions :

* configuration Spotify ;
* configuration ReccoBeats ;
* statut Docker Desktop / WSL2 ;
* statut des services Docker Compose ;
* lancement/arrêt du core Docker si supporté ;
* configuration yt-dlp ;
* configuration FFmpeg ;
* configuration chemins temporaires ;
* configuration cache ;
* configuration modèles audio ;
* choix du dossier SQLite ;
* export/import settings ;
* reset cache ;
* nettoyage fichiers temporaires ;
* mode debug.

---

## 14. Authentification Spotify

L’application doit utiliser OAuth Spotify avec PKCE, adapté aux applications desktop ou client-side ne pouvant pas protéger un client secret.

Scopes probables :

* user-library-read ;
* user-library-modify ;
* playlist-read-private ;
* playlist-read-collaborative ;
* playlist-modify-private ;
* playlist-modify-public.

Les scopes doivent être affichés clairement à l’utilisateur.

Le token doit être stocké de manière raisonnablement sécurisée :

* stockage OS keychain si possible ;
* sinon stockage local chiffré ;
* ne pas stocker inutilement le client secret ;
* utiliser PKCE.

---

## 15. Gestion des segments audio

### 15.1 Principe

L’utilisateur ne fournit pas de fichiers audio manuellement. Les fichiers analysés sont des fichiers locaux téléchargés temporairement par l’application, généralement sous forme de segments courts récupérés avec yt-dlp.

L’application doit donc séparer trois étapes :

1. résolution du titre vers une URL exploitable ;
2. récupération temporaire de segments avec yt-dlp ;
3. analyse locale puis suppression du fichier temporaire.

### 15.2 Stockage audio

Par défaut :

* ne pas conserver les fichiers audio ;
* ne garder que les features ;
* supprimer les fichiers temporaires ;
* conserver les logs techniques ;
* conserver le hash de source ou de segment si nécessaire pour éviter les doublons ;
* conserver les erreurs relançables pour audit technique.

### 15.3 Provider audio abstrait

Le core doit définir une interface abstraite :

```text
AudioProvider
  resolve(track)
  get_segments(track, segment_strategy)
  cleanup(job)
```

Providers possibles :

* YtDlpSegmentProvider ;
* CachedSegmentProvider ;
* TestAudioProvider ;
* FutureProvider.

L’avantage est de découpler le moteur d’analyse de la méthode d’obtention audio.

### 15.4 Stratégie de résolution

Une résolution de segment peut s’appuyer sur :

* titre ;
* artiste principal ;
* album ;
* durée ;
* ISRC ;
* identifiants externes ;
* résultat de recherche vidéo ;
* score de matching textuel ;
* score de cohérence de durée.

Le système doit stocker un score de confiance pour éviter d’analyser une mauvaise version du morceau.

Champs utiles :

* query_text ;
* candidate_title ;
* candidate_channel ;
* candidate_duration ;
* expected_duration ;
* duration_delta ;
* text_match_score ;
* selected ;
* rejected_reason.

---

## 16. Configuration utilisateur

### 16.1 Format

Les règles doivent être stockées en JSON dans SQLite et exportables en YAML.

Le YAML est utile pour :

* versionner ;
* partager ;
* éditer manuellement ;
* créer des presets.

### 16.2 Presets initiaux

Presets possibles :

* Dark / Intense ;
* Calm / Focus ;
* Ambient / Drone ;
* IDM / Experimental ;
* EBM / Industrial ;
* Pop / Vocal ;
* Acoustic / Organic ;
* Electronic / Synthetic ;
* High Energy ;
* Low Vocal ;
* Instrumental Focus ;
* Discover Forgotten Likes ;
* Recently Added ;
* Clean Library ;
* Missing Tracks Recovery ;
* Mix Context, optionnel.

---

## 17. Roadmap projet

### Phase 0 — cadrage technique

Objectifs :

* initialiser repo ;
* choisir structure monorepo ;
* valider Tauri + Svelte ;
* valider Docker Desktop + WSL2 ;
* valider Docker Compose ;
* valider core Python dockerisé ;
* valider API locale sur `127.0.0.1` ;
* valider SQLite ;
* définir modèle de données initial.

Livrables :

* app desktop vide ;
* communication UI ↔ core Docker ;
* base SQLite créée ;
* smoke test Docker Essentia low-level ;
* écran settings minimal.

### Phase 1 — Spotify Library Backup

Objectifs :

* OAuth Spotify ;
* import titres likés ;
* import playlists ;
* snapshots ;
* diff entre snapshots.

Livrables :

* écran connexion ;
* écran import ;
* écran snapshot ;
* base remplie ;
* export CSV/JSON.

### Phase 2 — Gestion bibliothèque

Objectifs :

* recherche et filtres ;
* détection absents ;
* doublons ;
* actions groupées ;
* dry-run ;
* restauration.

Livrables :

* écran gestion bibliothèque ;
* actions locales ;
* actions Spotify sécurisées ;
* historique des actions.

### Phase 3 — ReccoBeats enrichment

Objectifs :

* intégration ReccoBeats ;
* cache features ;
* statuts ;
* couverture ;
* retry/rate limiting ;
* relance failed/missing.

Livrables :

* écran enrichissement ;
* table audio_features ;
* source tracking ;
* score de confiance ;
* job queue locale.

### Phase 4 — yt-dlp + analyse locale par segments

Objectifs :

* intégrer yt-dlp ;
* intégrer FFmpeg ;
* télécharger uniquement des segments ;
* limiter chaque segment à 30 secondes maximum ;
* intégrer Essentia via Docker ;
* intégrer l’image `ghcr.io/mtg/essentia:bullseye-v2.1_beta5` ;
* intégrer streaming_extractor_music ;
* fallback des features manquantes ;
* nettoyage automatique des fichiers temporaires.

Livrables :

* YtDlpSegmentProvider ;
* audio_download_jobs ;
* track_segments ;
* analyse locale segmentée ;
* worker Docker `essentia-lowlevel` ;
* fusion ReccoBeats/local ;
* retries et logs.

### Phase 5 — Playlist generator v1

Objectifs :

* règles simples ;
* filtres stricts ;
* scoring généraliste ;
* contraintes ;
* preview ;
* export Spotify.

Livrables :

* écran générateur ;
* presets initiaux ;
* dry-run sync ;
* création playlist Spotify.

### Phase 6 — Clustering visuel généraliste

Objectifs :

* normalisation features ;
* profils de clustering ;
* UMAP ;
* HDBSCAN ;
* carte 2D ;
* sélection cluster ;
* génération playlist depuis cluster.

Livrables :

* écran carte de similarité ;
* clusters persistés ;
* labels manuels ;
* export sélection ;
* presets de feature profiles.

### Phase 7 — Analyse locale avancée

Objectifs :

* intégrer all-in-one ;
* intégrer image Docker custom `essentia-tensorflow` ;
* intégrer embeddings OpenL3 ou Discogs EffNet ;
* intégrer modèles TensorFlow Essentia ;
* améliorer structure musicale ;
* améliorer densité vocale ;
* améliorer scores mood/intensité/focus ;
* comparer les sources de features.

Livrables :

* moteur local audio avancé ;
* worker Docker TensorFlow ;
* source tracking détaillé ;
* comparaison ReccoBeats/local ;
* scores dérivés généralistes ;
* embeddings persistés.

### Phase 8 — Playlist engine avancé

Objectifs :

* ordonnancement avancé ;
* compatibilité harmonique optionnelle ;
* courbe d’énergie ;
* seed tracks ;
* diversité contrôlée ;
* explication des scores.

Livrables :

* moteur v2 ;
* presets avancés ;
* visualisation score ;
* génération plus musicale et plus configurable.

### Phase 9 — Packaging et polish

Objectifs :

* build Windows ;
* packaging Tauri ;
* gestion erreurs ;
* documentation utilisateur ;
* backup/restore DB ;
* tests.

Livrables :

* installateur local ;
* documentation ;
* jeu de test ;
* version MVP stable.

---

## 18. Stratégie de tests

### 18.1 Tests unitaires Python

À tester :

* parsing Spotify ;
* normalisation tracks ;
* matching ISRC ;
* sauvegarde SQLite ;
* diff snapshots ;
* règles playlist ;
* scoring ;
* contraintes ;
* dry-run ;
* feature merge ;
* gestion des valeurs manquantes ;
* validation durée segment <= 30 secondes ;
* génération de ranges yt-dlp ;
* retry/backoff ;
* cleanup fichiers temporaires ;
* construction des commandes Docker ;
* parsing des sorties JSON Essentia ;
* versionnement des pipelines d’analyse.

### 18.2 Tests d’intégration

À tester :

* import Spotify complet mocké ;
* enrichissement ReccoBeats mocké ;
* téléchargement segment mocké ;
* analyse locale sur segment de test ;
* smoke test `essentia-lowlevel` via Docker ;
* smoke test `essentia-tensorflow` via Docker ;
* génération playlist ;
* écriture SQLite ;
* synchronisation dry-run ;
* rollback local.

### 18.3 Tests UI

À tester :

* navigation écrans ;
* filtres table ;
* sélection multiple ;
* affichage progression ;
* confirmation actions dangereuses ;
* affichage erreurs ;
* affichage jobs failed/rate limited ;
* relance manuelle d’un job ;
* nettoyage cache temporaire.

### 18.4 Dataset de test

Créer un dataset local fictif :

* 100 tracks ;
* 20 artistes ;
* 10 albums ;
* 5 playlists ;
* 3 snapshots ;
* doublons ;
* titres disparus ;
* features manquantes ;
* features ReccoBeats mockées ;
* segments audio de test ;
* erreurs réseau simulées ;
* cas de rate limiting simulés.


### 18.5 Tests smoke Docker

Des tests smoke doivent permettre de vérifier rapidement l’environnement sur Windows.

Checks minimaux :

```text
docker --version
docker compose version
docker pull ghcr.io/mtg/essentia:bullseye-v2.1_beta5
essentia_streaming_extractor_music sur un WAV court
génération d’un JSON low-level
build de l’image essentia-tensorflow
inférence TensorFlow sur un WAV court
génération d’un JSON embeddings
```

Ces tests doivent être exécutables indépendamment de l’interface Tauri. Ils peuvent être exposés dans l’écran Paramètres en mode debug.

### 18.6 Tests de reproductibilité

À vérifier :

* même segment d’entrée ;
* même image Docker ;
* même version de pipeline ;
* même profil YAML ;
* même modèle TensorFlow ;
* JSON de sortie stable ou variation documentée ;
* hash du fichier segment ;
* hash du modèle utilisé.

---

## 19. Risques techniques

### 19.1 Docker / WSL2 / Windows

Risques :

* Docker Desktop non installé ;
* backend WSL2 désactivé ;
* chemins Windows mal montés dans les conteneurs ;
* lenteur des volumes montés depuis Windows ;
* conflit de ports sur `127.0.0.1:8765` ;
* images Docker lourdes ;
* échec de build de l’image TensorFlow ;
* difficulté de distribution pour un utilisateur non technique.

Mitigation :

* script de diagnostic environnement ;
* écran Paramètres affichant l’état Docker ;
* volumes projet standardisés ;
* éviter les chemins absolus Windows dans le core ;
* documenter l’installation Docker Desktop + WSL2 ;
* proposer des commandes smoke test ;
* versionner les images ;
* pinner les tags ou digests pour les images critiques ;
* séparer MVP développeur et packaging utilisateur final.

### 19.2 Spotify API

Risques :

* changements d’endpoints ;
* restrictions d’accès ;
* rate limits ;
* champs manquants ;
* playlists non accessibles ;
* tracks indisponibles.

Mitigation :

* cache local ;
* snapshots ;
* abstraction SpotifyClient ;
* gestion des erreurs ;
* pagination robuste ;
* dry-run ;
* retry/backoff ;
* tests mockés.

### 19.3 ReccoBeats

Risques :

* API indisponible ;
* rate limit ;
* track non trouvée ;
* valeurs incohérentes ;
* changement de format.

Mitigation :

* cache ;
* statut par track ;
* retry ;
* fallback local ;
* stockage raw_json ;
* versionnement source.

### 19.4 yt-dlp et récupération de segments

Risques :

* échec de résolution d’un titre ;
* mauvais matching vidéo ;
* changement de comportement du provider ;
* limitation temporaire ;
* segment non représentatif ;
* coupe imprécise ;
* temps de traitement élevé.

Mitigation :

* matching robuste titre/artiste/durée ;
* score de confiance ;
* validation manuelle possible ;
* segment de 30 secondes maximum ;
* plusieurs segments courts plutôt qu’un long extrait ;
* retry/backoff ;
* cache des résultats ;
* logs détaillés ;
* suppression des fichiers temporaires.

### 19.5 Analyse locale

Risques :

* dépendances lourdes ;
* packaging complexe ;
* temps de calcul ;
* CPU/GPU ;
* incohérence des résultats ;
* résultats moins fiables selon les styles musicaux.

Mitigation :

* rendre l’analyse locale progressive ;
* exécuter en jobs ;
* stocker progression ;
* permettre annulation ;
* versionner les modèles ;
* tester packaging tôt ;
* conserver la source et la confiance de chaque feature.

### 19.6 Clustering

Risques :

* clusters peu interprétables ;
* UMAP instable selon paramètres ;
* HDBSCAN classe beaucoup de points en bruit ;
* features incomplètes ;
* biais vers certains genres si les features sont trop orientées électronique.

Mitigation :

* paramètres configurables ;
* profils de features ;
* profils généralistes ;
* labels manuels ;
* visualisations multiples ;
* ne jamais supprimer les outliers ;
* ne pas faire dépendre le clustering uniquement de scores de mix.

### 19.7 UX

Risques :

* trop de paramètres ;
* application trop technique ;
* actions Spotify dangereuses ;
* confusion entre local et distant ;
* attente longue pendant l’analyse audio.

Mitigation :

* presets ;
* mode avancé ;
* dry-run obligatoire ;
* confirmations ;
* explication des actions ;
* historique ;
* affichage de progression ;
* relance des échecs ;
* séparation claire entre import, enrichissement, clustering et sync.

---

## 20. Décisions techniques validées

|Sujet|Décision|
|-|-|
|Type d’application|Desktop standalone|
|Backend web|Non hébergé, mais API locale Docker sur 127.0.0.1|
|CLI MVP|Non|
|Interface|Tauri + Svelte exécutés sur Windows|
|Core|Python dockerisé|
|Base|SQLite sur volume persistant Docker|
|Docker Desktop + WSL2|Oui, environnement technique validé|
|Docker Compose|Oui, orchestration du core et des workers|
|Tauri dans Docker|Non, Tauri reste côté Windows|
|API locale core|Oui, exposée uniquement sur 127.0.0.1|
|API Spotify|Oui, pour bibliothèque/playlists/sync|
|Audio features Spotify|Non, ne pas dépendre des anciennes features|
|ReccoBeats|Oui, source de features simples|
|yt-dlp|Oui, pour récupérer des segments audio temporaires|
|FFmpeg|Oui, pour extraction, conversion et découpe|
|Segment audio|30 secondes maximum par segment|
|Téléchargement complet morceau|Non pour l’analyse standard|
|Analyse locale|Oui, souvent nécessaire pour compléter ReccoBeats|
|Essentia low-level|Oui, image `ghcr.io/mtg/essentia:bullseye-v2.1_beta5`|
|Essentia TensorFlow|Oui, image Docker custom projet|
|Essentia|Oui, via Docker/WSL2|
|librosa|Oui, complément|
|all-in-one|Oui, structure musicale|
|OpenL3/Discogs EffNet|Oui, embeddings via worker Docker avancé|
|UMAP|Oui, visualisation|
|HDBSCAN|Oui, clustering|
|Scores dérivés|Oui, généralistes par défaut|
|Scores DJ/mix|Optionnels, non centraux|
|Stockage audio permanent|Non par défaut|
|Gestion bibliothèque|Oui, écran dédié|
|Dry-run|Obligatoire avant modifications Spotify|
|Retry/rate limiting|Oui, sur API et jobs réseau|

---

## 21. Priorités de développement

Priorité absolue :

1. environnement Docker Desktop + WSL2 validé ;
2. Docker Compose projet ;
3. core Python dockerisé ;
4. API locale `127.0.0.1` ;
5. SQLite propre sur volume persistant ;
6. import Spotify fiable ;
7. snapshots ;
8. gestion bibliothèque ;
9. ReccoBeats cache ;
10. système de jobs et retries ;
11. récupération de segments yt-dlp avec limite 30 secondes ;
12. worker Essentia low-level ;
13. smoke tests Docker ;
14. playlist generator simple ;
15. sync Spotify dry-run.

Priorité secondaire :

16. worker Essentia TensorFlow ;
17. embeddings Discogs EffNet ou OpenL3 ;
18. UMAP/HDBSCAN ;
19. carte de similarité ;
20. profils de clustering généralistes ;
21. all-in-one ;
22. scores dérivés généralistes ;
23. UI de monitoring des jobs Docker.

Priorité tardive :

24. packaging complet Windows ;
25. assistance à l’installation Docker pour utilisateur final ;
26. presets nombreux ;
27. modèles custom ;
28. UI très avancée ;
29. profils de mix/DJ avancés.

---

## 22. Résultat attendu

À terme, l’application doit permettre à l’utilisateur de transformer une bibliothèque Spotify massive en une bibliothèque locale fiable, explorable et exploitable.

Elle doit résoudre trois problèmes principaux :

1. Spotify ne donne plus accès aux anciennes audio features de manière fiable.
2. Une grande bibliothèque likée devient difficile à trier manuellement.
3. Spotify peut évoluer, masquer, rendre indisponibles ou perdre des titres sans que l’utilisateur puisse facilement auditer sa bibliothèque.

La solution proposée est une application desktop locale, appuyée par un core technique dockerisé reproductible, qui combine :

* sauvegarde ;
* synchronisation ;
* enrichissement ;
* récupération de segments audio temporaires ;
* analyse audio locale ;
* clustering ;
* règles utilisateur ;
* génération de playlists ;
* contrôle avant écriture Spotify.

Le cœur du projet n’est donc pas seulement un générateur de playlists, mais un véritable système personnel de gestion et de curation musicale.

L’architecture finale doit permettre de développer sur Windows sans dépendre d’un build natif d’Essentia. Les composants audio lourds sont exécutés dans Docker, avec deux niveaux d’analyse : Essentia low-level pour les descripteurs classiques, puis Essentia TensorFlow pour les embeddings et features avancées.


Le projet doit rester suffisamment généraliste pour fonctionner sur une bibliothèque variée. Les usages électroniques, EBM, industrial ou IDM restent importants, mais ils ne doivent pas déterminer toute la logique de scoring, de clustering ou de génération. Les profils doivent pouvoir s’adapter aussi bien à des morceaux vocaux, acoustiques, ambient, pop, rock, rap, expérimentaux ou instrumentaux.
