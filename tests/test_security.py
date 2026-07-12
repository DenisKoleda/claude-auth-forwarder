from gmail_monitor import GmailMonitor, extract_oauth_code


def test_oauth_callback_requires_matching_state() -> None:
    assert extract_oauth_code("http://localhost/?code=good&state=expected", "expected") == "good"
    assert extract_oauth_code("http://localhost/?code=evil&state=wrong", "expected") is None
    assert extract_oauth_code("http://localhost/?code=missing-state", "expected") is None


def test_auth_email_ttl(monkeypatch) -> None:
    monkeypatch.setattr("settings.AUTH_EMAIL_MAX_AGE_SECONDS", 900)
    monitor = GmailMonitor()
    assert monitor._is_stale("auth", 1000, now=1899) is False
    assert monitor._is_stale("auth", 1000, now=1901) is True
    assert monitor._is_stale("auth", 0, now=1000) is True
