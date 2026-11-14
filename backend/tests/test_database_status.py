import asyncio

from app.services.database_status import DatabaseStatusMonitor


def test_monitor_broadcasts_only_status_changes(monkeypatch):
    results = iter([True, True, False])
    monkeypatch.setattr(
        "app.services.database_status.check_database_connection",
        lambda: next(results, False),
    )

    async def verify_status_updates():
        monitor = DatabaseStatusMonitor(check_interval=0.01)
        queue = monitor.subscribe()

        assert queue.get_nowait() == "checking"

        await monitor.start()
        try:
            assert await asyncio.wait_for(queue.get(), timeout=1) == "online"
            await asyncio.sleep(0.015)
            assert await asyncio.wait_for(queue.get(), timeout=1) == "offline"
        finally:
            await monitor.stop()

    asyncio.run(verify_status_updates())
