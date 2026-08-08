import os

from dotenv import load_dotenv

load_dotenv()

_required = ["BOT_TOKEN", "HIDDIFY_URL", "HIDDIFY_PROXY_PATH",
             "HIDDIFY_USER_PATH", "HIDDIFY_ADMIN_UUID", "ADMIN_IDS"]
_missing = [k for k in _required if k not in os.environ]
if _missing:
    raise SystemExit(f"Missing required env vars: {', '.join(_missing)}. See .env.example")

BOT_TOKEN = os.environ["BOT_TOKEN"]

HIDDIFY_URL = os.environ["HIDDIFY_URL"].rstrip("/")
HIDDIFY_PROXY_PATH = os.environ["HIDDIFY_PROXY_PATH"]
HIDDIFY_USER_PATH = os.environ["HIDDIFY_USER_PATH"]
HIDDIFY_ADMIN_UUID = os.environ["HIDDIFY_ADMIN_UUID"]

ADMIN_IDS = set(int(x.strip()) for x in os.environ["ADMIN_IDS"].split(","))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")

QR_API_URL = os.environ.get("QR_API_URL", "https://api.qrserver.com/v1/create-qr-code/")

HIDDIFY_VERIFY_SSL = os.environ.get("HIDDIFY_VERIFY_SSL", "false").lower() == "true"
