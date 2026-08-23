"""
Простое хранилище на бинарных файлах (pickle).
Папка data создаётся автоматически, файлы создаются лениво при первой записи.
"""

import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.pkl"
HR_ROLES_FILE = DATA_DIR / "hr_roles.pkl"
HR_RECORDS_FILE = DATA_DIR / "hr_records.pkl"
SETTINGS_FILE = DATA_DIR / "settings.pkl"
TOPICS_FILE = DATA_DIR / "topics.pkl"


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except EOFError:
        return default


def _save(path: Path, data) -> None:
    with open(path, "wb") as f:
        pickle.dump(data, f)


# ---------------------------------------------------------------- users ----
def get_users() -> dict:
    return _load(USERS_FILE, {})


def register_user(user_id: int, username: Optional[str]) -> None:
    users = get_users()
    existing = users.get(user_id, {})
    users[user_id] = {
        "username": f"@{username}" if username else "(без username)",
        "first_seen": existing.get("first_seen", datetime.now().isoformat()),
    }
    _save(USERS_FILE, users)


# ------------------------------------------------------------- hr roles ----
def get_hr_roles() -> set:
    return _load(HR_ROLES_FILE, set())


def add_hr(user_id: int) -> None:
    roles = get_hr_roles()
    roles.add(user_id)
    _save(HR_ROLES_FILE, roles)


def remove_hr(user_id: int) -> None:
    roles = get_hr_roles()
    roles.discard(user_id)
    _save(HR_ROLES_FILE, roles)


def is_hr(user_id: int) -> bool:
    return user_id in get_hr_roles()


# ----------------------------------------------------------- hr records ----
def get_hr_records() -> list:
    return _load(HR_RECORDS_FILE, [])


def add_hr_record(record: dict) -> dict:
    records = get_hr_records()
    record = dict(record)
    record["id"] = (records[-1]["id"] + 1) if records else 1
    record["created_at"] = datetime.now().isoformat()
    records.append(record)
    _save(HR_RECORDS_FILE, records)
    return record


# -------------------------------------------------------------- settings --
def get_settings() -> dict:
    return _load(SETTINGS_FILE, {"target_topic_id": None})


def set_target_topic(topic_id: Optional[int]) -> None:
    settings = get_settings()
    settings["target_topic_id"] = topic_id
    _save(SETTINGS_FILE, settings)


# ---------------------------------------------------------------- topics --
def get_topics() -> dict:
    """topic_id (int | None) -> name. None ключ = General/основной топик."""
    return _load(TOPICS_FILE, {})


def register_topic(topic_id: Optional[int], name: str) -> None:
    topics = get_topics()
    topics[topic_id] = name
    _save(TOPICS_FILE, topics)
