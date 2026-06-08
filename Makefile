COMPOSE_LAMBDA_API := docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml --env-file .env.lambda --profile audio --profile advanced-analysis
COMPOSE_LAMBDA_UI := $(COMPOSE_LAMBDA_API) --profile lambda-ui
COMPOSE_LAMBDA := $(COMPOSE_LAMBDA_API)

.PHONY: lambda-build lambda-init-empty-db lambda-up lambda-up-tf1 lambda-up-tf2 \
	lambda-up-a100 lambda-up-a100-tf2 lambda-up-a100-ui lambda-up-a10 \
	lambda-down lambda-check-gpu lambda-backup lambda-export lambda-logs-tf

lambda-build:
	$(COMPOSE_LAMBDA) build

lambda-init-empty-db:
	bash scripts/lambda/init-empty-db.sh

lambda-up: lambda-up-a100

lambda-up-tf1: lambda-up-a100

lambda-up-tf2: lambda-up-a100-tf2

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

lambda-up-a100-ui:
	$(COMPOSE_LAMBDA_UI) up -d --scale audio-downloader=2 \
		--scale preview-resolver-worker=1 \
		--scale essentia-lowlevel-worker=1 \
		--scale essentia-tensorflow-worker=1

lambda-up-a10:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=2 \
		--scale preview-resolver-worker=1 \
		--scale essentia-lowlevel-worker=1 \
		--scale essentia-tensorflow-worker=1

lambda-down:
	$(COMPOSE_LAMBDA) down

lambda-check-gpu:
	$(COMPOSE_LAMBDA) run --rm -e REQUIRE_GPU=true essentia-tensorflow-worker \
		uv run python scripts/lambda/check_essentia_tf.py

lambda-backup:
	bash scripts/lambda/backup-runtime-sqlite.sh

lambda-export:
	bash scripts/lambda/export-final-sqlite.sh

lambda-logs-tf:
	$(COMPOSE_LAMBDA) logs -f essentia-tensorflow-worker
