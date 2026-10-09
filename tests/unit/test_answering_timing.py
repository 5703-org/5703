"""Queue latency preserves the offsets observed from PostgreSQL sessions."""

from datetime import datetime

import pytest

from app.modules.answering.service import submission_delay_ms


@pytest.mark.parametrize(
    "submitted",
    [
        "2026-09-26T12:14:07.856395+10:00",
        "2026-09-25T21:14:07.856395-05:00",
        "2026-09-26T02:14:07.856395+00:00",
        "2026-09-26T02:14:07.856395",
    ],
)
def test_same_actual_submission_has_same_queue_delay(submitted):
    started = datetime.fromisoformat("2026-09-26T02:14:08.131475+00:00")
    assert submission_delay_ms(datetime.fromisoformat(submitted), started) == pytest.approx(275.080)
