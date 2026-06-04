#!/usr/bin/env python3
"""Entrypoint for essentia-tensorflow-worker Docker service."""

from app.workers.essentia_tensorflow_worker import EssentiaTensorflowWorker


def main() -> None:
    EssentiaTensorflowWorker().run_forever()


if __name__ == "__main__":
    main()
