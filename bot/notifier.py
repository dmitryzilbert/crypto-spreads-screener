import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bot.config import NotifyConfig

logger = logging.getLogger(__name__)


@dataclass
class Notifier:
    notify_config: NotifyConfig
    muted: set[str] = field(default_factory=set)
    last_sent_ts: Dict[str, float] = field(default_factory=dict)
    last_snapshot: Optional[dict] = None

    def should_send(self, symbol: str) -> bool:
        now = time.time()
        last = self.last_sent_ts.get(symbol, 0)
        if now - last < self.notify_config.min_interval_sec_per_symbol:
            return False
        self.last_sent_ts[symbol] = now
        return True

    def format_go_message(self, event: dict) -> str:
        metrics = event.get("metrics", {})
        ts = event.get("ts", time.time())
        return (
            f"GO: {event.get('symbol','')}\n"
            f"spread: {metrics.get('spread_bps_med_60s', 0):.1f} bps\n"
            f"notional(60s): ${metrics.get('notional_60s_usd', 0):.0f}\n"
            f"refill: {metrics.get('refill_rate_5m', 0):.2f}\n"
            f"range(60s): {metrics.get('mid_range_bps_60s', 0):.1f} bps\n"
            f"score: {metrics.get('score', 0):.0f}\n"
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}"
        )

    def update_snapshot(self, event: dict) -> None:
        self.last_snapshot = event

    def cache_go_event(self, event: dict) -> None:
        symbol = event.get("symbol")
        if not symbol:
            return
        if event.get("type") == "go_off":
            self.last_sent_ts.pop(symbol, None)

    def get_top(self, n: int) -> List[dict]:
        if not self.last_snapshot:
            return []
        return list(self.last_snapshot.get("top", [])[:n])

    def active_go_count(self) -> int:
        if not self.last_snapshot:
            return 0
        return sum(1 for item in self.last_snapshot.get("top", []) if item.get("go"))

    def process_event(self, event: dict) -> Optional[str]:
        etype = event.get("type")
        symbol = event.get("symbol")
        if etype == "snapshot":
            if self.notify_config.include_snapshot:
                self.update_snapshot(event)
            return None
        if symbol is None:
            return None
        if symbol in self.muted:
            return None
        if etype == "go_on":
            if not self.should_send(symbol):
                return None
            self.cache_go_event(event)
            return self.format_go_message(event)
        if etype == "go_off" and self.notify_config.send_go_off:
            if not self.should_send(symbol):
                return None
            self.cache_go_event(event)
            return f"GO OFF: {symbol}\nscore: {event.get('metrics', {}).get('score', 0):.0f}"
        return None

    def mute(self, symbol: str) -> None:
        self.muted.add(symbol.upper())

    def unmute(self, symbol: str) -> None:
        self.muted.discard(symbol.upper())
