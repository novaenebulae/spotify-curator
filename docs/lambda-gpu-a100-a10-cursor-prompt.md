# Prompt Cursor — Mise à jour du mode Lambda GPU avec base vierge, Spotify OAuth tunnel, A100/A10

Contexte projet :
Le projet Spotify Curator utilise une architecture Tauri/Svelte + Python core + SQLite + Docker Compose. La phase 6 est validée. La pipeline audio avancée contient notamment le stage `essentia_tensorflow`, qui est le goulot principal. Les workers TensorFlow sont persistants, et le backend Essentia TensorFlow cache les predictors pendant la durée de vie du worker.

Contexte Lambda actuel :
Des fichiers Lambda existent déjà :
- `docs/20-lambda-gpu-cloud-analysis.md`
- `.env.lambda.example`
- `docker-compose.gpu.yml`
- `docker-compose.lambda.yml`
- `Makefile`
- `scripts/lambda/prepare-runtime.sh`
- `scripts/lambda/restore-input.sh`
- `scripts/lambda/backup-runtime-sqlite.sh`
- `scripts/lambda/export-final-sqlite.sh`
- `scripts/lambda/check_tf_gpu.py`
- `scripts/lambda/check-services.sh`
- `scripts/lambda/benchmark-pipeline.sh`

Rectification fonctionnelle :
Le nouveau workflow Lambda ne doit plus supposer qu’une base SQLite locale est envoyée vers Lambda. Le but est maintenant :
1. créer une base SQLite vierge directement sur Lambda ;
2. se reconnecter à Spotify via l’UI et un tunnel SSH ;
3. importer la bibliothèque Spotify dans la base Lambda ;
4. télécharger les modèles Essentia depuis l’UI sur la VM Lambda ;
5. lancer l’analyse ;
6. récupérer uniquement la base SQLite finale.

Important :
`restore-input.sh` devient un script optionnel/legacy pour restaurer une base existante. Il ne doit plus être le chemin principal de la documentation.

Objectifs d’implémentation :

## 1. Ajouter `scripts/lambda/init-empty-db.sh`

Créer un script qui initialise une base SQLite vierge sur Lambda.

Chemin cible :
`/home/ubuntu/spotify-curator-runtime/data/spotify_curator.sqlite`

Comportement :
- créer les dossiers runtime si absents ;
- refuser d’écraser une base existante par défaut ;
- option `--force` pour supprimer la base existante ;
- option `--backup-existing` pour sauvegarder l’existante avant recréation ;
- créer la base via le mécanisme normal du projet :
  - soit `uv run alembic upgrade head` dans `core`,
  - soit un script Python existant d’init DB,
  - soit le démarrage contrôlé de `core-api` si c’est la méthode officiellement supportée ;
- exécuter `PRAGMA integrity_check`;
- afficher clairement le chemin de la DB créée.

Exemple d’usage attendu :
```bash
bash scripts/lambda/prepare-runtime.sh
bash scripts/lambda/init-empty-db.sh
```

## 2. Mettre à jour `.env.lambda.example`

Changer les valeurs par défaut pour le nouveau workflow.

Valeurs critiques :
```env
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/spotify/auth/callback
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Ne pas utiliser `localhost` pour Spotify OAuth. Utiliser `127.0.0.1`.

Configuration workers recommandée par défaut :
```env
ESSENTIA_TENSORFLOW_WORKERS=1
ESSENTIA_LOWLEVEL_WORKERS=1
AUDIO_DOWNLOAD_WORKERS=2
PREVIEW_RESOLVER_WORKERS=1
AUDIO_DOWNLOAD_CONCURRENCY=2
```

Ajouter sections commentées :

A100 optimisé :
```env
# A100 optimized after benchmark:
# ESSENTIA_TENSORFLOW_WORKERS=2
# TF_NUM_INTRAOP_THREADS=2
# TF_NUM_INTEROP_THREADS=1
# OMP_NUM_THREADS=2
```

A100 80GB expérimental :
```env
# A100 80GB experimental only:
# ESSENTIA_TENSORFLOW_WORKERS=3
# TF_NUM_INTRAOP_THREADS=2
# TF_NUM_INTEROP_THREADS=1
# OMP_NUM_THREADS=2
```

A10 :
```env
# A10 recommended:
# ESSENTIA_TENSORFLOW_WORKERS=1
# ESSENTIA_LOWLEVEL_WORKERS=1
# AUDIO_DOWNLOAD_WORKERS=2
# PREVIEW_RESOLVER_WORKERS=1
# AUDIO_DOWNLOAD_CONCURRENCY=2
```

## 3. Mettre à jour `Makefile`

Ajouter :
```makefile
lambda-init-empty-db:
	bash scripts/lambda/init-empty-db.sh
```

Ajouter des cibles explicites :

```makefile
lambda-up-a100:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=2 \
		--scale preview-resolver-worker=1 \
		--scale essentia-lowlevel-worker=1 \
		--scale essentia-tensorflow-worker=1

lambda-up-a100-tf2:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=2 \
		--scale preview-resolver-worker=1 \
		--scale essentia-lowlevel-worker=1 \
		--scale essentia-tensorflow-worker=2

lambda-up-a10:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=2 \
		--scale preview-resolver-worker=1 \
		--scale essentia-lowlevel-worker=1 \
		--scale essentia-tensorflow-worker=1
```

Conserver `lambda-up` comme alias stable vers la configuration sûre.

## 4. Vérifier `docker-compose.lambda.yml`

S’assurer que :
- `core-api` est bindé sur `127.0.0.1:8000:8765`;
- `frontend-dev` est bindé sur `127.0.0.1:5173:5173`;
- `frontend-dev` utilise `VITE_API_BASE_URL=http://127.0.0.1:8000`;
- les modèles sont montés depuis `/lambda/nfs/persistent-storage/spotify-curator/models:/app/models`;
- la base active est sur `/home/ubuntu/spotify-curator-runtime/data:/app/data`.

## 5. Mettre à jour `scripts/lambda/check-services.sh`

Vérifier :
```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:5173
```

Ne pas utiliser `localhost` dans la documentation principale si cela peut créer de la confusion avec Spotify OAuth.

## 6. Documenter Spotify OAuth via tunnel SSH

Mettre à jour `docs/20-lambda-gpu-cloud-analysis.md`.

Le tunnel recommandé :
```bash
ssh -i ~/.ssh/lambda_spotify_curator \
  -L 5173:127.0.0.1:5173 \
  -L 8000:127.0.0.1:8000 \
  ubuntu@<LAMBDA_INSTANCE_IP>
```

URL UI :
```text
http://127.0.0.1:5173
```

URL API vue par le navigateur :
```text
http://127.0.0.1:8000
```

Redirect URI à configurer dans Spotify Developer Dashboard :
```text
http://127.0.0.1:8000/api/v1/spotify/auth/callback
```

Expliquer le flux :
- Spotify redirige vers `127.0.0.1:8000`;
- le tunnel SSH transfère la callback vers l’API Lambda ;
- l’API Lambda échange le code OAuth ;
- les tokens sont stockés dans la SQLite Lambda.

## 7. Documenter téléchargement des modèles Essentia depuis l’UI

Mettre à jour la documentation :
- ne plus demander de copier les modèles depuis le PC ;
- les modèles doivent être téléchargés depuis l’UI sur Lambda ;
- chemin persistant :
  `/lambda/nfs/persistent-storage/spotify-curator/models`
- montage conteneur :
  `/app/models`
- profil recommandé :
  `phase6-recommended`
- éviter `phase6-full` au premier run complet.

## 8. Documenter A100 vs A10

Ajouter une section :
- A100 recommandé ;
- A10 fallback ;
- A100 40GB : 1 worker stable, 2 workers recommandé après benchmark, 3 déconseillé ;
- A100 80GB : 1 worker stable, 2 workers recommandé, 3 expérimental ;
- A10 24GB : 1 worker recommandé, 2 expérimental, 3+ déconseillé.

Expliquer que 4 workers download est probablement trop haut si le goulot est TensorFlow. Recommandation par défaut :
```env
AUDIO_DOWNLOAD_WORKERS=2
AUDIO_DOWNLOAD_CONCURRENCY=2
```

Monter à 4 uniquement si le GPU attend les segments.

## 9. Mettre à jour le workflow principal de la doc

Nouveau workflow :
```text
Lambda:
1. créer instance A100 ou A10
2. cloner repo
3. cp .env.lambda.example .env.lambda
4. renseigner SPOTIFY_CLIENT_ID
5. prepare-runtime.sh
6. init-empty-db.sh
7. make lambda-build
8. make lambda-check-gpu
9. make lambda-up-a100 ou make lambda-up-a10
10. ouvrir tunnel SSH
11. accéder à http://127.0.0.1:5173
12. connecter Spotify
13. importer bibliothèque
14. télécharger modèles Essentia depuis l’UI
15. benchmark 20–50 pistes
16. lancer analyse complète
17. make lambda-export
18. scp archive finale
```

## 10. Conserver le workflow d’import SQLite comme option legacy

Ne pas supprimer `restore-input.sh`, mais le documenter comme :
```text
Optionnel : restaurer une base existante ou reprendre un backup.
Non utilisé dans le workflow principal base vierge.
```

## 11. Tests et validation

Commandes attendues :
```bash
bash scripts/lambda/prepare-runtime.sh
bash scripts/lambda/init-empty-db.sh
make lambda-build
make lambda-check-gpu
make lambda-up-a100
bash scripts/lambda/check-services.sh
bash scripts/lambda/benchmark-pipeline.sh 30
make lambda-export
```

Critères d’acceptation :
- base SQLite vierge créée sur Lambda ;
- migrations appliquées ;
- `PRAGMA integrity_check` retourne `ok`;
- API accessible via `127.0.0.1:8000`;
- frontend accessible via `127.0.0.1:5173`;
- Spotify OAuth fonctionne via tunnel SSH ;
- tokens stockés dans la SQLite Lambda ;
- import Spotify fonctionne ;
- modèles Essentia téléchargeables via UI ;
- TensorFlow voit le GPU ;
- benchmark fonctionne sur A100 ou A10 ;
- export final produit `spotify_curator.sqlite`;
- workflow local existant non régressé.
