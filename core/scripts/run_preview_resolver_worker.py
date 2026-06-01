# #region agent log
import json
import os
import sys
import time


def _agent_worker_log(message: str, *, hypothesis_id: str, data: dict) -> None:
    payload = {
        "sessionId": "8df333",
        "hypothesisId": hypothesis_id,
        "location": "run_preview_resolver_worker.py:entry",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
        "runId": os.environ.get("DEBUG_RUN_ID", "pre-fix"),
    }
    line = json.dumps(payload) + "\n"
    for path in (os.environ.get("DEBUG_LOG_PATH", ""), "/app/data/debug-8df333.log"):
        if not path:
            continue
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)
            break
        except OSError:
            pass
    print(f"DEBUG-8df333 {message} {data}", flush=True)


_agent_worker_log(
    "worker entry sys.path",
    hypothesis_id="H1",
    data={"sys_path_head": sys.path[:5], "pythonpath": os.environ.get("PYTHONPATH")},
)
# #endregion

from app.workers.preview_resolver_worker import PreviewResolverWorker


def main() -> None:
    PreviewResolverWorker().run_forever()


if __name__ == "__main__":
    main()
