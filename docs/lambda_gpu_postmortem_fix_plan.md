# Post-mortem Lambda GPU — problèmes rencontrés et plan de correction

## 1. Objectif du document

Ce document récapitule les problèmes rencontrés lors de l’exécution de Spotify Curator sur une VM GPU Lambda Labs, afin de fournir à Cursor un contexte clair pour corriger l’application et stabiliser le mode cloud GPU.

Le but initial était :

```text
- créer une base SQLite vierge sur Lambda ;
- se reconnecter à Spotify via tunnel SSH ;
- importer la bibliothèque Spotify ;
- télécharger les modèles Essentia depuis l’UI ;
- exécuter la pipeline audio avancée avec GPU ;
- récupérer uniquement la base SQLite finale analysée.
```

La VM Lambda utilisée était une instance NVIDIA A100. L’instance a été supprimée après plusieurs blocages, mais les logs permettent d’identifier plusieurs problèmes distincts.

---

## 2. Architecture Lambda cible attendue

Architecture souhaitée :

```text
VM Lambda GPU
├── Docker + NVIDIA Container Toolkit
├── Docker Compose
├── core-api              → 127.0.0.1:8000
├── workers audio
├── essentia-lowlevel-worker
├── essentia-tensorflow-worker GPU
├── SQLite active sur SSD local
│   └── /home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite
├── modèles Essentia sur filesystem persistant
│   └── /lambda/nfs/persistent-storage/spotify-curator/models
└── frontend local sur PC utilisateur
    └── VITE_API_BASE_URL=http://127.0.0.1:8000 via tunnel SSH
```

Le frontend distant Lambda n’est pas obligatoire. Le mode recommandé est :

```text
PC local frontend → tunnel SSH → API Lambda → SQLite Lambda + workers Lambda
```

Tunnel recommandé :

```bash
ssh -N -i ~/.ssh/lambda_spotify_curator \
  -L 8000:127.0.0.1:8000 \
  ubuntu@<LAMBDA_INSTANCE_IP>
```

Le port `5173` ne doit pas être forwardé si le frontend tourne localement sur le PC.

---

## 3. Problème 1 — permissions Docker sur Lambda

### Symptôme

Commande :

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Erreur :

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

### Cause

L’utilisateur `ubuntu` n’était pas membre du groupe `docker`.

### Correction

```bash
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker ubuntu
exit
```

Puis se reconnecter en SSH.

Vérification :

```bash
groups
docker ps
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

### À documenter

Ne pas utiliser `sudo make` ou `sudo docker compose` comme solution permanente. Cela peut créer des fichiers root-owned dans le repo et masquer les problèmes d’environnement.

---

## 4. Problème 2 — outils manquants sur l’hôte Lambda

### Symptôme

Le script benchmark échoue :

```text
scripts/lambda/benchmark-pipeline.sh: line 8: uv: command not found
```

### Cause

Le script `scripts/lambda/benchmark-pipeline.sh` s’exécute sur l’hôte Lambda et utilise directement `uv`, mais `uv` n’était pas installé sur la VM.

Le script dépend aussi de `sqlite3` pour les commandes de diagnostic/export.

### Correction immédiate

```bash
sudo apt-get update
sudo apt-get install -y sqlite3 curl ca-certificates python3 python3-venv python3-pip build-essential

curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

uv --version
sqlite3 --version
```

Si Python 3.11 est requis :

```bash
uv python install 3.11
```

### Correction projet recommandée

Éviter que les scripts Lambda critiques dépendent de `uv` installé sur l’hôte.

Deux options :

#### Option A — documenter les prérequis hôte

Ajouter un script :

```text
scripts/lambda/install-host-prereqs.sh
```

Qui installe :

```text
- sqlite3
- curl
- ca-certificates
- python3
- python3-venv
- python3-pip
- build-essential
- uv
```

#### Option B — exécuter le benchmark dans un conteneur

Modifier `benchmark-pipeline.sh` pour exécuter le script Python dans le conteneur `core-api` :

```bash
docker compose ... exec core-api \
  uv run python scripts/benchmark_advanced_pipeline.py ...
```

Cette option réduit les dépendances de l’hôte, mais impose que `core-api` contienne bien les scripts et l’environnement Python complet.

---

## 5. Problème 3 — frontend Lambda inaccessible

### Symptôme

Check services :

```text
Checking frontend http://127.0.0.1:5173 ...
curl: (56) Recv failure: Connection reset by peer
Frontend FAILED
```

Et côté tunnel SSH :

```text
channel 3: open failed: connect failed: Connection refused
```

### Causes probables

1. `frontend-dev` n’était pas lancé avec le profil `lambda-ui`.
2. Vite écoutait peut-être sur `localhost` dans le conteneur au lieu de `0.0.0.0`.
3. Le tunnel forwardait le port `5173` alors qu’aucun service n’écoutait sur `127.0.0.1:5173` côté VM.
4. Le frontend distant n’était pas nécessaire puisque l’option frontend local a été choisie.

### Correction recommandée

Ne pas lancer le frontend sur Lambda pour le workflow GPU. Utiliser le frontend local.

Sur la VM :

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.gpu.yml \
  -f docker-compose.lambda.yml \
  --env-file .env.lambda \
  --profile audio \
  --profile advanced-analysis \
  up -d
```

Sur le PC :

```bash
ssh -N -i ~/.ssh/lambda_spotify_curator \
  -L 8000:127.0.0.1:8000 \
  ubuntu@<LAMBDA_INSTANCE_IP>
```

Frontend local :

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
```

PowerShell :

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev -- --host 127.0.0.1 --port 5173
```

### Correction projet recommandée

Dans la documentation, faire du frontend local le mode principal.

Garder `frontend-dev` Lambda seulement comme option secondaire.

---

## 6. Problème 4 — Spotify OAuth via tunnel

### Contrainte

Pour OAuth, il faut utiliser explicitement :

```text
http://127.0.0.1:8000/api/v1/spotify/auth/callback
```

et pas :

```text
http://localhost:8000/...
```

### Configuration attendue

Dans Spotify Developer Dashboard :

```text
http://127.0.0.1:8000/api/v1/spotify/auth/callback
```

Dans `.env.lambda` :

```env
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/spotify/auth/callback
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Flux attendu

```text
1. Frontend local ouvert sur http://127.0.0.1:5173
2. Clic Connect Spotify
3. Frontend appelle API Lambda via http://127.0.0.1:8000
4. Spotify redirige vers http://127.0.0.1:8000/api/v1/spotify/auth/callback
5. Le tunnel SSH transfère la callback à l’API Lambda
6. L’API Lambda stocke les tokens dans la SQLite Lambda
```

---

## 7. Problème 5 — confusion entre `tensorflow` et `essentia-tensorflow`

### Symptôme

Check GPU :

```text
ModuleNotFoundError: No module named 'tensorflow'
```

Mais :

```bash
uv pip list | grep -i tensorflow
```

retourne :

```text
essentia-tensorflow 2.1b6.dev1389
```

### Diagnostic

`tensorflow` et `essentia-tensorflow` sont deux paquets différents.

```text
essentia-tensorflow
→ fournit les bindings Essentia avec algorithmes TensorFlowPredict, TensorflowPredict2D, etc.

tensorflow
→ API Python officielle TensorFlow, importée via `import tensorflow as tf`
```

Le projet utilise principalement les algorithmes Essentia TensorFlow. Le paquet Python `tensorflow` n’est pas forcément nécessaire à l’inférence.

### Problème projet identifié

Le code du worker effectue un setup GPU avec :

```python
import tensorflow as tf
```

Ce setup échoue si `tensorflow` n’est pas installé :

```text
TensorFlow import failed during device setup: No module named 'tensorflow'
```

### Correction recommandée

L’import Python TensorFlow doit être optionnel.

Comportement attendu :

```text
- Si `tensorflow` est absent :
  - logger un warning non bloquant ;
  - ne pas désactiver le worker ;
  - ne pas considérer cela comme échec GPU final.
- Vérifier Essentia TensorFlow séparément :
  - import essentia ;
  - présence TensorflowPredictEffnetDiscogs ;
  - présence TensorflowPredict2D ;
  - nvidia-smi accessible.
```

Ajouter un script :

```text
scripts/lambda/check_essentia_tf.py
```

Qui teste :

```python
import essentia
import essentia.standard as es

getattr(es, "TensorflowPredictEffnetDiscogs")
getattr(es, "TensorflowPredict2D")
```

Le script `check_tf_gpu.py` doit être renommé ou modifié pour ne pas supposer que `tensorflow` Python est obligatoire.

---

## 8. Problème 6 — runtime CUDA/cuDNN incomplet ou incompatible

### Symptôme initial

Logs TensorFlow C++ :

```text
Cannot dlopen some GPU libraries.
Skipping registering GPU devices...
```

### Diagnostic

Le conteneur voyait l’A100 via `nvidia-smi`, mais `LD_LIBRARY_PATH` ne contenait initialement que :

```text
/usr/local/nvidia/lib:/usr/local/nvidia/lib64
```

Cela expose les bibliothèques du driver, mais pas forcément les bibliothèques CUDA/cuDNN attendues par Essentia TensorFlow.

### Patch temporaire appliqué (résolu dans le repo)

**État actuel** : le target `gpu` de [`docker/essentia-tensorflow-worker/Dockerfile`](../docker/essentia-tensorflow-worker/Dockerfile) installe CUDA 11.2/cuDNN 8.1 via Miniforge/conda et définit `LD_LIBRARY_PATH`. Le montage volume hôte `/home/ubuntu/cuda112-libs` n’est plus nécessaire.

Installation manuelle historique (référence post-mortem VM) :

Installation de bibliothèques CUDA 11.2/cuDNN 8.1 via conda sur l’hôte :

```bash
cd ~
curl -L -o Miniforge3.sh \
  https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh

bash Miniforge3.sh -b -p "$HOME/miniforge3"

"$HOME/miniforge3/bin/conda" create -y \
  -p "$HOME/cuda112-libs" \
  -c conda-forge \
  cudatoolkit=11.2 \
  cudnn=8.1
```

Override Compose temporaire :

```yaml
services:
  essentia-tensorflow-worker:
    volumes:
      - /home/ubuntu/cuda112-libs:/opt/cuda112-libs:ro
    environment:
      LD_LIBRARY_PATH: /opt/cuda112-libs/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64
      NVIDIA_VISIBLE_DEVICES: all
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
      ESSENTIA_TF_DEVICE: gpu
      ESSENTIA_TF_WARMUP: "false"
      ESSENTIA_TENSORFLOW_WORKERS: "1"
      TF_FORCE_GPU_ALLOW_GROWTH: "true"
      TF_NUM_INTRAOP_THREADS: "4"
      TF_NUM_INTEROP_THREADS: "2"
      OMP_NUM_THREADS: "4"
    mem_limit: "24g"
    memswap_limit: "24g"
    shm_size: "4gb"
```

### Correction projet recommandée

Intégrer proprement ces bibliothèques dans l’image Docker GPU plutôt que via un bind mount hôte.

Option Dockerfile GPU :

```dockerfile
RUN apt-get update && apt-get install -y curl bzip2 ca-certificates && rm -rf /var/lib/apt/lists/*

RUN curl -L -o /tmp/Miniforge3.sh \
    https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
    && bash /tmp/Miniforge3.sh -b -p /opt/conda \
    && /opt/conda/bin/conda install -y -c conda-forge cudatoolkit=11.2 cudnn=8.1 \
    && /opt/conda/bin/conda clean -afy

ENV LD_LIBRARY_PATH=/opt/conda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64
```

Ce target doit être réservé au worker GPU.

---

## 9. Problème 7 — warm-up MAEST mal configuré

### Symptôme

Logs :

```text
TensorflowPredict: Successfully loaded graph file: `/app/models/essentia/feature-extractors/maest/discogs-maest-30s-pw-519l-2.pb`
Warmup failed for genre_discogs519_maest_519l: 'output' is not a parameter of TensorflowPredict
essentia-tensorflow-worker warmup failed: Warmup incomplete for profile 'phase6-recommended': missing predictors for ['genre_discogs519_maest_519l']
essentia-tensorflow-worker exited with code 1 (restarting)
```

### Diagnostic

Le warm-up traite probablement MAEST comme un modèle `TensorflowPredict2D`.

Or :

```text
TensorflowPredict2D utilise :
- input
- output

TensorflowPredict utilise :
- inputs
- outputs
```

Le warm-up passe probablement :

```python
TensorflowPredict(output=...)
```

alors qu’il faut :

```python
TensorflowPredict(outputs=[...])
```

### Correction immédiate

Désactiver le warm-up Lambda :

```env
ESSENTIA_TF_WARMUP=false
```

### Correction propre

Modifier `_get_predictor` ou la logique de warm-up :

```python
if algo_name == "TensorflowPredict2D":
    kwargs = {
        "graphFilename": graph,
        "input": input_node,
        "output": output_node,
    }

elif algo_name == "TensorflowPredict":
    kwargs = {
        "graphFilename": graph,
        "inputs": [input_node] if isinstance(input_node, str) else input_node,
        "outputs": [output_node] if isinstance(output_node, str) else output_node,
    }
```

Ne jamais passer `output=` à `TensorflowPredict`.

### Correction de robustesse

Le warm-up ne doit pas faire crasher le worker si un modèle optionnel échoue.

Comportement attendu :

```text
- Warm-up EffNet échoue → échec critique si EffNet obligatoire.
- Warm-up têtes optionnelles échoue → warning.
- Warm-up MAEST échoue → warning si le modèle est optionnel, ou désactivation contrôlée du genre MAEST.
- Le worker ne doit pas entrer en restart loop.
```

---

## 10. Problème 8 — variables d’environnement contradictoires dans Compose

### Symptôme

`docker compose config | grep` affiche plusieurs fois :

```text
ESSENTIA_TF_WARMUP: "false"
ESSENTIA_TF_WARMUP: "true"
ESSENTIA_TENSORFLOW_WORKERS: "1"
```

### Diagnostic

Le grep global affiche les variables de tous les services. Ce n’est pas forcément une erreur.

Mais un override Compose peut surcharger la valeur pour un service précis.

Le fichier temporaire `docker-compose.lambda.cuda112.yml` contenait initialement :

```yaml
ESSENTIA_TF_WARMUP: "true"
```

alors que `.env.lambda` contenait :

```env
ESSENTIA_TF_WARMUP=false
```

### Correction

Toujours inspecter le service ciblé :

```bash
docker compose ... config | sed -n '/essentia-tensorflow-worker:/,/preview-resolver-worker:/p'
```

Et vérifier dans le conteneur :

```bash
docker compose ... exec essentia-tensorflow-worker \
  bash -lc 'env | grep -E "ESSENTIA_TF_WARMUP|ESSENTIA_TENSORFLOW_WORKERS|DATABASE_URL|LD_LIBRARY_PATH"'
```

### Recommandation

Pour Lambda, la valeur finale doit être :

```env
ESSENTIA_TF_WARMUP=false
ESSENTIA_TENSORFLOW_WORKERS=1
```

jusqu’à correction du warm-up MAEST.

---

## 11. Problème 9 — limite mémoire trop faible

### Symptôme potentiel

La config effective montrait :

```text
mem_limit: ~3.5 Go
```

### Diagnostic

C’est trop faible pour un worker Essentia TensorFlow chargé avec :

```text
- EffNet ;
- MAEST ;
- plusieurs classification heads ;
- décodage audio ;
- caches ;
- runtime TensorFlow C++.
```

### Correction

Pour Lambda A100 :

```yaml
services:
  essentia-tensorflow-worker:
    mem_limit: "24g"
    memswap_limit: "24g"
    shm_size: "4gb"
```

### Recommandation workers

Tant que le mode GPU n’est pas validé :

```env
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2
```

Tester 2 workers uniquement après :

```text
- plus aucun restart ;
- GPU visible dans nvidia-smi pendant l’analyse ;
- pas de blocage job_items ;
- throughput 1 worker mesuré.
```

---

## 12. Problème 10 — pipeline bloquée au stage `essentia_tensorflow`

### Symptôme

La pipeline reste bloquée au stage :

```text
essentia_tensorflow
```

Le worker est démarré mais silencieux.

### Causes probables

1. Le worker a crashé auparavant et a laissé des `job_items` en `running`, `processing` ou `leased`.
2. Les jobs ont atteint `max_attempts`.
3. Le worker regarde la mauvaise SQLite.
4. Le worker ne poll pas les bons `stage_name`.
5. Le worker ne log pas suffisamment la boucle de polling.
6. Le worker est tué par limite mémoire.
7. La config `ESSENTIA_TF_WARMUP=false` bloque accidentellement le runner si le code lie warm-up et initialisation.

### Diagnostics nécessaires

#### Vérifier jobs

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite "
SELECT stage_name, status, COUNT(*)
FROM job_items
GROUP BY stage_name, status
ORDER BY stage_name, status;
"
```

#### Vérifier les jobs TensorFlow

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite "
SELECT id, stage_name, status, attempts, locked_by, locked_at, last_error
FROM job_items
WHERE stage_name LIKE '%tensorflow%'
ORDER BY updated_at DESC
LIMIT 50;
"
```

#### Vérifier schéma

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite "
PRAGMA table_info(job_items);
"
```

#### Réinitialiser les jobs bloqués

Faire backup avant :

```bash
sqlite3 /home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite "
PRAGMA wal_checkpoint(FULL);
.backup '/lambda/nfs/persistent-storage/spotify-curator/backups/before-reset-tf-jobs.sqlite'
"
```

Puis reset :

```sql
UPDATE job_items
SET status='queued',
    locked_by=NULL,
    locked_at=NULL,
    last_error=NULL
WHERE stage_name='essentia_tensorflow'
  AND status IN ('running', 'processing', 'leased');
```

Adapter selon le schéma réel.

### Correction projet recommandée

Ajouter une commande officielle :

```bash
python -m core.scripts.inspect_jobs --stage essentia_tensorflow
python -m core.scripts.reset_stale_jobs --stage essentia_tensorflow --older-than-minutes 30
```

Ajouter logs de polling worker :

```text
- SQLite path utilisé ;
- stage_name recherché ;
- nombre d’items queued ;
- nombre d’items running ;
- nombre d’items failed ;
- nombre d’items locked/stale ;
- raison si aucun item pris ;
- item_id locké ;
- track_id ;
- segment_path ;
- missing file ;
- missing model ;
- attempts/max_attempts ;
- pipeline_version.
```

---

## 13. Configuration Lambda recommandée après correction

### `.env.lambda`

```env
APP_ENV=lambda
RUN_ENV=lambda

DATABASE_URL=sqlite:////app/data/spotify_curator.sqlite
SQLITE_PATH=/app/data/spotify_curator.sqlite
SQLITE_JOURNAL_MODE=WAL

CACHE_DIR=/app/temp-audio
MODELS_DIR=/app/models
LOGS_DIR=/app/logs

SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/spotify/auth/callback
VITE_API_BASE_URL=http://127.0.0.1:8000

ESSENTIA_MODEL_PROFILE=phase6-recommended
ESSENTIA_MODELS_DIR=/app/models/essentia

ESSENTIA_TF_DEVICE=gpu
ESSENTIA_TF_WARMUP=false
ESSENTIA_TF_BATCH_SIZE=1

ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2

TF_FORCE_GPU_ALLOW_GROWTH=true
TF_NUM_INTRAOP_THREADS=4
TF_NUM_INTEROP_THREADS=2
OMP_NUM_THREADS=4

NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

### `docker-compose.lambda.cuda112.yml`

```yaml
services:
  essentia-tensorflow-worker:
    volumes:
      - /home/ubuntu/cuda112-libs:/opt/cuda112-libs:ro
    environment:
      LD_LIBRARY_PATH: /opt/cuda112-libs/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64
      NVIDIA_VISIBLE_DEVICES: all
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
      ESSENTIA_TF_DEVICE: gpu
      ESSENTIA_TF_WARMUP: "false"
      ESSENTIA_TENSORFLOW_WORKERS: "1"
      TF_FORCE_GPU_ALLOW_GROWTH: "true"
      TF_NUM_INTRAOP_THREADS: "4"
      TF_NUM_INTEROP_THREADS: "2"
      OMP_NUM_THREADS: "4"
    mem_limit: "24g"
    memswap_limit: "24g"
    shm_size: "4gb"
```

À terme, intégrer CUDA112/cuDNN dans le Dockerfile GPU plutôt que via bind mount hôte.

---

## 14. Ordre de validation recommandé pour une future instance

1. Créer VM Lambda A100.
2. Installer prérequis hôte : Docker group, uv, sqlite3.
3. Cloner repo.
4. Créer SQLite vierge.
5. Lancer `core-api` seulement.
6. Ouvrir tunnel API uniquement.
7. Lancer frontend local.
8. Connexion Spotify OAuth.
9. Import Spotify.
10. Télécharger modèles Essentia depuis UI.
11. Lancer workers audio sans TF.
12. Vérifier segment download + lowlevel.
13. Lancer 1 worker TF avec `ESSENTIA_TF_WARMUP=false`.
14. Vérifier worker heartbeat.
15. Vérifier `job_items`.
16. Lancer 1 job TF.
17. Surveiller `nvidia-smi`.
18. Mesurer débit.
19. Tester 2 workers uniquement si 1 worker stable.

---

## 15. Critères d’acceptation pour Cursor

Le mode Lambda GPU est considéré corrigé si :

```text
- Docker GPU fonctionne avec nvidia-smi.
- L’API répond sur 127.0.0.1:8000.
- Le frontend local peut se connecter à l’API via tunnel SSH.
- Spotify OAuth fonctionne avec 127.0.0.1.
- Une base SQLite vierge Lambda peut être créée.
- Les modèles Essentia peuvent être téléchargés depuis l’UI.
- `essentia-tensorflow-worker` démarre sans restart loop.
- `ESSENTIA_TF_WARMUP=false` désactive uniquement le préchargement, pas le traitement.
- MAEST warm-up n’utilise plus `output=` avec TensorflowPredict.
- Le worker traite au moins un `job_item` `essentia_tensorflow`.
- Les jobs bloqués peuvent être inspectés et reset via commandes officielles.
- La limite mémoire TF est au moins 16–24 Go sur Lambda.
- L’export final SQLite fonctionne et passe `PRAGMA integrity_check`.
```
