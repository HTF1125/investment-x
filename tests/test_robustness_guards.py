import asyncio
import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from ix.api.routers.custom import _load_explicit_export_charts
from ix.api.task_utils import TaskEventSubscriber, _deliver_task_event
from ix.db.models import Timeseries
from ix.db.query import Series

db_conn_module = importlib.import_module("ix.db.conn")


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        del args, kwargs
        return self

    def all(self):
        return list(self._rows)


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *args):
        del args
        return _FakeQuery(self._rows)


class _BrokenTimeseries:
    start = None
    currency = ""
    scale = 1

    @property
    def data(self):
        raise RuntimeError("boom")


class _BrokenSessionQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        del args, kwargs
        return self

    def first(self):
        return self._result


class _BrokenSession:
    def __init__(self, result):
        self._result = result

    def query(self, *args, **kwargs):
        del args, kwargs
        return _BrokenSessionQuery(self._result)


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


class ExportAccessTests(unittest.TestCase):
    def test_blocks_private_chart_export_for_non_owner(self):
        chart = SimpleNamespace(
            id="chart-1",
            public=False,
            created_by_user_id="owner-1",
        )
        current_user = SimpleNamespace(id="viewer-1", role="general")

        with self.assertRaises(HTTPException) as ctx:
            _load_explicit_export_charts(_FakeDB([chart]), current_user, ["chart-1"])

        self.assertEqual(ctx.exception.status_code, 404)

    def test_allows_private_chart_export_for_owner(self):
        chart = SimpleNamespace(
            id="chart-1",
            public=False,
            created_by_user_id="owner-1",
        )
        current_user = SimpleNamespace(id="owner-1", role="general")

        result = _load_explicit_export_charts(
            _FakeDB([chart]),
            current_user,
            ["chart-1"],
        )

        self.assertEqual(result, [chart])

    def test_allows_public_chart_export_for_non_owner(self):
        chart = SimpleNamespace(
            id="chart-1",
            public=True,
            created_by_user_id="owner-1",
        )
        current_user = SimpleNamespace(id="viewer-1", role="general")

        result = _load_explicit_export_charts(
            _FakeDB([chart]),
            current_user,
            ["chart-1"],
        )

        self.assertEqual(result, [chart])


class TaskEventDeliveryTests(unittest.TestCase):
    def test_bounded_queue_drops_oldest_event(self):
        loop = asyncio.new_event_loop()
        try:
            queue = asyncio.Queue(maxsize=1)
            subscriber = TaskEventSubscriber(loop=loop, queue=queue)
            queue.put_nowait({"event": "old"})

            _deliver_task_event(subscriber, {"event": "new"})

            self.assertEqual(queue.get_nowait()["event"], "new")
        finally:
            loop.close()


class SeriesStrictnessTests(unittest.TestCase):
    def test_series_strict_mode_reraises_loader_error(self):
        broken_session = _BrokenSession(_BrokenTimeseries())
        with self.assertRaises(RuntimeError):
            Series("SPX Index:PX_LAST", session=broken_session, strict=True)

    def test_series_non_strict_mode_returns_empty_series(self):
        token = db_conn_module.custom_chart_session.set(
            _BrokenSession(_BrokenTimeseries())
        )
        try:
            series = Series("SPX Index:PX_LAST", strict=False)
        finally:
            db_conn_module.custom_chart_session.reset(token)

        self.assertTrue(series.empty)


class TimeseriesCycleValidationTests(unittest.TestCase):
    def test_detect_cycle_raises_when_validation_cannot_run(self):
        ts = Timeseries()
        ts.id = "child-1"

        with patch("ix.db.conn.Session", side_effect=RuntimeError("boom")):
            with self.assertRaises(ValueError):
                ts._detect_cycle("parent-1")


if __name__ == "__main__":
    unittest.main()
