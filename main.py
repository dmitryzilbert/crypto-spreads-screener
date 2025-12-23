import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any, Dict

import yaml

from mexc_mm_screener.events import EventSink
from mexc_mm_screener.screener import build_screener_from_config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MEXC MM Screener")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="Path to YAML config")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    events_cfg = config.get("events", {})
    sink_path = events_cfg.get("path", "./events.jsonl")
    event_sink = EventSink(sink_path) if sink_path else None
    screener = build_screener_from_config(config, event_sink)
    await screener.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
