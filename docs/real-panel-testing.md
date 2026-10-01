# Running the real Hiddify panel locally

The fake panel in `tests/fakes/panel.py` is an interpretation of the panel source. To check it against the real thing (for example after a panel upgrade), run the actual panel code and point the bot's client at it. This recipe worked for v14.0.0b5.

## Requirements

- Python 3.13 (the panel requires it; `uv python install 3.13` works), a Redis server, **MySQL 8** (MariaDB fails: the panel creates a stored procedure with a `JSON` parameter), `wg` (wireguard-tools) and `ssh-keygen` (openssh-client) on `PATH`.
- Clone `hiddify/Hiddify-Panel` and install its dependencies from `pyproject.toml` except `mysqlclient`; the pure-Python `pymysql` driver is enough.

## Configuration

Create a directory with `data/hiddify-panel/app.cfg` and `data/log/system/`, and set `HIDDIFY_CFG_PATH` to the cfg file:

```
SQLALCHEMY_DATABASE_URI='mysql+pymysql://USER:PASS@127.0.0.1:3307/DB?charset=utf8mb4&client_flag=65536'
HIDDIFY_CONFIG_PATH=/path/to/that/directory/
SECRET_KEY=any
USER_SECRET=any
STDOUT_LOG_LEVEL=WARNING
```

`client_flag=65536` enables multi-statements; the panel sends `DROP PROCEDURE ...; CREATE PROCEDURE ...` in one query. Also export `REDIS_URI_MAIN=redis://127.0.0.1:PORT/0`. Start `mysqld` with `--no-defaults` if leftover MariaDB config interferes.

## Starting it

`create_app_wsgi()` picks CLI or web mode from `sys.argv`, so call `create_app(app_mode="web")` yourself and run the Flask app. Creating the app initialises the schema and a super admin. Read the credentials in an app context:

```python
AdminUser.get_super_admin_uuid()  # HIDDIFY_ADMIN_UUID
hconfig(ConfigEnum.proxy_path_admin)  # HIDDIFY_PROXY_PATH
hconfig(ConfigEnum.proxy_path_client)  # HIDDIFY_USER_PATH
```

Then run `make smoke-write` with `HIDDIFY_URL=http://127.0.0.1:PORT` and those three values.
