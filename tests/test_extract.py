import types

import pytest
import requests

from pipeline import extract

SETTINGS = types.SimpleNamespace(max_retries=3, retry_base_seconds=0.5, request_timeout=5, max_retry_wait_seconds=60)


class FakeResponse:
    def __init__(self, status, body=None, headers=None, text=""):
        self.status_code, self._body, self.headers, self.text = status, body, headers or {}, text

    def json(self):
        if self._body is None:
            raise ValueError("not json")
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0

    def get(self, url, params=None, timeout=None):
        assert timeout is not None                     # every request carries a timeout
        self.calls += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def sleeps(monkeypatch):
    waits = []
    monkeypatch.setattr(extract.time, "sleep", waits.append)
    return waits


def _get(session, log):
    return extract.http_get_with_retry(session, "http://x/api", params={"api_key": "SECRET123"}, settings=SETTINGS,
                                       logger=log, label="T")


def test_5xx_is_retried_with_exponential_backoff(sleeps, log):
    s = FakeSession([FakeResponse(500), FakeResponse(503), FakeResponse(200, {})])
    assert _get(s, log).status_code == 200 and s.calls == 3 and sleeps == [0.5, 1.0]


def test_429_honours_retry_after_seconds_and_http_dates(sleeps, log):
    s = FakeSession([FakeResponse(429, {"retry_after_seconds": 2}),
                     FakeResponse(429, None, {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}),   # a date in the past
                     FakeResponse(200, {})])
    _get(s, log)
    assert sleeps == [2.0, 0.0]


def test_server_requested_wait_is_capped(sleeps, log):
    _get(FakeSession([FakeResponse(429, {"retry_after_seconds": 3600}), FakeResponse(200, {})]), log)
    assert sleeps == [60]


def test_4xx_is_not_retried(sleeps, log):
    s = FakeSession([FakeResponse(404, text="not found")])
    with pytest.raises(extract.RetrievalError, match="non-retryable status 404"):
        _get(s, log)
    assert s.calls == 1 and sleeps == []


def test_retries_are_bounded_and_do_not_wait_after_the_last_attempt(sleeps, log):
    s = FakeSession([FakeResponse(503)] * 3)
    with pytest.raises(extract.RetrievalError, match="after 3 attempts"):
        _get(s, log)
    assert s.calls == 3 and sleeps == [0.5, 1.0]


def test_api_key_never_reaches_logs_or_error_messages(sleeps, log, caplog):
    leak = requests.ConnectionError("Max retries exceeded with url: /api?api_key=SECRET123&fuel_type=ELEC")
    with caplog.at_level("WARNING", logger="tests"), pytest.raises(extract.RetrievalError) as exc:
        _get(FakeSession([leak] * 3), log)
    assert "SECRET123" not in str(exc.value) and "SECRET123" not in caplog.text and "api_key=***" in caplog.text
