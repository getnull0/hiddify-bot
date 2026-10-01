"""Test package; pins the settings before any application module reads the environment."""

import os

_DEFAULTS = {
    "BOT_TOKEN": "42:TEST",
    "HIDDIFY_URL": "http://panel.test",
    "HIDDIFY_PROXY_PATH": "adminpath",
    "HIDDIFY_USER_PATH": "userpath",
    "HIDDIFY_ADMIN_UUID": "00000000-0000-0000-0000-00000000aaaa",
    "ADMIN_IDS": "1001",
    "ADMIN_USERNAME": "support_admin",
}
# Forced, not defaulted: tests must not depend on the developer's shell or .env file.
os.environ.update(_DEFAULTS)
for _key in ("QR_API_URL", "HIDDIFY_VERIFY_SSL"):
    os.environ.pop(_key, None)
