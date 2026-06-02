#!/usr/bin/env python3
"""Entrypoint for audio-downloader Docker worker."""

from app.workers.audio_downloader_worker import AudioDownloaderWorker


def main() -> None:
    AudioDownloaderWorker().run_forever()


if __name__ == "__main__":
    main()
