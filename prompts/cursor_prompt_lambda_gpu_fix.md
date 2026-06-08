# Prompt Cursor — Correction complète du mode Lambda GPU Spotify Curator

Contexte :
Nous avons tenté d’exécuter Spotify Curator sur une VM GPU Lambda Labs A100 pour accélérer le stage `essentia_tensorflow`. L’instance a été supprimée car la pipeline restait bloquée. Il faut corriger le projet avant de relancer une nouvelle VM.

Architecture projet :
- Frontend Svelte/Tauri, frontend web local possible via Vite.
- API Python core.
- SQLite locale.
- Docker Compose.
- Workers persistants :
  - audio-downloader
  - preview-resolver-worker
  - essentia-lowlevel-worker
  - essentia-tensorflow-worker
- Phase 6 validée localement.
- Stage bloquant : `essentia_tensorflow`.

Workflow Lambda cible :
- Ne pas envoyer la SQLite locale.
- Créer une base SQLite vierge sur Lambda.
- Se reconnecter à Spotify via tunnel SSH.
- Importer la bibliothèque Spotify dans la SQLite Lambda.
- Télécharger les modèles Essentia depuis l’UI.
- Exécuter l’analyse.
- Exporter uniquement la SQLite finale.

Mode UI recommandé :
- Frontend local sur le PC.
- API Lambda via tunnel SSH.
- Ne pas dépendre du frontend Lambda.

Tunnel :
```bash
ssh -N -i ~/.ssh/lambda_spotify_curator \
  -L 8000:127.0.0.1:8000 \
  ubuntu@<LAMBDA_INSTANCE_IP>
```

Frontend local :
```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
```

Spotify redirect URI :
```text
http://127.0.0.1:8000/api/v1/spotify/auth/callback
```

## Problèmes rencontrés à corriger

### 1. Docker permissions sur Lambda

Erreur :
```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

Correction documentation :
```bash
sudo usermod -aG docker ubuntu
exit
```
Puis reconnexion SSH.

Ne pas utiliser `sudo make` comme solution permanente.

### 2. Outils manquants sur l’hôte

Erreur :
```text
uv: command not found
```

Créer un script :
```text
scripts/lambda/install-host-prereqs.sh
```

Il doit installer :
```text
sqlite3
curl
ca-certificates
python3
python3-venv
python3-pip
build-essential
uv
```

Commande :
```bash
sudo apt-get update
sudo apt-get install -y sqlite3 curl ca-certificates python3 python3-venv python3-pip build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Frontend Lambda instable

Symptôme :
```text
curl: (56) Recv failure: Connection reset by peer
channel 3: open failed: connect failed: Connection refused
```

Décision :
- Ne plus faire du frontend Lambda le workflow principal.
- Documenter le frontend local comme workflow principal.
- Garder `frontend-dev` Lambda optionnel.

### 4. Confusion `tensorflow` vs `essentia-tensorflow`

Constat :
```bash
uv pip list | grep -i tensorflow
```
retourne :
```text
essentia-tensorflow 2.1b6.dev1389
```

Mais le worker affiche :
```text
TensorFlow import failed during device setup: No module named 'tensorflow'
```

À faire :
- Identifier le code qui fait `import tensorflow as tf`.
- Rendre cet import optionnel.
- Ne pas faire échouer le worker si Python `tensorflow` est absent.
- Ajouter un check séparé pour Essentia :
  - `import essentia`
  - `import essentia.standard as es`
  - vérifier `TensorflowPredictEffnetDiscogs`
  - vérifier `TensorflowPredict2D`
  - lancer `nvidia-smi`
- Ne pas installer `tensorflow[and-cuda]` sauf si le code utilise réellement l’API Python TensorFlow.

Créer :
```text
scripts/lambda/check_essentia_tf.py
```

### 5. Runtime CUDA/cuDNN incomplet

Erreur initiale :
```text
Cannot dlopen some GPU libraries.
Skipping registering GPU devices...
```

Patch temporaire qui doit être intégré proprement :
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

À faire proprement :
- Intégrer CUDA 11.2/cuDNN 8.1 dans l’image Docker GPU du worker TF.
- Ne pas dépendre d’un bind mount `/home/ubuntu/cuda112-libs` à long terme.
- Mettre `LD_LIBRARY_PATH` dans le Dockerfile GPU.

Exemple :
```dockerfile
RUN curl -L -o /tmp/Miniforge3.sh \
    https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
    && bash /tmp/Miniforge3.sh -b -p /opt/conda \
    && /opt/conda/bin/conda install -y -c conda-forge cudatoolkit=11.2 cudnn=8.1 \
    && /opt/conda/bin/conda clean -afy

ENV LD_LIBRARY_PATH=/opt/conda/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64
```

### 6. Warm-up MAEST cassé

Erreur :
```text
Warmup failed for genre_discogs519_maest_519l: 'output' is not a parameter of TensorflowPredict
essentia-tensorflow-worker warmup failed: Warmup incomplete for profile 'phase6-recommended'
```

Diagnostic :
- `TensorflowPredict2D` utilise `input` / `output`.
- `TensorflowPredict` utilise `inputs` / `outputs`.
- Le warm-up passe probablement `output=` à `TensorflowPredict`.

À corriger :
- Dans `_get_predictor` ou warm-up :
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

- Ne jamais passer `output=` à `TensorflowPredict`.
- Ajouter tests unitaires pour MAEST warm-up.
- Tant que ce n’est pas corrigé, `.env.lambda.example` doit mettre :
```env
ESSENTIA_TF_WARMUP=false
```

### 7. Restart loop du worker

Cause :
- warm-up MAEST échoue ;
- worker exit code 1 ;
- `restart: unless-stopped` relance en boucle ;
- jobs restent bloqués.

Correction :
- Warm-up ne doit pas tuer le worker pour des modèles optionnels.
- Ajouter classification required/optional dans le warm-up.
- Logguer les modèles manquants sans crash si optionnels.

### 8. Limite mémoire trop faible

Config observée :
```text
mem_limit: ~3.5 Go
```

C’est trop faible.

Correction Lambda :
```yaml
mem_limit: "24g"
memswap_limit: "24g"
shm_size: "4gb"
```

### 9. Variables d’environnement contradictoires

Plusieurs services affichent `ESSENTIA_TF_WARMUP`. Ce n’est pas forcément une erreur, mais il faut inspecter le bloc du service concerné.

Ajouter documentation :
```bash
docker compose ... config | sed -n '/essentia-tensorflow-worker:/,/preview-resolver-worker:/p'
docker compose ... exec essentia-tensorflow-worker env | grep -E "ESSENTIA_TF_WARMUP|ESSENTIA_TENSORFLOW_WORKERS|DATABASE_URL|LD_LIBRARY_PATH"
```

Valeurs Lambda sûres :
```env
ESSENTIA_TF_WARMUP=false
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2
```

### 10. Pipeline bloquée au stage `essentia_tensorflow`

Causes possibles :
- jobs laissés en `running` après crash ;
- jobs verrouillés ;
- max_attempts atteint ;
- worker regarde une autre SQLite ;
- mauvais stage_name ;
- pas assez de logs polling.

À implémenter :
1. Script diagnostic :
```bash
python -m core.scripts.inspect_jobs --stage essentia_tensorflow
```

Il doit afficher :
- status counts ;
- queued ;
- running ;
- failed ;
- locked_by ;
- locked_at ;
- attempts ;
- last_error ;
- pipeline_version ;
- exemples de jobs récents.

2. Script reset :
```bash
python -m core.scripts.reset_stale_jobs --stage essentia_tensorflow --older-than-minutes 30
```

3. Logs de polling dans le worker :
- SQLite path ;
- stage_name ;
- nombre queued ;
- nombre running ;
- nombre failed ;
- raison si aucun item pris ;
- item_id locké ;
- track_id ;
- segment_path ;
- missing segment file ;
- missing model ;
- attempts/max_attempts ;
- exception complète.

4. `ESSENTIA_TF_WARMUP=false` ne doit pas empêcher le traitement normal.

## Configuration Lambda cible

`.env.lambda.example` :

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

## Critères d’acceptation

- `docker run --rm --gpus all nvidia/cuda:... nvidia-smi` fonctionne.
- API Lambda répond sur `127.0.0.1:8000`.
- Frontend local se connecte via tunnel SSH.
- Spotify OAuth fonctionne avec `127.0.0.1`.
- Une base SQLite vierge peut être créée sur Lambda.
- Les modèles Essentia sont téléchargeables via UI.
- Worker TensorFlow démarre sans restart loop.
- Warm-up MAEST corrigé ou désactivé.
- CUDA/cuDNN GPU runtime intégré proprement.
- Worker traite au moins un job `essentia_tensorflow`.
- `nvidia-smi` montre un process pendant l’inférence.
- Jobs bloqués inspectables et réinitialisables.
- Export SQLite final fonctionne.
