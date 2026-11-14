import asyncio
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import check_database_connection
from app.services.database_status import DatabaseStatusMonitor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    try:
        database_online = check_database_connection()
    except SQLAlchemyError as error:
        logger.exception("Database health check failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "offline",
            },
        ) from error

    if not database_online:
        logger.error("Database health check did not confirm connectivity.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "offline",
            },
        )

    return {
        "status": "healthy",
        "database": "online",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.websocket("/ws/database-status")
async def database_status_updates(websocket: WebSocket) -> None:
    await websocket.accept()
    monitor: DatabaseStatusMonitor = websocket.app.state.database_status_monitor
    queue = monitor.subscribe()

    try:
        while True:
            status_task = asyncio.create_task(queue.get())
            receive_task = asyncio.create_task(websocket.receive())
            heartbeat_task = asyncio.create_task(asyncio.sleep(20))
            done, pending = await asyncio.wait(
                (status_task, receive_task, heartbeat_task),
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

            if receive_task in done:
                if receive_task.result()["type"] == "websocket.disconnect":
                    break
                if status_task not in done:
                    continue

            if status_task in done:
                await websocket.send_json({"database": status_task.result()})
            elif heartbeat_task in done:
                await websocket.send_json({"database": monitor.status})
    except WebSocketDisconnect:
        pass
    finally:
        monitor.unsubscribe(queue)
