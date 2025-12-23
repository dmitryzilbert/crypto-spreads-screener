from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class TelegramConfig:
    token: str
    chat_id: str


@dataclass
class EventConfig:
    path: Path


@dataclass
class NotifyConfig:
    min_interval_sec_per_symbol: int = 300
    send_go_off: bool = False
    include_snapshot: bool = True


@dataclass
class CommandConfig:
    top_n_default: int = 10


@dataclass
class BotConfig:
    telegram: TelegramConfig
    events: EventConfig
    notify: NotifyConfig
    commands: CommandConfig


def load_config(path: Path) -> BotConfig:
    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = yaml.safe_load(f) or {}

    telegram_raw = data.get("telegram", {})
    events_raw = data.get("events", {})
    notify_raw = data.get("notify", {})
    commands_raw = data.get("commands", {})

    telegram = TelegramConfig(token=str(telegram_raw.get("token", "")), chat_id=str(telegram_raw.get("chat_id", "")))
    events = EventConfig(path=Path(events_raw.get("path", "./events.jsonl")))
    notify = NotifyConfig(
        min_interval_sec_per_symbol=int(notify_raw.get("min_interval_sec_per_symbol", 300)),
        send_go_off=bool(notify_raw.get("send_go_off", False)),
        include_snapshot=bool(notify_raw.get("include_snapshot", True)),
    )
    commands = CommandConfig(top_n_default=int(commands_raw.get("top_n_default", 10)))

    return BotConfig(telegram=telegram, events=events, notify=notify, commands=commands)
