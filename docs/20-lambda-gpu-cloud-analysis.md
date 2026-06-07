# 20 — Exécution cloud GPU sur Lambda Labs pour l’analyse audio avancée

## 1. Objectif

Ce document décrit la mise en place d’une instance GPU Lambda Labs pour exécuter la pipeline d’analyse audio avancée du projet Spotify Curator.

L’objectif est d’accélérer le stage le plus lent :

```text
essentia_tensorflow

```

Le workflow cible est :

```text
PC local
  ↓ export SQLite
Lambda Labs A6000 GPU VM
  ↓ Docker Compose GPU
UI locale via tunnel SSH
  ↓ lancement analyse depuis l’interface
SQLite analysée
  ↓ récupération locale
PC local

```

Le but n’est pas de remplacer le fonctionnement local du projet. Le mode Lambda est un mode d’exécution ponctuel pour analyser rapidement une bibliothèque complète.

**Fichiers implémentés** : [`.env.lambda.example`](../.env.lambda.example), [`docker-compose.gpu.yml`](../docker-compose.gpu.yml), [`docker-compose.lambda.yml`](../docker-compose.lambda.yml), [`Makefile`](../Makefile), [`scripts/lambda/`](../scripts/lambda/), [`docker/frontend/Dockerfile`](../docker/frontend/Dockerfile).

**Services Compose** : `core-api` (API `127.0.0.1:8000` → `:8765`), `frontend-dev` (profil `lambda-ui`, port `5173`), workers audio/TF.

**Santé API** : `GET /api/v1/health`. **SQLite active** : `spotify_curator.sqlite` sur SSD local.

---

## 2. Pourquoi Lambda Labs pour ce projet

Lambda Labs est plus simple que RunPod pour ce projet car Lambda fournit une vraie VM Linux GPU. Cela permet de conserver l’architecture Docker Compose existante.

Comparaison rapide :

```text
RunPod
- Pod/conteneur managé
- nécessite idéalement une image Docker unique multi-processus
- plus économique
- plus d’adaptation projet

Lambda Labs
- VM Linux GPU classique
- Docker + NVIDIA Container Toolkit disponibles
- Docker Compose utilisable
- SSH classique
- tunnel SSH simple pour UI/API
- plus simple pour ce projet

```

Pour Spotify Curator, Lambda est donc recommandé si l’objectif est de lancer rapidement la pipeline sans refactoriser le déploiement.

---

## 3. Architecture Lambda cible

Sur Lambda, on utilise une instance GPU A6000 avec Docker Compose.

```text
Lambda A6000 VM
├── Docker
├── NVIDIA Container Toolkit
├── docker compose
├── projet spotify-curator
├── docker-compose.yml
├── docker-compose.gpu.yml
├── docker-compose.lambda.yml
├── active runtime local SSD
│   └── /home/ubuntu/spotify-curator-runtime
│       ├── data/app.sqlite
│       ├── temp-audio/
│       └── logs/
└── filesystem persistant Lambda
    └── /lambda/nfs/persistent-storage/spotify-curator
        ├── backups/
        ├── models/
        ├── exports/
        └── final-output/

```

### Décision importante : SQLite actif sur SSD local

Il est préférable de faire travailler SQLite sur le disque SSD local de l’instance plutôt que directement sur le filesystem réseau Lambda.

Raison :

```text
SQLite + beaucoup d’écritures + plusieurs workers
→ meilleur comportement sur disque local

```

Le filesystem Lambda reste utilisé pour :

```text
- sauvegarder la base avant analyse ;
- stocker une copie finale analysée ;
- conserver les modèles Essentia ;
- conserver les logs importants ;
- éviter de perdre les résultats si l’instance est supprimée après sauvegarde.

```

Le workflow recommandé est donc :

```text
1. Copier app.sqlite vers le SSD local de l’instance.
2. Lancer l’analyse sur cette copie locale.
3. Faire des checkpoints SQLite réguliers.
4. Copier la base finale vers le filesystem persistant.
5. Récupérer la base finale sur le PC local.

```

---

## 4. Configuration Lambda recommandée

### Instance recommandée

```text
Instance : 1x NVIDIA A6000
VRAM : 48 GB
vCPU : 14
RAM : 100 GiB
SSD local : 512 GiB

```

Cette configuration est suffisante pour :

```text
- une base SQLite locale ;
- les modèles Essentia ;
- les segments audio temporaires ;
- les workers Docker ;
- le frontend ;
- l’API ;
- un ou deux workers TensorFlow GPU.

```

### Choix GPU

Priorité :

```text
1. A6000 48 GB
2. A100 40 GB si A6000 indisponible, mais plus cher
3. A10 24 GB uniquement si A6000 indisponible

```

A6000 est le meilleur choix pour ce projet car :

```text
- 48 GB VRAM ;
- coût raisonnable ;
- bonne stabilité ;
- assez de VRAM pour tester 2 workers TensorFlow ;
- beaucoup plus simple qu’une plateforme marketplace.

```

---

## 5. Configuration workers recommandée

Le stage limitant est `essentia_tensorflow`.

L’A6000 n’est pas magique : lancer trop de workers TensorFlow sur un seul GPU peut réduire les performances à cause de :

```text
- duplication des graphes TensorFlow ;
- duplication des modèles Essentia ;
- duplication des caches ;
- contention GPU ;
- contention CPU lors du decode audio ;
- saturation I/O ;
- overhead de scheduling.

```

### Configuration initiale recommandée

```env
ESSENTIA_TF_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=2
AUDIO_DOWNLOADER_WORKERS=4
PREVIEW_RESOLVER_WORKERS=2
JOB_POLL_INTERVAL_MS=500
ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_TF_WARMUP=true
ESSENTIA_TF_DEVICE=gpu

```

C’est le profil de départ le plus sûr.

### Configuration optimisée à tester

Après validation GPU sur 20 à 50 pistes :

```env
ESSENTIA_TF_WORKERS=2
ESSENTIA_LOWLEVEL_WORKERS=2
AUDIO_DOWNLOADER_WORKERS=4
PREVIEW_RESOLVER_WORKERS=2
JOB_POLL_INTERVAL_MS=300
ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_TF_WARMUP=true
ESSENTIA_TF_DEVICE=gpu

```

C’est probablement le meilleur compromis sur une seule A6000.

### Configuration maximale non recommandée par défaut

```env
ESSENTIA_TF_WORKERS=3

```

À utiliser uniquement si toutes les conditions suivantes sont vraies :

```text
- VRAM utilisée < 32 GB avec 2 workers ;
- GPU utilization souvent < 60 % ;
- CPU non saturé ;
- aucun OOM TensorFlow ;
- les temps moyens diminuent réellement avec 3 workers.

```

### Configuration à éviter

```env
ESSENTIA_TF_WORKERS=4

```

Sur une seule A6000, 4 workers TensorFlow risquent de réduire la performance globale. Chaque worker charge ses propres graphes TensorFlow, ses predictors Essentia et ses caches. Le GPU sera partagé entre trop de processus.

### Règle pratique

```text
1 worker TF GPU : recommandé pour stabilité
2 workers TF GPU : recommandé après benchmark
3 workers TF GPU : expérimental
4 workers TF GPU : déconseillé

```

---

## 6. Batch size recommandé

Le projet actuel fonctionne principalement par segments/tracks. Si le worker TensorFlow traite un segment à la fois, le paramètre `batch_size` n’aura pas d’effet global tant qu’une vraie file de micro-batch n’est pas implémentée.

### Si le batching inter-segments n’est pas implémenté

Utiliser :

```env
ESSENTIA_TF_BATCH_SIZE=1

```

Puis compenser avec :

```env
ESSENTIA_TF_WORKERS=1

```

ou après benchmark :

```env
ESSENTIA_TF_WORKERS=2

```

### Si Cursor implémente un micro-batching TensorFlow

Valeurs recommandées :

```env
ESSENTIA_TF_BATCH_SIZE=8
ESSENTIA_TF_BATCH_TIMEOUT_MS=1000

```

Valeurs à tester :

```env
ESSENTIA_TF_BATCH_SIZE=4
ESSENTIA_TF_BATCH_SIZE=8
ESSENTIA_TF_BATCH_SIZE=16

```

Recommandation :

```text
batch_size=4  : très sûr
batch_size=8  : point de départ conseillé
batch_size=16 : possible sur A6000, à valider
batch_size=32 : probablement inutile ou instable pour cette pipeline

```

La priorité est d’éviter que le GPU attende trop longtemps pour former un batch. Pour une pipeline à jobs audio, un batch timeout court est préférable :

```env
ESSENTIA_TF_BATCH_TIMEOUT_MS=500

```

ou :

```env
ESSENTIA_TF_BATCH_TIMEOUT_MS=1000

```

### Recommandation finale batch

Pour Lambda A6000 :

```env
ESSENTIA_TF_BATCH_SIZE=8
ESSENTIA_TF_BATCH_TIMEOUT_MS=1000

```

Seulement si le micro-batching est implémenté.

Sinon :

```env
ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TF_WORKERS=1 ou 2

```

---

## 7. Variables TensorFlow recommandées

Ajouter dans l’environnement du worker TensorFlow GPU :

```env
ESSENTIA_TF_DEVICE=gpu
ESSENTIA_TF_WARMUP=true
ESSENTIA_MODEL_PROFILE=phase6-recommended

TF_FORCE_GPU_ALLOW_GROWTH=true
TF_CPP_MIN_LOG_LEVEL=1
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

```

Pour limiter l’oversubscription CPU :

### Avec 1 worker TensorFlow

```env
TF_NUM_INTRAOP_THREADS=4
TF_NUM_INTEROP_THREADS=2
OMP_NUM_THREADS=4

```

### Avec 2 workers TensorFlow

```env
TF_NUM_INTRAOP_THREADS=2
TF_NUM_INTEROP_THREADS=1
OMP_NUM_THREADS=2

```

L’objectif est de garder du CPU disponible pour :

```text
- API ;
- frontend ;
- job scheduler ;
- low-level worker ;
- audio decode ;
- SQLite ;
- ffmpeg ;
- workers downloader.

```

---

## 8. Préparer la base SQLite localement

Depuis le PC local, arrêter le projet :

```bash
docker compose down

```

Faire un checkpoint WAL :

```bash
sqlite3 data/app.sqlite "PRAGMA wal_checkpoint(FULL);"

```

Vérifier l’intégrité :

```bash
sqlite3 data/app.sqlite "PRAGMA integrity_check;"

```

Résultat attendu :

```text
ok

```

Créer une sauvegarde locale :

```bash
mkdir -p backups
cp data/app.sqlite backups/app.before-lambda.sqlite

```

Créer une archive d’export :

```bash
mkdir -p export-lambda/data
cp data/app.sqlite export-lambda/data/app.sqlite
tar -czf spotify-curator-lambda-input.tar.gz export-lambda

```

Si les modèles Essentia sont déjà présents localement :

```bash
mkdir -p export-lambda/models
cp -r models/* export-lambda/models/
tar -czf spotify-curator-lambda-input.tar.gz export-lambda

```

Sur PowerShell :

```powershell
New-Item -ItemType Directory -Force backups
Copy-Item data/app.sqlite backups/app.before-lambda.sqlite

New-Item -ItemType Directory -Force export-lambda/data
Copy-Item data/app.sqlite export-lambda/data/app.sqlite

tar -czf spotify-curator-lambda-input.tar.gz export-lambda

```

---

## 9. Créer le compte Lambda Labs

Étapes :

```text
1. Créer un compte Lambda Cloud.
2. Ajouter un moyen de paiement.
3. Ajouter une clé SSH.
4. Créer un filesystem persistant.
5. Lancer une instance A6000 en attachant le filesystem.

```

---

## 10. Générer une clé SSH locale

Sur le PC local :

```bash
ssh-keygen -t ed25519 -C "lambda-spotify-curator"

```

Chemin recommandé :

```text
~/.ssh/lambda_spotify_curator

```

Afficher la clé publique :

```bash
cat ~/.ssh/lambda_spotify_curator.pub

```

Sur PowerShell :

```powershell
Get-Content $env:USERPROFILE\.ssh\lambda_spotify_curator.pub

```

Ajouter la clé publique dans Lambda Cloud :

```text
Lambda Cloud → SSH Keys → Add SSH Key

```

---

## 11. Créer le filesystem persistant Lambda

Dans Lambda Cloud :

```text
Storage → Create filesystem

```

Configuration recommandée :

```text
Name   : persistent-storage
Region : même région que l’instance GPU

```

Le filesystem sera monté sur l’instance sous :

```text
/lambda/nfs/persistent-storage

```

Créer ensuite l’arborescence projet :

```bash
mkdir -p /lambda/nfs/persistent-storage/spotify-curator
mkdir -p /lambda/nfs/persistent-storage/spotify-curator/backups
mkdir -p /lambda/nfs/persistent-storage/spotify-curator/models
mkdir -p /lambda/nfs/persistent-storage/spotify-curator/exports
mkdir -p /lambda/nfs/persistent-storage/spotify-curator/final-output

```

---

## 12. Lancer l’instance Lambda

Dans Lambda Cloud :

```text
Instances → Launch instance

```

Configuration recommandée :

```text
Instance type : 1x NVIDIA A6000
Image         : Lambda Stack ou GPU Base Ubuntu
SSH key       : lambda_spotify_curator
Filesystem    : persistent-storage
Region        : même région que le filesystem

```

Après création, récupérer l’adresse IP publique de l’instance.

---

## 13. Connexion SSH

Depuis le PC local :

```bash
ssh -i ~/.ssh/lambda_spotify_curator ubuntu@<LAMBDA_INSTANCE_IP>

```

PowerShell :

```powershell
ssh -i $env:USERPROFILE\.ssh\lambda_spotify_curator ubuntu@<LAMBDA_INSTANCE_IP>

```

Vérifier le GPU :

```bash
nvidia-smi

```

Vérifier Docker :

```bash
docker --version

```

Vérifier Docker Compose :

```bash
docker compose version

```

Si Docker Compose manque :

```bash
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

```

Ajouter l’utilisateur au groupe Docker si nécessaire :

```bash
sudo adduser "$(id -un)" docker
exec bash

```

Tester l’accès GPU Docker :

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

```

---

## 14. Cloner le projet

Sur l’instance Lambda :

```bash
cd /lambda/nfs/persistent-storage
git clone <REPO_GIT> spotify-curator
cd spotify-curator

```

Si le repository est privé, configurer SSH GitHub ou utiliser un token.

---

## 15. Transférer la base SQLite vers Lambda

Depuis le PC local :

```bash
scp -i ~/.ssh/lambda_spotify_curator \
  spotify-curator-lambda-input.tar.gz \
  ubuntu@<LAMBDA_INSTANCE_IP>:/lambda/nfs/persistent-storage/spotify-curator/

```

PowerShell :

```powershell
scp -i $env:USERPROFILE\.ssh\lambda_spotify_curator `
  spotify-curator-lambda-input.tar.gz `
  ubuntu@<LAMBDA_INSTANCE_IP>:/lambda/nfs/persistent-storage/spotify-curator/

```

Sur l’instance :

```bash
cd /lambda/nfs/persistent-storage/spotify-curator
tar -xzf spotify-curator-lambda-input.tar.gz

```

Créer le runtime local SSD :

```bash
mkdir -p /home/ubuntu/spotify-curator-runtime/data
mkdir -p /home/ubuntu/spotify-curator-runtime/logs
mkdir -p /home/ubuntu/spotify-curator-runtime/temp-audio

```

Copier SQLite vers le runtime local :

```bash
cp export-lambda/data/app.sqlite /home/ubuntu/spotify-curator-runtime/data/app.sqlite

```

Vérifier :

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "PRAGMA integrity_check;"

```

Résultat attendu :

```text
ok

```

---

## 16. Configurer `.env.lambda`

Créer un fichier :

```bash
nano .env.lambda

```

Contenu recommandé :

```env
APP_ENV=lambda
RUN_ENV=lambda

DATA_DIR=/app/data
SQLITE_PATH=/app/data/app.sqlite
MODELS_DIR=/app/models
LOG_DIR=/app/logs
TEMP_AUDIO_DIR=/app/temp-audio

ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_TF_DEVICE=gpu
ESSENTIA_TF_WARMUP=true

ESSENTIA_TF_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=2
AUDIO_DOWNLOADER_WORKERS=4
PREVIEW_RESOLVER_WORKERS=2

ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TF_BATCH_TIMEOUT_MS=1000

TF_FORCE_GPU_ALLOW_GROWTH=true
TF_CPP_MIN_LOG_LEVEL=1
TF_NUM_INTRAOP_THREADS=4
TF_NUM_INTEROP_THREADS=2
OMP_NUM_THREADS=4

NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

VITE_API_BASE_URL=http://localhost:8000

```

Pour benchmark 2 workers TensorFlow :

```env
ESSENTIA_TF_WORKERS=2
TF_NUM_INTRAOP_THREADS=2
TF_NUM_INTEROP_THREADS=1
OMP_NUM_THREADS=2

```

---

## 17. Créer `docker-compose.gpu.yml`

Créer le fichier :

```bash
nano docker-compose.gpu.yml

```

Contenu type :

```yaml
services:
  essentia-tensorflow-worker:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      NVIDIA_VISIBLE_DEVICES: all
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
      ESSENTIA_TF_DEVICE: gpu
      ESSENTIA_TF_WARMUP: "true"
      TF_FORCE_GPU_ALLOW_GROWTH: "true"

```

Si Docker Compose ne duplique pas les workers via variable, utiliser une seconde définition ou `--scale` au lancement :

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  -f docker-compose.lambda.yml \
  --env-file .env.lambda \
  --profile audio \
  --profile advanced-analysis \
  up -d --scale essentia-tensorflow-worker=2

```

Attention : commencer par `--scale essentia-tensorflow-worker=1`.

---

## 18. Créer `docker-compose.lambda.yml`

Ce fichier adapte les volumes et les ports pour Lambda.

```yaml
services:
  core-api:
    env_file:
      - .env.lambda
    volumes:
      - /home/ubuntu/spotify-curator-runtime/data:/app/data
      - /home/ubuntu/spotify-curator-runtime/logs:/app/logs
      - /home/ubuntu/spotify-curator-runtime/temp-audio:/app/temp-audio
      - /lambda/nfs/persistent-storage/spotify-curator/models:/app/models
    ports:
      - "127.0.0.1:8000:8765"

  frontend-dev:
    profiles: ["lambda-ui"]
    env_file:
      - .env.lambda
    ports:
      - "127.0.0.1:5173:5173"
    environment:
      VITE_API_BASE_URL: http://localhost:8000

  audio-downloader:
    env_file:
      - .env.lambda
    volumes:
      - /home/ubuntu/spotify-curator-runtime/data:/app/data
      - /home/ubuntu/spotify-curator-runtime/logs:/app/logs
      - /home/ubuntu/spotify-curator-runtime/temp-audio:/app/temp-audio

  preview-resolver-worker:
    env_file:
      - .env.lambda
    volumes:
      - /home/ubuntu/spotify-curator-runtime/data:/app/data
      - /home/ubuntu/spotify-curator-runtime/logs:/app/logs

  essentia-lowlevel-worker:
    env_file:
      - .env.lambda
    volumes:
      - /home/ubuntu/spotify-curator-runtime/data:/app/data
      - /home/ubuntu/spotify-curator-runtime/logs:/app/logs
      - /home/ubuntu/spotify-curator-runtime/temp-audio:/app/temp-audio

  essentia-tensorflow-worker:
    env_file:
      - .env.lambda
    volumes:
      - /home/ubuntu/spotify-curator-runtime/data:/app/data
      - /home/ubuntu/spotify-curator-runtime/logs:/app/logs
      - /home/ubuntu/spotify-curator-runtime/temp-audio:/app/temp-audio
      - /lambda/nfs/persistent-storage/spotify-curator/models:/app/models

```

Adapter les noms de services aux noms réels du projet.

---

## 19. Build des images Docker

Depuis l’instance Lambda :

```bash
cd /lambda/nfs/persistent-storage/spotify-curator

```

Build :

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  -f docker-compose.lambda.yml \
  --env-file .env.lambda \
  --profile audio \
  --profile advanced-analysis \
  build

```

---

## 20. Vérifier TensorFlow GPU dans le conteneur

Commande :

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  -f docker-compose.lambda.yml \
  --env-file .env.lambda \
  --profile audio \
  --profile advanced-analysis \
  run --rm essentia-tensorflow-worker \
  python - <<'PY'
import tensorflow as tf
print("TensorFlow:", tf.__version__)
print("GPUs:", tf.config.list_physical_devices("GPU"))
PY

```

Résultat attendu :

```text
GPUs: [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]

```

Si le résultat est :

```text
GPUs: []

```

ne pas lancer l’analyse complète. Corriger l’image Docker GPU.

---

## 21. Lancer l’application

Démarrage avec 1 worker TensorFlow :

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  -f docker-compose.lambda.yml \
  --env-file .env.lambda \
  --profile audio \
  --profile advanced-analysis \
  --profile lambda-ui \
  up -d --scale essentia-tensorflow-worker=1

```

Vérifier :

```bash
docker compose ps

```

Logs du worker TensorFlow :

```bash
docker compose logs -f essentia-tensorflow-worker

```

Tester l’API :

```bash
curl http://localhost:8000/api/v1/health

```

Tester le frontend :

```bash
curl http://localhost:5173

```

---

## 22. Créer le tunnel SSH UI/API

Depuis le PC local, ouvrir un terminal et le laisser ouvert :

```bash
ssh -i ~/.ssh/lambda_spotify_curator \
  -L 5173:localhost:5173 \
  -L 8000:localhost:8000 \
  ubuntu@<LAMBDA_INSTANCE_IP>

```

PowerShell :

```powershell
ssh -i $env:USERPROFILE\.ssh\lambda_spotify_curator `
  -L 5173:localhost:5173 `
  -L 8000:localhost:8000 `
  ubuntu@<LAMBDA_INSTANCE_IP>

```

Ensuite, ouvrir sur le PC local :

```text
http://localhost:5173

```

L’UI appelle l’API via :

```text
http://localhost:8000

```

Ces deux ports sont redirigés vers l’instance Lambda via SSH.

---

## 23. Lancer un benchmark court

Avant d’analyser toute la bibliothèque, lancer un job de test sur 20 à 50 pistes.

Configuration :

```text
profile : phase6-recommended
only_missing : true
tensorflow : enabled
limit : 20 à 50 pistes si l’UI/API le permet

```

Surveiller GPU :

```bash
watch -n 1 nvidia-smi

```

Surveiller logs :

```bash
docker compose logs -f essentia-tensorflow-worker

```

Surveiller progression SQLite :

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "
SELECT stage_name, status, COUNT(*)
FROM job_items
GROUP BY stage_name, status
ORDER BY stage_name, status;
"

```

Mesurer les durées si les colonnes existent :

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "
SELECT stage_name,
       AVG(duration_ms) / 1000.0 AS avg_seconds,
       COUNT(*) AS n
FROM job_events
WHERE duration_ms IS NOT NULL
GROUP BY stage_name
ORDER BY avg_seconds DESC;
"

```

Adapter les noms de colonnes au schéma réel.

---

## 24. Tester 2 workers TensorFlow

Après validation avec 1 worker :

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  -f docker-compose.lambda.yml \
  --env-file .env.lambda \
  --profile audio \
  --profile advanced-analysis \
  up -d --scale essentia-tensorflow-worker=2

```

Avant de relancer, modifier `.env.lambda` :

```env
ESSENTIA_TF_WORKERS=2
TF_NUM_INTRAOP_THREADS=2
TF_NUM_INTEROP_THREADS=1
OMP_NUM_THREADS=2

```

Puis benchmark sur 20 à 50 pistes.

Comparer :

```text
1 worker :
- temps moyen par segment
- GPU utilization
- VRAM
- erreurs

2 workers :
- temps moyen par segment
- GPU utilization
- VRAM
- erreurs

```

Garder 2 workers seulement si :

```text
- throughput global meilleur ;
- pas d’OOM ;
- pas de saturation CPU ;
- pas de hausse importante des failures.

```

---

## 25. Lancer l’analyse complète

Depuis l’UI :

```text
Features → Audio analysis → Advanced

```

Paramètres recommandés :

```text
profile : phase6-recommended
only_missing : true
tensorflow : enabled
mode : recommended ou fast

```

Éviter `phase6-full` sur toute la bibliothèque au premier passage.

---

## 26. Suivi de l’analyse complète

Commandes utiles :

### GPU

```bash
watch -n 1 nvidia-smi

```

### Logs

```bash
docker compose logs -f essentia-tensorflow-worker

```

### Workers

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "
SELECT worker_id, stage_name, status, last_seen_at
FROM worker_heartbeats
ORDER BY last_seen_at DESC;
"

```

### Jobs

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "
SELECT stage_name, status, COUNT(*)
FROM job_items
GROUP BY stage_name, status
ORDER BY stage_name, status;
"

```

### Couverture embeddings

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "
SELECT COUNT(*) FROM track_embeddings;
"

```

### Couverture features avancées

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "
SELECT COUNT(*) FROM track_advanced_features;
"

```

Adapter les noms de tables si nécessaire.

---

## 27. Sauvegardes intermédiaires

Créer un script `scripts/lambda/backup-runtime-sqlite.sh` :

```bash
#!/usr/bin/env bash
set -euo pipefail

SRC="/home/ubuntu/spotify-curator-runtime/data/app.sqlite"
DST_DIR="/lambda/nfs/persistent-storage/spotify-curator/backups"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DST_DIR"

sqlite3 "$SRC" "PRAGMA wal_checkpoint(FULL);"
sqlite3 "$SRC" "PRAGMA integrity_check;"

cp "$SRC" "$DST_DIR/app.${TS}.sqlite"

echo "Backup created: $DST_DIR/app.${TS}.sqlite"

```

Lancer périodiquement :

```bash
bash scripts/lambda/backup-runtime-sqlite.sh

```

---

## 28. Arrêt propre après analyse

Arrêter les services :

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  -f docker-compose.lambda.yml \
  --env-file .env.lambda \
  --profile audio \
  --profile advanced-analysis \
  down

```

Checkpoint SQLite :

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "PRAGMA wal_checkpoint(FULL);"
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "PRAGMA integrity_check;"

```

Résultat attendu :

```text
ok

```

Créer l’archive finale :

```bash
cd /lambda/nfs/persistent-storage/spotify-curator

mkdir -p final-output
cp /home/ubuntu/spotify-curator-runtime/data/app.sqlite final-output/app.sqlite

tar -czf spotify-curator-lambda-output.tar.gz final-output

```

---

## 29. Récupérer la base analysée

Depuis le PC local :

```bash
scp -i ~/.ssh/lambda_spotify_curator \
  ubuntu@<LAMBDA_INSTANCE_IP>:/lambda/nfs/persistent-storage/spotify-curator/spotify-curator-lambda-output.tar.gz \
  .

```

PowerShell :

```powershell
scp -i $env:USERPROFILE\.ssh\lambda_spotify_curator `
  ubuntu@<LAMBDA_INSTANCE_IP>:/lambda/nfs/persistent-storage/spotify-curator/spotify-curator-lambda-output.tar.gz `
  .

```

Extraire :

```bash
tar -xzf spotify-curator-lambda-output.tar.gz

```

Sauvegarder la base locale actuelle :

```bash
cp data/app.sqlite data/app.before-lambda-result.sqlite

```

Remplacer :

```bash
cp final-output/app.sqlite data/app.sqlite

```

Vérifier :

```bash
sqlite3 data/app.sqlite "PRAGMA integrity_check;"

```

Relancer le projet local :

```bash
docker compose up -d

```

---

## 30. Terminer l’instance Lambda

Après récupération de la base :

```text
Lambda Cloud → Instances → Terminate

```

Ne pas simplement éteindre la VM avec `shutdown`. Terminer l’instance depuis l’interface Lambda.

Garder le filesystem persistant tant que les résultats n’ont pas été vérifiés localement.

Après vérification locale :

```text
Lambda Cloud → Storage → supprimer le filesystem si inutile

```

---

## 31. Troubleshooting

### TensorFlow ne voit pas le GPU

Symptôme :

```text
GPUs: []

```

Vérifier :

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

```

Si Docker voit le GPU mais pas TensorFlow :

```text
- image TensorFlow CPU-only ;
- mauvaise version TensorFlow/CUDA ;
- dépendance `tensorflow[and-cuda]` absente ;
- image Docker non adaptée au GPU.

```

### Le GPU est visible mais peu utilisé

Causes possibles :

```text
- pas assez de jobs `essentia_tensorflow` en queue ;
- pipeline bloquée sur download ou low-level ;
- batch size 1 ;
- un seul worker mais preprocessing CPU lent ;
- workers trop peu nombreux ;
- modèles non GPU réellement ;
- graphes TensorFlow non utilisés par GPU.

```

Actions :

```text
1. Vérifier `job_items`.
2. Vérifier `nvidia-smi`.
3. Tester 2 workers TensorFlow.
4. Ajouter métriques par stage.
5. Vérifier les logs TensorFlow.

```

### OOM GPU

Symptôme :

```text
ResourceExhaustedError
CUDA out of memory
container killed

```

Actions :

```text
1. Revenir à 1 worker TensorFlow.
2. Réduire batch size.
3. Activer memory growth TensorFlow.
4. Réduire le profil modèle.
5. Éviter phase6-full.

```

### UI inaccessible

Vérifier côté Lambda :

```bash
curl http://localhost:5173
curl http://localhost:8000/api/v1/health

```

Vérifier tunnel local :

```bash
ssh -i ~/.ssh/lambda_spotify_curator \
  -L 5173:localhost:5173 \
  -L 8000:localhost:8000 \
  ubuntu@<LAMBDA_INSTANCE_IP>

```

Puis ouvrir :

```text
http://localhost:5173

```

### API inaccessible depuis UI

Vérifier que le frontend utilise :

```env
VITE_API_BASE_URL=http://localhost:8000

```

Avec le tunnel SSH, `localhost:8000` côté navigateur local est redirigé vers l’API distante.

### SQLite corrompue ou WAL non copié

Toujours faire :

```bash
sqlite3 app.sqlite "PRAGMA wal_checkpoint(FULL);"
sqlite3 app.sqlite "PRAGMA integrity_check;"

```

avant de copier la base.

---

## 32. Configuration finale recommandée

### Run complet stable

```env
ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_TF_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=2
AUDIO_DOWNLOADER_WORKERS=4
PREVIEW_RESOLVER_WORKERS=2
ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TF_WARMUP=true
TF_FORCE_GPU_ALLOW_GROWTH=true
TF_NUM_INTRAOP_THREADS=4
TF_NUM_INTEROP_THREADS=2
OMP_NUM_THREADS=4

```

### Run complet optimisé après benchmark

```env
ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_TF_WORKERS=2
ESSENTIA_LOWLEVEL_WORKERS=2
AUDIO_DOWNLOADER_WORKERS=4
PREVIEW_RESOLVER_WORKERS=2
ESSENTIA_TF_BATCH_SIZE=1
ESSENTIA_TF_WARMUP=true
TF_FORCE_GPU_ALLOW_GROWTH=true
TF_NUM_INTRAOP_THREADS=2
TF_NUM_INTEROP_THREADS=1
OMP_NUM_THREADS=2

```

### Run futur avec micro-batching

```env
ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_TF_WORKERS=1
ESSENTIA_TF_BATCH_SIZE=8
ESSENTIA_TF_BATCH_TIMEOUT_MS=1000
ESSENTIA_TF_WARMUP=true
TF_FORCE_GPU_ALLOW_GROWTH=true

```

Si micro-batching efficace :

```env
ESSENTIA_TF_WORKERS=1
ESSENTIA_TF_BATCH_SIZE=16

```

ou :

```env
ESSENTIA_TF_WORKERS=2
ESSENTIA_TF_BATCH_SIZE=8

```

à valider uniquement par benchmark.

---

## 33. Critères d’acceptation

Le mode Lambda est considéré valide si :

```text
- l’instance Lambda voit le GPU avec `nvidia-smi` ;
- Docker voit le GPU avec `docker run --gpus all ... nvidia-smi` ;
- le worker TensorFlow voit le GPU via TensorFlow ;
- l’API répond sur localhost:8000 ;
- l’UI répond sur localhost:5173 ;
- le tunnel SSH permet d’ouvrir l’UI depuis le PC local ;
- l’analyse test sur 20–50 pistes fonctionne ;
- `essentia_tensorflow` est plus rapide que localement ;
- la base SQLite finale passe `PRAGMA integrity_check`;
- la base récupérée localement fonctionne avec l’application.

```

---

## 34. Résumé opérationnel

```bash
# local
docker compose down
sqlite3 data/app.sqlite "PRAGMA wal_checkpoint(FULL);"
sqlite3 data/app.sqlite "PRAGMA integrity_check;"
tar -czf spotify-curator-lambda-input.tar.gz export-lambda

# lambda
ssh -i ~/.ssh/lambda_spotify_curator ubuntu@<IP>
git clone <REPO>
scp archive depuis local
cp app.sqlite vers /home/ubuntu/spotify-curator-runtime/data/app.sqlite
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml --env-file .env.lambda build
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml --env-file .env.lambda up -d --scale essentia-tensorflow-worker=1

# local tunnel
ssh -i ~/.ssh/lambda_spotify_curator -L 5173:localhost:5173 -L 8000:localhost:8000 ubuntu@<IP>

# navigateur local
http://localhost:5173

# après analyse
docker compose down
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "PRAGMA wal_checkpoint(FULL);"
sqlite3 /home/ubuntu/spotify-curator-runtime/data/app.sqlite "PRAGMA integrity_check;"
tar -czf spotify-curator-lambda-output.tar.gz final-output

# local récupération
scp ubuntu@<IP>:/lambda/nfs/persistent-storage/spotify-curator/spotify-curator-lambda-output.tar.gz .
tar -xzf spotify-curator-lambda-output.tar.gz
cp final-output/app.sqlite data/app.sqlite

```

