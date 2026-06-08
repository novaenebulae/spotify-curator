COMPOSE_LAMBDA_API := docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.lambda.yml --env-file .env.lambda --profile audio --profile advanced-analysis
COMPOSE_LAMBDA_UI := $(COMPOSE_LAMBDA_API) --profile lambda-ui
COMPOSE_LAMBDA := $(COMPOSE_LAMBDA_API)

.PHONY: lambda-build lambda-init-empty-db lambda-up lambda-up-tf1 lambda-up-tf2 \
	lambda-up-a100 lambda-up-a100-tf2 lambda-up-a10-tuned lambda-up-a10-max lambda-up-a10-ultra lambda-up-a10-download-max lambda-up-a10-tf-focus lambda-up-a10-balanced lambda-up-a10-tf-lean lambda-up-a10-balanced-tf4 lambda-up-a10-stable-tf4 lambda-retry-pipeline-failed lambda-up-a100-ui lambda-up-a10 \
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

# A10 24 GB after benchmark: 2 TF (exp.) + 2 lowlevel + 2 preview + 3 downloaders.
# See docs/20-lambda-gpu-cloud-analysis.md §3 (A10 — 2 workers expérimentaux).
lambda-up-a10-tuned:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=3 \
		--scale preview-resolver-worker=2 \
		--scale essentia-lowlevel-worker=2 \
		--scale essentia-tensorflow-worker=2

# A10 24 GB max throughput: feed GPU when segment_download is the bottleneck (30 vCPU VM).
lambda-up-a10-max:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=6 \
		--scale preview-resolver-worker=2 \
		--scale essentia-lowlevel-worker=4 \
		--scale essentia-tensorflow-worker=2

# A10 24 GB ultra: 8 DL + 8 lowlevel + 3 TF (VRAM ~9 GB); lambda.yml raises CPU/mem per worker.
lambda-up-a10-ultra:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=8 \
		--scale preview-resolver-worker=2 \
		--scale essentia-lowlevel-worker=8 \
		--scale essentia-tensorflow-worker=3

# A10 download-max: segment_download is the bottleneck (deezer fast + yt-dlp slow).
# 12 DL + 3 preview + 5 lowlevel + 3 TF — fewer lowlevel replicas reduce SQLite lock contention.
lambda-up-a10-download-max:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=12 \
		--scale preview-resolver-worker=3 \
		--scale essentia-lowlevel-worker=5 \
		--scale essentia-tensorflow-worker=3

# A10 TF-focus: TF backlog + SQLite lock fix — feed GPU, limit DB writers (4 DL + 4 LL + 3 TF).
lambda-up-a10-tf-focus:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=4 \
		--scale preview-resolver-worker=2 \
		--scale essentia-lowlevel-worker=4 \
		--scale essentia-tensorflow-worker=3

# A10 balanced: 8 DL + 4 LL + 3 TF — feed download after SQLite fixes, keep TF fed.
lambda-up-a10-balanced:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=8 \
		--scale preview-resolver-worker=2 \
		--scale essentia-lowlevel-worker=4 \
		--scale essentia-tensorflow-worker=3

# A10 TF-lean: fewer SQLite writers (6 DL + 3 LL) + 4 TF workers on A10 24GB (~12 GB VRAM).
lambda-up-a10-tf-lean:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=6 \
		--scale preview-resolver-worker=2 \
		--scale essentia-lowlevel-worker=3 \
		--scale essentia-tensorflow-worker=4

# A10 balanced-tf4: 8 DL + 3 LL + 4 TF — keep download throughput, add TF worker, fewer LL writers.
lambda-up-a10-balanced-tf4:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=8 \
		--scale preview-resolver-worker=2 \
		--scale essentia-lowlevel-worker=3 \
		--scale essentia-tensorflow-worker=4

# A10 stable-tf4: fewer SQLite writers (6 DL + 1 preview + 3 LL + 4 TF) for long runs.
lambda-up-a10-stable-tf4:
	$(COMPOSE_LAMBDA) up -d --scale audio-downloader=6 \
		--scale preview-resolver-worker=1 \
		--scale essentia-lowlevel-worker=3 \
		--scale essentia-tensorflow-worker=4

lambda-retry-pipeline-failed:
	$(COMPOSE_LAMBDA) exec -T core-api uv run python scripts/retry_pipeline_failed.py $(JOB_ID)

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
