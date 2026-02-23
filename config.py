import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]

HIDDIFY_URL = os.environ["HIDDIFY_URL"].rstrip("/")
HIDDIFY_PROXY_PATH = os.environ["HIDDIFY_PROXY_PATH"]
HIDDIFY_USER_PATH = os.environ["HIDDIFY_USER_PATH"]
HIDDIFY_ADMIN_UUID = os.environ["HIDDIFY_ADMIN_UUID"]

ADMIN_IDS = set(int(x.strip()) for x in os.environ["ADMIN_IDS"].split(","))

HIDDIFY_VERIFY_SSL = os.environ.get("HIDDIFY_VERIFY_SSL", "false").lower() == "true"
