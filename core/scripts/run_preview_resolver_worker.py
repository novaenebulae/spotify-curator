#!/usr/bin/env python3
"""Entrypoint for preview-resolver-worker Docker service."""

from app.workers.preview_resolver_worker import PreviewResolverWorker


def main() -> None:
    PreviewResolverWorker().run_forever()


if __name__ == "__main__":
    main()
