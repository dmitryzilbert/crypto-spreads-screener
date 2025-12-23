import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncIterator, Dict


logger = logging.getLogger(__name__)


async def tail_events(path: Path, poll_interval: float = 1.0) -> AsyncIterator[Dict]:
    position = 0
    inode = None
    file_obj = None
    while True:
        try:
            stat = path.stat()
            current_inode = stat.st_ino
            if inode != current_inode:
                if file_obj:
                    file_obj.close()
                file_obj = path.open("r", encoding="utf-8")
                inode = current_inode
                position = 0
                logger.info("Opened events file %s", path)
            if stat.st_size < position:
                position = 0
                file_obj.seek(0)
            file_obj.seek(position)
            line = file_obj.readline()
            if line:
                position = file_obj.tell()
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed event line: %s", line.strip())
                continue
        except FileNotFoundError:
            if file_obj:
                file_obj.close()
                file_obj = None
            inode = None
        except OSError as exc:
            logger.warning("Tail error for %s: %s", path, exc)
            if file_obj:
                file_obj.close()
                file_obj = None
            inode = None
        await asyncio.sleep(poll_interval)
