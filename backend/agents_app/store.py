import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

DATA_DIR = Path(
    os.environ.get("GIVA_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data"))
)
TEMPLATES_PATH = DATA_DIR / "templates.json"

_lock = Lock()


def _ensure_store() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TEMPLATES_PATH.exists():
        TEMPLATES_PATH.write_text("[]", encoding="utf-8")


def add_template(channel: str, name: str, brand_name: str, payload: dict) -> dict:
    _ensure_store()
    with _lock:
        templates = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
        record = {
            "id": str(uuid.uuid4()),
            "channel": channel,
            "name": name,
            "brand": brand_name,
            "payload": payload,
            "status": "saved",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        templates.append(record)
        TEMPLATES_PATH.write_text(json.dumps(templates, indent=2), encoding="utf-8")
        return record


def list_templates(channel: str | None = None) -> list[dict]:
    _ensure_store()
    with _lock:
        templates = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    if channel:
        templates = [t for t in templates if t["channel"] == channel]
    return templates


def get_template(template_id: str) -> dict | None:
    _ensure_store()
    with _lock:
        templates = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    return next((t for t in templates if t["id"] == template_id), None)


def update_template(template_id: str, name: str, payload: dict) -> dict | None:
    _ensure_store()
    with _lock:
        templates = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
        for t in templates:
            if t["id"] == template_id:
                t["name"] = name
                t["payload"] = payload
                t["updated_at"] = datetime.now(timezone.utc).isoformat()
                TEMPLATES_PATH.write_text(json.dumps(templates, indent=2), encoding="utf-8")
                return t
    return None
