import argparse
import asyncio
import logging
from pathlib import Path

from bot.config import load_config
from bot.telegram_bot import run_bot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telegram notifier for MEXC MM screener")
    parser.add_argument("--config", type=Path, default=Path("config.telegram.yaml"), help="Path to telegram YAML config")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    await run_bot(config)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
