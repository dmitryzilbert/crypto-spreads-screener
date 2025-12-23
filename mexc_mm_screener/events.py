import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class Event:
    ts: float
    type: str
    symbol: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    top: Optional[List[Dict[str, Any]]] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"ts": self.ts, "type": self.type}
        if self.symbol is not None:
            payload["symbol"] = self.symbol
        if self.metrics is not None:
            payload["metrics"] = self.metrics
        if self.top is not None:
            payload["top"] = self.top
        payload.update(self.extra)
        return payload


class EventSink:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._file = None

    def _ensure_file(self) -> None:
        if self._file is not None:
            return
        try:
            self._file = self.path.open("a", buffering=1, encoding="utf-8")
        except OSError as exc:
            logger.warning("Unable to open events file %s: %s", self.path, exc)
            self._file = None

    def emit(self, event: Dict[str, Any] | Event) -> None:
        if isinstance(event, Event):
            data = event.to_dict()
        else:
            data = event
        self._ensure_file()
        if self._file is None:
            return
        try:
            self._file.write(json.dumps(data, ensure_ascii=False) + "\n")
            self._file.flush()
        except OSError as exc:
            logger.warning("Failed to write event to %s: %s", self.path, exc)
            self._file = None
