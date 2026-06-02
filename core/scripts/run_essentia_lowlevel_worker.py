#!/usr/bin/env python3
"""Entrypoint for essentia-lowlevel-worker Docker service."""

from app.workers.essentia_lowlevel_worker import EssentiaLowlevelWorker


def main() -> None:
    EssentiaLowlevelWorker().run_forever()


if __name__ == "__main__":
    main()
