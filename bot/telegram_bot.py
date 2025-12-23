import asyncio
import logging
from typing import Callable, Optional

from telegram import Update
from telegram.ext import Application, CallbackContext, CommandHandler

from bot.config import BotConfig
from bot.event_tail import tail_events
from bot.notifier import Notifier

logger = logging.getLogger(__name__)


async def _send_message(application: Application, chat_id: str, text: str) -> None:
    try:
        await application.bot.send_message(chat_id=chat_id, text=text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to send telegram message: %s", exc)


async def _event_worker(app: Application, chat_id: str, notifier: Notifier, path, stop_event: asyncio.Event) -> None:
    async for event in tail_events(path):
        if stop_event.is_set():
            break
        message = notifier.process_event(event)
        if message:
            await _send_message(app, chat_id, message)


def _parse_int(value: Optional[str], default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


async def start_command(update: Update, _: CallbackContext) -> None:
    await update.message.reply_text(
        "MEXC MM Screener bot. Commands: /top [N], /status, /mute SYMBOL, /unmute SYMBOL"
    )


async def top_command(update: Update, context: CallbackContext, notifier: Notifier, default_n: int) -> None:
    args = context.args if context.args else []
    n = _parse_int(args[0], default_n) if args else default_n
    top = notifier.get_top(n)
    if not top:
        await update.message.reply_text("Нет данных snapshot")
        return
    lines = []
    for item in top:
        lines.append(
            f"{item.get('symbol')}: score={item.get('score', 0):.1f}, "
            f"spread={item.get('spread_bps_med_60s', 0):.1f}bps, "
            f"notional=${item.get('notional_60s_usd', 0):.0f}, "
            f"refill={item.get('refill_rate_5m', 0):.2f}"
        )
    await update.message.reply_text("Top:\n" + "\n".join(lines))


async def status_command(update: Update, _: CallbackContext, notifier: Notifier) -> None:
    count = notifier.active_go_count()
    await update.message.reply_text(f"Активных GO: {count}")


async def mute_command(update: Update, context: CallbackContext, notifier: Notifier) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /mute SYMBOL")
        return
    symbol = context.args[0].upper()
    notifier.mute(symbol)
    await update.message.reply_text(f"Muted {symbol}")


async def unmute_command(update: Update, context: CallbackContext, notifier: Notifier) -> None:
    if not context.args:
        await update.message.reply_text("Использование: /unmute SYMBOL")
        return
    symbol = context.args[0].upper()
    notifier.unmute(symbol)
    await update.message.reply_text(f"Unmuted {symbol}")


async def run_bot(config: BotConfig) -> None:
    notifier = Notifier(config.notify)
    application = Application.builder().token(config.telegram.token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("top", lambda u, c: top_command(u, c, notifier, config.commands.top_n_default)))
    application.add_handler(CommandHandler("status", lambda u, c: status_command(u, c, notifier)))
    application.add_handler(CommandHandler("mute", lambda u, c: mute_command(u, c, notifier)))
    application.add_handler(CommandHandler("unmute", lambda u, c: unmute_command(u, c, notifier)))

    stop_event = asyncio.Event()

    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Telegram bot started")
        worker = asyncio.create_task(
            _event_worker(application, config.telegram.chat_id, notifier, config.events.path, stop_event)
        )
        await application.updater.wait()
    finally:
        stop_event.set()
        if 'worker' in locals():
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
