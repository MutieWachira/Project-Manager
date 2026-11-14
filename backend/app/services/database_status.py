import asyncio
import logging
from typing import Literal

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import check_database_connection

logger = logging.getLogger(__name__)

DatabaseStatus = Literal["checking", "online", "offline"]


class DatabaseStatusMonitor:
    def __init__(self, check_interval: float = 5) -> None:
        self._check_interval = check_interval
        self._status: DatabaseStatus = "checking"
        self._subscribers: set[asyncio.Queue[DatabaseStatus]] = set()
        self._task: asyncio.Task[None] | None = None
        self._check_failed = False

    @property
    def status(self) -> DatabaseStatus:
        return self._status

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    def subscribe(self) -> asyncio.Queue[DatabaseStatus]:
        queue: asyncio.Queue[DatabaseStatus] = asyncio.Queue(maxsize=1)
        queue.put_nowait(self._status)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[DatabaseStatus]) -> None:
        self._subscribers.discard(queue)

    async def _run(self) -> None:
        while True:
            await self._refresh_status()
            await asyncio.sleep(self._check_interval)

    async def _refresh_status(self) -> None:
        try:
            database_online = await asyncio.to_thread(check_database_connection)
            status: DatabaseStatus = "online" if database_online else "offline"
        except SQLAlchemyError:
            if not self._check_failed:
                logger.exception(
                    "Database status monitor could not reach the database."
                )
            self._check_failed = True
            status = "offline"
        else:
            self._check_failed = False

        if status == self._status:
            return

        self._status = status
        for queue in tuple(self._subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(status)
