import pytest

from config import DEFAULT_QR_API_URL, ConfigError, Settings, _load, _parse_admin_ids

BASE_ENV = {
    "BOT_TOKEN": "1:abc",
    "HIDDIFY_URL": "https://panel.example.com/",
    "HIDDIFY_PROXY_PATH": "/secretpath/",
    "HIDDIFY_USER_PATH": "client",
    "HIDDIFY_ADMIN_UUID": "uuid-1",
    "ADMIN_IDS": "10, 20",
}


def test_from_env_normalises_values():
    s = Settings.from_env(BASE_ENV)
    assert s.hiddify_url == "https://panel.example.com"
    assert s.proxy_path == "secretpath"
    assert s.api_base == "https://panel.example.com/secretpath/api/v2"
    assert s.admin_ids == {10, 20}
    assert s.qr_api_url == DEFAULT_QR_API_URL
    assert s.admin_username == ""
    assert s.verify_ssl is False


def test_optional_values():
    env = {
        **BASE_ENV,
        "ADMIN_USERNAME": " @boss ",
        "QR_API_URL": "https://qr.local/",
        "HIDDIFY_VERIFY_SSL": "TRUE",
    }
    s = Settings.from_env(env)
    assert s.admin_username == "boss"
    assert s.qr_api_url == "https://qr.local/"
    assert s.verify_ssl is True


def test_missing_vars_are_listed():
    with pytest.raises(ConfigError, match=r"BOT_TOKEN.*ADMIN_IDS"):
        Settings.from_env({**BASE_ENV, "BOT_TOKEN": "", "ADMIN_IDS": "  "})


@pytest.mark.parametrize("url", ["panel.example.com", "ftp://x.y", "https://"])
def test_bad_url_is_rejected(url):
    with pytest.raises(ConfigError, match="HIDDIFY_URL"):
        Settings.from_env({**BASE_ENV, "HIDDIFY_URL": url})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("1", {1}), ("1,2,", {1, 2}), (" 3 , 4 ,,", {3, 4}), ("5,5", {5})],
)
def test_parse_admin_ids(raw, expected):
    assert _parse_admin_ids(raw) == expected


@pytest.mark.parametrize("raw", ["abc", "1,x", ",,"])
def test_parse_admin_ids_rejects_garbage(raw):
    with pytest.raises(ConfigError):
        _parse_admin_ids(raw)


def test_load_exits_with_readable_message(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN")
    monkeypatch.setattr("config.load_dotenv", lambda: None)
    with pytest.raises(SystemExit, match="BOT_TOKEN"):
        _load()
