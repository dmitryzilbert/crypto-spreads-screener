import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from mexc_mm_screener.events import Event, EventSink

logger = logging.getLogger(__name__)


@dataclass
class SymbolState:
    symbol: str
    go: bool = False
    score: float = 0.0
    spread_bps_med_60s: float = 0.0
    notional_60s_usd: float = 0.0
    refill_rate_5m: float = 0.0
    mid_range_bps_60s: float = 0.0

    @property
    def metrics(self) -> Dict[str, float]:
        return {
            "spread_bps_med_60s": self.spread_bps_med_60s,
            "notional_60s_usd": self.notional_60s_usd,
            "refill_rate_5m": self.refill_rate_5m,
            "mid_range_bps_60s": self.mid_range_bps_60s,
            "score": self.score,
        }


def _simulate_metrics() -> Dict[str, float]:
    score = random.uniform(0, 120)
    return {
        "spread_bps_med_60s": random.uniform(0.5, 30.0),
        "notional_60s_usd": random.uniform(5000, 80000),
        "refill_rate_5m": random.uniform(0, 5),
        "mid_range_bps_60s": random.uniform(1, 40),
        "score": score,
    }


class Screener:
    def __init__(
        self,
        symbols: List[str],
        go_score_threshold: float,
        go_off_threshold: Optional[float],
        tick_interval: float,
        snapshot_interval: float,
        snapshot_top_n: int,
        event_sink: Optional[EventSink] = None,
        emit_go_off: bool = True,
    ) -> None:
        self.states: Dict[str, SymbolState] = {sym: SymbolState(sym) for sym in symbols}
        self.go_score_threshold = go_score_threshold
        self.go_off_threshold = go_off_threshold if go_off_threshold is not None else go_score_threshold * 0.8
        self.tick_interval = tick_interval
        self.snapshot_interval = snapshot_interval
        self.snapshot_top_n = snapshot_top_n
        self.event_sink = event_sink
        self.emit_go_off = emit_go_off
        self._last_snapshot = 0.0

    async def run(self) -> None:
        logger.info("Starting screener for %d symbols", len(self.states))
        while True:
            start = time.time()
            await self._process_symbols()
            if start - self._last_snapshot >= self.snapshot_interval:
                self._emit_snapshot(start)
                self._last_snapshot = start
            elapsed = time.time() - start
            await asyncio.sleep(max(0.0, self.tick_interval - elapsed))

    async def _process_symbols(self) -> None:
        for state in self.states.values():
            metrics = _simulate_metrics()
            state.score = metrics["score"]
            state.spread_bps_med_60s = metrics["spread_bps_med_60s"]
            state.notional_60s_usd = metrics["notional_60s_usd"]
            state.refill_rate_5m = metrics["refill_rate_5m"]
            state.mid_range_bps_60s = metrics["mid_range_bps_60s"]
            was_go = state.go
            if was_go:
                now_go = metrics["score"] >= self.go_off_threshold
            else:
                now_go = metrics["score"] >= self.go_score_threshold
            state.go = now_go
            if not was_go and now_go:
                self._emit_event("go_on", state)
                logger.info("GO ON %s score=%.2f", state.symbol, state.score)
            elif was_go and not now_go and self.emit_go_off:
                self._emit_event("go_off", state)
                logger.info("GO OFF %s score=%.2f", state.symbol, state.score)

    def _emit_event(self, event_type: str, state: SymbolState) -> None:
        if self.event_sink is None:
            return
        event = Event(ts=time.time(), type=event_type, symbol=state.symbol, metrics=state.metrics)
        self.event_sink.emit(event)

    def _emit_snapshot(self, ts: float) -> None:
        top = sorted(self.states.values(), key=lambda s: s.score, reverse=True)[: self.snapshot_top_n]
        payload = [
            {
                "symbol": s.symbol,
                "go": s.go,
                "score": s.score,
                "spread_bps_med_60s": s.spread_bps_med_60s,
                "notional_60s_usd": s.notional_60s_usd,
                "refill_rate_5m": s.refill_rate_5m,
                "mid_range_bps_60s": s.mid_range_bps_60s,
            }
            for s in top
        ]
        if self.event_sink is None:
            return
        self.event_sink.emit(Event(ts=ts, type="snapshot", top=payload))


def build_screener_from_config(config: Dict[str, object], event_sink: Optional[EventSink]) -> Screener:
    symbols = [s.upper() for s in config.get("symbols", [])]
    go_score_threshold = float(config.get("go_score_threshold", 80))
    go_off_threshold_raw = config.get("go_off_threshold")
    go_off_threshold = float(go_off_threshold_raw) if go_off_threshold_raw is not None else None
    runtime = config.get("runtime", {})
    tick_interval = float(getattr(runtime, "get", lambda _k, default=None: default)("tick_interval_sec", 5))
    snapshot_interval = float(getattr(runtime, "get", lambda _k, default=None: default)("snapshot_interval_sec", 30))
    snapshot_top_n = int(getattr(runtime, "get", lambda _k, default=None: default)("snapshot_top_n", 10))
    emit_go_off = bool(config.get("emit_go_off", True))
    return Screener(
        symbols=symbols,
        go_score_threshold=go_score_threshold,
        go_off_threshold=go_off_threshold,
        tick_interval=tick_interval,
        snapshot_interval=snapshot_interval,
        snapshot_top_n=snapshot_top_n,
        event_sink=event_sink,
        emit_go_off=emit_go_off,
    )
