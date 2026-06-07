COMPOSE_LAMBDA := docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml --env-file .env.lambda --profile audio --profile advanced-analysis --profile lambda-ui

.PHONY: lambda-build lambda-up lambda-up-tf1 lambda-up-tf2 lambda-down lambda-check-gpu lambda-backup lambda-export lambda-logs-tf

lambda-build:
	$(COMPOSE_LAMBDA) build

lambda-up: lambda-up-tf1

lambda-up-tf1:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=$${AUDIO_DOWNLOAD_WORKERS:-4} \
		--scale preview-resolver-worker=$${PREVIEW_RESOLVER_WORKERS:-2} \
		--scale essentia-lowlevel-worker=$${ESSENTIA_LOWLEVEL_WORKERS:-2} \
		--scale essentia-tensorflow-worker=1

lambda-up-tf2:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=$${AUDIO_DOWNLOAD_WORKERS:-4} \
		--scale preview-resolver-worker=$${PREVIEW_RESOLVER_WORKERS:-2} \
		--scale essentia-lowlevel-worker=$${ESSENTIA_LOWLEVEL_WORKERS:-2} \
		--scale essentia-tensorflow-worker=2

lambda-down:
	$(COMPOSE_LAMBDA) down

lambda-check-gpu:
	$(COMPOSE_LAMBDA) run --rm -e REQUIRE_GPU=true essentia-tensorflow-worker \
		uv run python scripts/lambda/check_tf_gpu.py

lambda-backup:
	bash scripts/lambda/backup-runtime-sqlite.sh

lambda-export:
	bash scripts/lambda/export-final-sqlite.sh

lambda-logs-tf:
	$(COMPOSE_LAMBDA) logs -f essentia-tensorflow-worker
