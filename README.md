# crypto-spreads-screener

Минимальный MVP скринера стаканов (async) + Telegram-бот уведомлений через events.jsonl.

## Установка

Для скринера достаточно стандартной библиотеки + PyYAML:

```bash
python -m pip install PyYAML
```

Для бота используйте отдельные зависимости, чтобы не тянуть их в основной скринер:

```bash
python -m pip install -r requirements-bot.txt
```

## Конфиги

Пример `config.yaml` (скринер):

```yaml
symbols:
  - BTCUSDT
  - ETHUSDT
  - XRPUSDT

go_score_threshold: 80
go_off_threshold: 60
emit_go_off: true

events:
  path: "./events.jsonl"

runtime:
  tick_interval_sec: 5
  snapshot_interval_sec: 30
  snapshot_top_n: 10
```

Пример `config.telegram.yaml` (бот):

```yaml
telegram:
  token: "YOUR_TELEGRAM_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"
events:
  path: "./events.jsonl"
notify:
  min_interval_sec_per_symbol: 300
  send_go_off: false
  include_snapshot: true
commands:
  top_n_default: 10
```

## Events & Telegram bot

1. Скринер запускается отдельно и пишет события в `events.jsonl` (append-only JSONL). Он продолжает работать даже если файл недоступен или бот не запущен.
2. Бот — отдельный процесс, tail-читает `events.jsonl`, парсит события и отправляет уведомления в Telegram с анти-спамом по каждому символу.
3. Слабая связка: никаких очередей/БД, только локальный файл событий. Ошибки бота не влияют на скринер.
4. Команды бота: `/start`, `/top [N]`, `/status`, `/mute SYMBOL`, `/unmute SYMBOL`.
5. Rate-limit на уведомлениях: не чаще, чем указанно в `notify.min_interval_sec_per_symbol`.

## Запуск

1. Запустите скринер:

```bash
python main.py --config config.yaml
```

2. В другом процессе запустите бота:

```bash
python bot_main.py --config config.telegram.yaml
```

## Как это работает

- При смене состояния GO `false -> true` (и при `true -> false`, если разрешено) скринер пишет события `go_on`/`go_off` с ключевыми метриками.
- Периодически пишется `snapshot` топ-N символов, чтобы бот мог отвечать на `/top` и `/status`.
- Бот следит за событиями, применяет rate-limit, форматирует сообщения и отправляет их в указанный чат.
- Все процессы используют `asyncio`, без потоков и внешних брокеров.

## Ограничения

- Метрики в текущем MVP симулируются случайно, пороги настраиваются в `config.yaml`.
- Mute список хранится только в памяти бота.
