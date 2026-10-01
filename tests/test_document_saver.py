"""The second half of a save runs on its own thread and reports back on the interface thread (S1.2).

What the interface needs from it: it must not block the event loop while a file is written, the
writes must come out in the order they were asked, the result must arrive on the interface thread
(callbacks touch widgets), a failure must reach the caller, and a closing application must be able
to wait for what is in flight.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6 import QtCore

from ui.core.document.document_saver import DocumentSaver
from ui.core.document.save_capture import SaveCapture


def _capture(uid="doc", revision=1, name="a.lmn") -> SaveCapture:
    return SaveCapture(uid=uid, revision=revision, target=Path(name), manifest={}, snapshot=None,
                       raster_layers=(), extras={})


def _drain(qapp, saver: DocumentSaver, timeout_ms=5000) -> None:
    assert saver.wait_idle(timeout_ms), "the saver did not go idle"
    qapp.processEvents()


def test_the_callback_runs_on_the_interface_thread_and_the_write_on_another(qapp):
    where = {}

    def writer(capture):
        where["write"] = threading.get_ident()
        return str(capture.target)

    saver = DocumentSaver(writer=writer)
    saver.submit(_capture(), on_done=lambda capture: where.update(done=threading.get_ident(), target=capture.target))
    _drain(qapp, saver)
    assert where["write"] != threading.get_ident()
    assert where["done"] == threading.get_ident()
    assert where["target"] == Path("a.lmn")


def test_writes_happen_one_at_a_time_in_the_order_they_were_asked(qapp):
    order, running, overlap = [], [0], []

    def writer(capture):
        running[0] += 1
        overlap.append(running[0])
        time.sleep(0.02)
        order.append(capture.revision)
        running[0] -= 1
        return ""

    saver = DocumentSaver(writer=writer)
    done = []
    for revision in range(6):
        saver.submit(_capture(revision=revision), on_done=lambda c: done.append(c.revision))
    _drain(qapp, saver)
    assert order == list(range(6)) and done == list(range(6))
    assert max(overlap) == 1, "two writes ran at once"


def test_the_event_loop_keeps_running_while_a_slow_file_is_written(qapp):
    """The point of it all: the interface must not freeze for the length of a save."""
    def writer(_capture_):
        time.sleep(0.5)
        return ""

    saver = DocumentSaver(writer=writer)
    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
    timer.start()
    saver.submit(_capture())
    deadline = time.perf_counter() + 5
    while saver.is_busy() and time.perf_counter() < deadline:
        qapp.processEvents()
        time.sleep(0.001)
    timer.stop()
    assert len(ticks) > 40, f"only {len(ticks)} timer ticks in half a second: the event loop was starved"
    longest_gap = max(b - a for a, b in zip(ticks, ticks[1:]))
    # A write that blocked the interface would leave a gap of about 500 ms (the length of the write).
    # 100 ms keeps a 20x margin over that and does not fail when a loaded machine pauses the process
    # for a scheduler slice (it did once in the full suite at 50 ms).
    assert longest_gap < 0.1, f"the event loop stopped for {longest_gap * 1000:.0f} ms during the write"


def test_a_failed_write_reaches_the_caller_with_its_capture(qapp):
    def writer(_capture_):
        raise OSError("disk full")

    saver = DocumentSaver(writer=writer)
    errors = []
    saver.submit(_capture(uid="x"), on_done=lambda c: errors.append("done"), on_error=lambda c, exc: errors.append((c.uid, str(exc))))
    _drain(qapp, saver)
    assert errors == [("x", "disk full")]


def test_a_failure_nobody_handles_is_logged_and_the_queue_goes_on(qapp, caplog):
    calls = []

    def writer(capture):
        if capture.revision == 1:
            raise OSError("boom")
        calls.append(capture.revision)
        return ""

    saver = DocumentSaver(writer=writer)
    saver.submit(_capture(revision=1))
    saver.submit(_capture(revision=2), on_done=lambda c: calls.append("done"))
    with caplog.at_level("ERROR"):
        _drain(qapp, saver)
    assert calls == [2, "done"]
    assert any("boom" in record.getMessage() for record in caplog.records)


def test_a_callback_that_raises_does_not_stop_the_next_job(qapp, caplog):
    saver = DocumentSaver(writer=lambda capture: "")
    seen = []

    def bad(_c):
        raise RuntimeError("callback bug")

    saver.submit(_capture(revision=1), on_done=bad)
    saver.submit(_capture(revision=2), on_done=lambda c: seen.append(c.revision))
    with caplog.at_level("ERROR"):
        _drain(qapp, saver)
    assert seen == [2]
    assert any("callback bug" in (record.exc_text or "") for record in caplog.records)


def test_wait_idle_returns_when_the_queue_empties_and_times_out_otherwise(qapp):
    release = threading.Event()

    def writer(_capture_):
        release.wait(5)
        return ""

    saver = DocumentSaver(writer=writer)
    assert saver.wait_idle(10) is True, "nothing in flight: it must return at once"
    saver.submit(_capture(uid="blocked"))
    assert saver.is_busy() and saver.is_saving("blocked") and not saver.is_saving("other")
    assert saver.wait_idle(50) is False, "it must give up when the timeout runs out"
    release.set()
    assert saver.wait_idle(5000) is True
    assert not saver.is_busy()


def test_idle_is_announced_once_when_the_last_job_ends(qapp):
    saver = DocumentSaver(writer=lambda capture: "")
    announced = []
    saver.idle.connect(lambda: announced.append(1))
    saver.submit(_capture(revision=1))
    saver.submit(_capture(revision=2))
    _drain(qapp, saver)
    assert announced == [1]
