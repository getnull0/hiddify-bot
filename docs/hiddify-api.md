# Hiddify panel API: what the bot relies on

Verified against the Hiddify-Panel v14.0.0b5 source. Re-check these when the panel is upgraded.

## Authentication and addressing

- The panel decides the account type from the **proxy path in the URL**. Admin endpoints live under `/<admin_path>/api/v2/admin/...` and need the admin UUID in the `Hiddify-API-Key` header.
- Per-user endpoints (`/user/me/`, `/user/mtproxies/`, ...) live under the **client** path and treat the user's UUID as the key. The admin key is rejected there (403), but the UUID can sit **in the URL path**: `/<client_path>/<uuid>/api/v2/user/me/`, no header needed. The bot knows every user's UUID, so it uses this for optional extras (see below). The core features still go through admin endpoints, and the subscription link is built locally: `{HIDDIFY_URL}/{HIDDIFY_USER_PATH}/{uuid}/`. (This was long mistaken for a v11 bug.)
- Errors are JSON `{"message": ..., "detail": ...}`. A wrong key or role answers 403 `Unathorized`; a wrong proxy path answers **400 `invalid request`**.
- A freshly initialised panel already contains one user named `default`.

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

## Optional extras (must degrade gracefully)

| Call | Used for |
|---|---|
| `GET /<client>/<uuid>/api/v2/user/me/` | `profile_reset_days` (the panel reports 10000 for no-reset users) and `telegram_proxy_enable` |
| `GET /<client>/<uuid>/api/v2/user/mtproxies/` | `tg://proxy` links; 404 when the admin has not enabled the Telegram proxy |
| `GET /admin/dashboard/` | statistics: users online (`m5`, `h24`, `today`), traffic totals in bytes with trends in percent, 30-day series |
| `GET /admin/nodes/` (+ `/{id}/ping/`, `POST /{id}/sync/`) | remote servers; each row carries `admin_url`, which embeds the admin's secret UUID and must never be shown |

Not used: `/user/short/` and `/user/apps/` (they failed on a minimal panel without Hiddify-Manager, so unverified), protocol toggles and settings (a change can disconnect everyone).

## Semantics that shape the bot

- `is_active` is `enable and usage_limit >= usage and remaining_days >= 0`. **A zero limit does not block a user who has used nothing**, so the bot blocks with `enable=False` (the panel drops the client from the proxy cores immediately).
- `remaining_days` is `package_days - days since start_date`; `start_date` stays `null` until the first connection. Extending therefore uses `max(package_days, elapsed) + days` so an expired package comes back to life.
- `telegram_id` and `comment` can be set but not cleared through the API (the panel ignores falsy values).
- `server_status.usage_history.total.users` counts soft-deleted users and `total.online` means "seen in the last 10 years", so the bot does not show them; the dashboard has the accurate counts.
- `usage_limit_GB` is capped by the panel at 1,000,000.
- Dates: `start_date` is `YYYY-MM-DD`; `last_online` is `YYYY-MM-DD HH:MM:SS`, with `0001-...` meaning never.
