import time
from threading import Lock


_STATUS: dict[str, dict] = {}
_LOCK = Lock()


def init_request(request_id: str) -> None:
    with _LOCK:
        _STATUS[request_id] = {
            "request_id": request_id,
            "status": "running",
            "started_at": int(time.time() * 1000),
            "updated_at": int(time.time() * 1000),
            "steps": [],
        }


def add_step(
    request_id: str,
    stage: str,
    status: str,
    detail: str,
    elapsed_ms: int | None = None,
) -> None:
    with _LOCK:
        if request_id not in _STATUS:
            init_request(request_id)
        _STATUS[request_id]["steps"].append(
            {
                "stage": stage,
                "status": status,
                "detail": detail,
                "elapsed_ms": elapsed_ms,
            }
        )
        _STATUS[request_id]["updated_at"] = int(time.time() * 1000)


def mark_done(request_id: str) -> None:
    with _LOCK:
        if request_id in _STATUS:
            _STATUS[request_id]["status"] = "done"
            _STATUS[request_id]["updated_at"] = int(time.time() * 1000)


def mark_error(request_id: str, detail: str) -> None:
    with _LOCK:
        if request_id not in _STATUS:
            init_request(request_id)
        _STATUS[request_id]["status"] = "error"
        _STATUS[request_id]["updated_at"] = int(time.time() * 1000)
        _STATUS[request_id]["steps"].append(
            {
                "stage": "error",
                "status": "error",
                "detail": detail,
                "elapsed_ms": None,
            }
        )


def get_status(request_id: str) -> dict | None:
    with _LOCK:
        data = _STATUS.get(request_id)
        if not data:
            return None
        return {
            "request_id": data["request_id"],
            "status": data["status"],
            "started_at": data["started_at"],
            "updated_at": data["updated_at"],
            "steps": list(data["steps"]),
        }
