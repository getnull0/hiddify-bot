# Hiddify panel API: what the bot relies on

Verified against the Hiddify-Panel v14.0.0b5 source. Re-check these when the panel is upgraded.

## Authentication and addressing

- The panel decides the account type from the **proxy path in the URL**. Admin endpoints live under `/<admin_path>/api/v2/admin/...` and need the admin UUID in the `Hiddify-API-Key` header.
- Per-user endpoints (`/user/me/`, `/user/short/`, ...) live under the **client** path and need the *user's own* UUID, so they cannot be used with the admin key. This is why the bot reads everything through admin endpoints and builds the subscription link itself: `{HIDDIFY_URL}/{HIDDIFY_USER_PATH}/{uuid}/`. (It was long mistaken for a v11 bug.)
- Wrong key, wrong role or wrong path answer 403 or 404 with a JSON body `{"message": ..., "detail": ...}`.

## Endpoints used

| Call | Notes |
|---|---|
| `GET /admin/user/` | Answers **404 "You have no user"** when the list is empty. The client turns that into `[]` after confirming credentials with `/admin/me/`. |
| `GET/PATCH/DELETE /admin/user/{uuid}/` | PATCH accepts partial bodies; DELETE is a soft delete. |
| `POST /admin/user/` | Fails with 400 once the admin's user limit is reached. |
| `GET /admin/server_status/` | `stats.system`, `stats.top5`, `usage_history`. |
| `GET /admin/update_user_usage/` | Super admin only; returns text. |
| `POST /admin/log/` | Super admin only; form field `file`; returns an HTML page that includes a `<style>` block. |
| `GET /admin/me/`, `GET /panel/info/` | Admin identity and panel version. |

## Semantics that shape the bot

- `is_active` is `enable and usage_limit >= usage and remaining_days >= 0`. **A zero limit does not block a user who has used nothing**, so the bot blocks with `enable=False` (the panel drops the client from the proxy cores immediately).
- `remaining_days` is `package_days - days since start_date`; `start_date` stays `null` until the first connection. Extending therefore uses `max(package_days, elapsed) + days` so an expired package comes back to life.
- `telegram_id` can be set but not cleared through the API (the panel ignores falsy values).
- `usage_limit_GB` is capped by the panel at 1,000,000.
- Dates: `start_date` is `YYYY-MM-DD`; `last_online` is `YYYY-MM-DD HH:MM:SS`, with `0001-...` meaning never.
