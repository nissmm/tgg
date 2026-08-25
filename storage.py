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
HR_PROFILES_FILE = DATA_DIR / "hr_profiles.pkl"
LEGACY_HR_ROLES_FILE = DATA_DIR / "hr_roles.pkl"  # формат до апдейта с профилями
HR_RECORDS_FILE = DATA_DIR / "hr_records.pkl"
SETTINGS_FILE = DATA_DIR / "settings.pkl"
TOPICS_FILE = DATA_DIR / "topics.pkl"


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
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


# ------------------------------------------------------------ hr profiles --
def get_hr_profiles() -> dict:
    """user_id -> {username, joined_at, shift_start, total_worked_seconds}."""
    profiles = _load(HR_PROFILES_FILE, None)
    if profiles is not None:
        return profiles

    # миграция со старого формата (просто множество id без метаданных)
    legacy = _load(LEGACY_HR_ROLES_FILE, None)
    profiles = {}
    if legacy:
        now = datetime.now().isoformat()
        for uid in legacy:
            profiles[uid] = {
                "username": "",
                "joined_at": now,
                "shift_start": None,
                "total_worked_seconds": 0.0,
            }
    _save(HR_PROFILES_FILE, profiles)
    return profiles


def get_hr_roles() -> set:
    return set(get_hr_profiles().keys())


def is_hr(user_id: int) -> bool:
    return user_id in get_hr_profiles()


def get_hr_profile(user_id: int) -> Optional[dict]:
    return get_hr_profiles().get(user_id)


def add_hr(user_id: int, username: Optional[str] = None) -> None:
    profiles = get_hr_profiles()
    if user_id not in profiles:
        profiles[user_id] = {
            "username": username or "",
            "joined_at": datetime.now().isoformat(),
            "shift_start": None,
            "total_worked_seconds": 0.0,
        }
    elif username:
        profiles[user_id]["username"] = username
    _save(HR_PROFILES_FILE, profiles)


def remove_hr(user_id: int) -> None:
    profiles = get_hr_profiles()
    profiles.pop(user_id, None)
    _save(HR_PROFILES_FILE, profiles)


def is_shift_active(user_id: int) -> bool:
    profile = get_hr_profiles().get(user_id)
    return bool(profile and profile.get("shift_start"))


def start_shift(user_id: int) -> None:
    profiles = get_hr_profiles()
    if user_id in profiles:
        profiles[user_id]["shift_start"] = datetime.now().isoformat()
        _save(HR_PROFILES_FILE, profiles)


def end_shift(user_id: int):
    """Завершает смену. Возвращает (duration_seconds, shift_start_iso) либо None,
    если смена не была начата."""
    profiles = get_hr_profiles()
    profile = profiles.get(user_id)
    if not profile or not profile.get("shift_start"):
        return None

    shift_start_iso = profile["shift_start"]
    started = datetime.fromisoformat(shift_start_iso)
    duration = (datetime.now() - started).total_seconds()
    profile["total_worked_seconds"] = profile.get("total_worked_seconds", 0.0) + duration
    profile["shift_start"] = None
    _save(HR_PROFILES_FILE, profiles)
    return duration, shift_start_iso


# ------------------------------------------------------------- hr records --
def get_hr_records() -> list:
    return _load(HR_RECORDS_FILE, [])


def _save_records(records: list) -> None:
    _save(HR_RECORDS_FILE, records)


def add_hr_record(record: dict) -> dict:
    records = get_hr_records()
    record = dict(record)
    record["id"] = max((r.get("id", 0) for r in records), default=0) + 1
    record.setdefault("created_at", datetime.now().isoformat())
    record.setdefault("status", "approved")
    records.append(record)
    _save_records(records)
    return record


def get_record(record_id: int) -> Optional[dict]:
    for r in get_hr_records():
        if r["id"] == record_id:
            return r
    return None


def update_record(record_id: int, **fields) -> Optional[dict]:
    records = get_hr_records()
    for r in records:
        if r["id"] == record_id:
            r.update(fields)
            _save_records(records)
            return r
    return None


def get_pending_records() -> list:
    return [r for r in get_hr_records() if r.get("status") in ("pending", "postponed")]


def get_records_by_hr(hr_id: int, status: Optional[str] = "approved") -> list:
    if status is None:
        return [r for r in get_hr_records() if r.get("hr_id") == hr_id]
    return [r for r in get_hr_records() if r.get("hr_id") == hr_id and r.get("status") == status]


def add_ticket_message(record_id: int, sender_type: str, sender_id: int, author_name: str, text: str) -> Optional[dict]:
    records = get_hr_records()
    for r in records:
        if r["id"] == record_id:
            messages = r.setdefault("tickets", [])
            msg = {
                "id": len(messages) + 1,
                "sender_type": sender_type,  # 'hr' | 'user'
                "sender_id": sender_id,
                "author_name": author_name,
                "text": text,
                "created_at": datetime.now().isoformat(),
            }
            messages.append(msg)
            _save_records(records)
            return msg
    return None


def get_ticket_messages(record_id: int) -> list:
    record = get_record(record_id)
    return record.get("tickets", []) if record else []


# -------------------------------------------------------------- settings --
def get_settings() -> dict:
    return _load(SETTINGS_FILE, {"target_topic_id": None, "daily_plan": 10})


def set_target_topic(topic_id: Optional[int]) -> None:
    settings = get_settings()
    settings["target_topic_id"] = topic_id
    _save(SETTINGS_FILE, settings)


def get_daily_plan() -> int:
    return get_settings().get("daily_plan", 10)


def set_daily_plan(value: int) -> None:
    settings = get_settings()
    settings["daily_plan"] = value
    _save(SETTINGS_FILE, settings)


# ---------------------------------------------------------------- topics --
def get_topics() -> dict:
    """topic_id (int | None) -> name. None ключ = General/основной топик."""
    return _load(TOPICS_FILE, {})


def register_topic(topic_id: Optional[int], name: str) -> None:
    topics = get_topics()
    topics[topic_id] = name
    _save(TOPICS_FILE, topics)
