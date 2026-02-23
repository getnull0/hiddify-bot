from urllib.parse import quote

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, URLInputFile

import services.user_service as svc
from filters.admin import IsAdmin
from formatters.user import user_card
from keyboards.inline import (
    admin_main_kb, users_list_kb, user_actions_kb,
    confirm_delete_kb, user_link_kb, user_mode_kb, generic_back_kb,
    fsm_cancel_kb, fsm_nav_kb, photo_close_kb,
)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ── FSM ───────────────────────────────────────────────────────────────────────

class CreateUser(StatesGroup):
    name    = State()
    days    = State()
    limit_gb = State()
    tg_id   = State()


class EditUser(StatesGroup):
    waiting = State()


class UnblockUser(StatesGroup):
    limit_gb = State()


class SetTgId(StatesGroup):
    waiting = State()


class SearchUser(StatesGroup):
    query = State()


# ── FSM: cancel / back ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fsm_cancel:"))
async def fsm_cancel(cb: CallbackQuery, state: FSMContext):
    back_cb = cb.data.split(":", 1)[1]
    await state.clear()
    await cb.answer("Отменено")
    if back_cb.startswith("user:"):
        uuid = back_cb.split(":", 1)[1]
        user = await svc.get(uuid)
        await cb.message.edit_text(
            user_card(user),
            reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
        )
    else:
        await cb.message.edit_text(
            "👋 <b>Hiddify Admin</b>\n\nВыбери действие:",
            reply_markup=admin_main_kb(),
        )


@router.callback_query(F.data == "fsm_back")
async def fsm_back(cb: CallbackQuery, state: FSMContext):
    current = await state.get_state()
    data = await state.get_data()
    back_cb = data.get("back_cb", "menu")
    await cb.answer()

    if current == CreateUser.days.state:
        await state.set_state(CreateUser.name)
        await cb.message.edit_text(
            "Введи имя нового пользователя:",
            reply_markup=fsm_nav_kb(back_cb, has_prev=False),
        )
    elif current == CreateUser.limit_gb.state:
        await state.set_state(CreateUser.days)
        await cb.message.edit_text(
            "Количество дней (дефолт 30, . — пропустить):",
            reply_markup=fsm_nav_kb(back_cb, has_prev=True),
        )
    elif current == CreateUser.tg_id.state:
        await state.set_state(CreateUser.limit_gb)
        await cb.message.edit_text(
            "Лимит трафика GB (дефолт 50, . — пропустить):",
            reply_markup=fsm_nav_kb(back_cb, has_prev=True),
        )


# ── List ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("users_list:"))
async def users_list(cb: CallbackQuery):
    page = int(cb.data.split(":")[1])
    await cb.answer()
    users = await svc.get_all()
    if not users:
        await cb.message.edit_text("Нет пользователей.", reply_markup=generic_back_kb())
        return
    await cb.message.edit_text(
        f"👥 <b>Пользователи</b> ({len(users)})\n\nВыбери для управления:",
        reply_markup=users_list_kb(users, page),
    )


# ── Card ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user:"))
async def user_detail(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    user = await svc.get(uuid)
    await cb.message.edit_text(
        user_card(user),
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


# ── Block / Unblock ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_block:"))
async def user_block(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer("⛔ Заблокирован")
    user = await svc.block(uuid)
    await cb.message.edit_text(
        user_card(user),
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


@router.callback_query(F.data.startswith("user_unblock:"))
async def user_unblock_start(cb: CallbackQuery, state: FSMContext):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    await state.set_state(UnblockUser.limit_gb)
    await state.update_data(uuid=uuid, back_cb=f"user:{uuid}")
    await cb.message.edit_text(
        "Введи новый лимит трафика в GB (например: 50):",
        reply_markup=fsm_cancel_kb(f"user:{uuid}"),
    )


@router.message(UnblockUser.limit_gb)
async def user_unblock_do(msg: Message, state: FSMContext):
    try:
        limit = float(msg.text.strip())
        if limit <= 0:
            raise ValueError
    except ValueError:
        await msg.answer(
            "❌ Нужно положительное число, попробуй ещё раз:",
            reply_markup=fsm_cancel_kb((await state.get_data()).get("back_cb", "menu")),
        )
        return
    data = await state.get_data()
    uuid = data["uuid"]
    try:
        user = await svc.unblock(uuid, limit)
    except Exception as e:
        await state.clear()
        await msg.answer(f"❌ Ошибка API: {e}", reply_markup=generic_back_kb())
        return
    await state.clear()
    await msg.answer(
        user_card(user),
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


# ── Reset traffic ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_reset:"))
async def user_reset(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer("🔄 Трафик сброшен")
    user = await svc.reset_traffic(uuid)
    await cb.message.edit_text(
        user_card(user),
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


# ── Extend ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_extend:"))
async def user_extend(cb: CallbackQuery):
    parts = cb.data.split(":")
    uuid, days = parts[1], int(parts[2])
    await cb.answer(f"⏱ +{days} дней")
    user = await svc.extend(uuid, days)
    await cb.message.edit_text(
        user_card(user),
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


# ── Edit limit / days ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_set_limit:"))
async def set_limit_start(cb: CallbackQuery, state: FSMContext):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    await state.set_state(EditUser.waiting)
    await state.update_data(uuid=uuid, field="usage_limit_GB", back_cb=f"user:{uuid}")
    await cb.message.edit_text(
        "Введи новый лимит трафика в GB (например: 50):",
        reply_markup=fsm_cancel_kb(f"user:{uuid}"),
    )


@router.callback_query(F.data.startswith("user_set_days:"))
async def set_days_start(cb: CallbackQuery, state: FSMContext):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    await state.set_state(EditUser.waiting)
    await state.update_data(uuid=uuid, field="package_days", back_cb=f"user:{uuid}")
    await cb.message.edit_text(
        "Введи количество дней (например: 30):",
        reply_markup=fsm_cancel_kb(f"user:{uuid}"),
    )


@router.message(EditUser.waiting)
async def edit_value(msg: Message, state: FSMContext):
    data = await state.get_data()
    uuid, field = data["uuid"], data["field"]
    try:
        value = float(msg.text.strip()) if field == "usage_limit_GB" else int(msg.text.strip())
    except ValueError:
        await msg.answer(
            "❌ Некорректное значение, попробуй ещё раз:",
            reply_markup=fsm_cancel_kb(data.get("back_cb", "menu")),
        )
        return
    try:
        user = await svc.update(uuid, **{field: value})
    except Exception as e:
        await state.clear()
        await msg.answer(f"❌ Ошибка API: {e}", reply_markup=generic_back_kb())
        return
    await state.clear()
    await msg.answer(
        user_card(user),
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


# ── Link ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_link:"))
async def user_link(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    from services.account_service import get_account
    data = await get_account(uuid)
    await cb.message.edit_text(
        f"🔑 <b>Ссылка подписки</b>\n\n"
        f"<code>{data['sub_url']}</code>\n\n"
        f"<i>Нажми на ссылку чтобы скопировать\n"
        f"или QR-код для сканирования</i>",
        reply_markup=user_link_kb(uuid),
    )


@router.callback_query(F.data.startswith("user_qr:"))
async def user_qr(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    from services.account_service import get_account
    data = await get_account(uuid)
    sub_url = data["sub_url"]
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&margin=10&data={quote(sub_url, safe='')}"
    await cb.message.answer_photo(
        URLInputFile(qr_url, filename="qr.png"),
        caption=f"📲 <b>QR-код подписки</b>\n\nИли скопируй ссылку:\n<code>{sub_url}</code>",
        reply_markup=photo_close_kb(),
    )


# ── Apps ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_apps:"))
async def user_apps(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    from keyboards.inline import apps_kb
    await cb.message.edit_text(
        "📱 <b>Приложения для подключения</b>\n\n"
        "Нажми на приложение — скачаешь и настроишь через «Импорт подписки».\n\n"
        "<b>Hiddify</b> — рекомендуем, поддерживает все протоколы.\n"
        "<b>v2rayNG / NekoBox</b> — Android-альтернативы.\n"
        "<b>Streisand</b> — лучший выбор для iOS.",
        reply_markup=apps_kb(back_cb=f"user:{uuid}", home_cb="menu"),
    )


# ── Set Telegram ID ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_set_tgid:"))
async def set_tgid_start(cb: CallbackQuery, state: FSMContext):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    await state.set_state(SetTgId.waiting)
    await state.update_data(uuid=uuid, back_cb=f"user:{uuid}")
    await cb.message.edit_text(
        "Введи Telegram ID пользователя\n(числовой ID, например: 123456789):",
        reply_markup=fsm_cancel_kb(f"user:{uuid}"),
    )


@router.message(SetTgId.waiting)
async def set_tgid_do(msg: Message, state: FSMContext):
    try:
        tg_id = int(msg.text.strip())
    except ValueError:
        await msg.answer(
            "❌ Нужен числовой Telegram ID, попробуй ещё раз:",
            reply_markup=fsm_cancel_kb((await state.get_data()).get("back_cb", "menu")),
        )
        return
    data = await state.get_data()
    uuid = data["uuid"]
    try:
        user = await svc.update(uuid, telegram_id=tg_id)
    except Exception as e:
        await state.clear()
        await msg.answer(f"❌ Ошибка API: {e}", reply_markup=generic_back_kb())
        return
    await state.clear()
    await msg.answer(
        f"✅ Telegram ID {tg_id} привязан.\n\n{user_card(user)}",
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


# ── Mode ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_set_mode:"))
async def set_mode_menu(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    await cb.message.edit_text(
        "🔁 Выбери режим сброса трафика:",
        reply_markup=user_mode_kb(uuid),
    )


@router.callback_query(F.data.startswith("user_mode:"))
async def set_mode_do(cb: CallbackQuery):
    _, uuid, mode = cb.data.split(":")
    mode_labels = {"monthly": "ежемесячно", "weekly": "еженедельно",
                   "daily": "ежедневно", "no_reset": "без сброса"}
    await cb.answer(f"✅ {mode_labels.get(mode, mode)}")
    user = await svc.update(uuid, mode=mode)
    await cb.message.edit_text(
        user_card(user),
        reply_markup=user_actions_kb(uuid, user.get("usage_limit_GB") or 0.0),
    )


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("user_delete_confirm:"))
async def delete_confirm(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer()
    await cb.message.edit_text(
        "⚠️ Удалить пользователя? Это необратимо.",
        reply_markup=confirm_delete_kb(uuid),
    )


@router.callback_query(F.data.regexp(r"^user_delete:[^_]"))
async def delete_do(cb: CallbackQuery):
    uuid = cb.data.split(":", 1)[1]
    await cb.answer("🗑 Удалён")
    await svc.delete(uuid)
    await cb.message.edit_text("✅ Пользователь удалён.", reply_markup=generic_back_kb(back_cb="users_list:0"))


# ── Create ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "user_create")
async def create_start(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(CreateUser.name)
    await state.update_data(back_cb="menu")
    await cb.message.edit_text(
        "Введи имя нового пользователя:",
        reply_markup=fsm_nav_kb("menu", has_prev=False),
    )


@router.message(CreateUser.name)
async def create_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    if not name or len(name) > 64:
        await msg.answer(
            "❌ Имя должно быть от 1 до 64 символов:",
            reply_markup=fsm_nav_kb("menu", has_prev=False),
        )
        return
    await state.update_data(name=name)
    await state.set_state(CreateUser.days)
    await msg.answer(
        "Количество дней (дефолт 30, . — пропустить):",
        reply_markup=fsm_nav_kb("menu", has_prev=True),
    )


@router.message(CreateUser.days)
async def create_days(msg: Message, state: FSMContext):
    raw = msg.text.strip()
    if raw == ".":
        days = 30
    else:
        try:
            days = int(raw)
        except ValueError:
            await msg.answer(
                "❌ Нужно целое число или . для пропуска:",
                reply_markup=fsm_nav_kb("menu", has_prev=True),
            )
            return
        if days <= 0:
            await msg.answer(
                "❌ Количество дней должно быть больше 0:",
                reply_markup=fsm_nav_kb("menu", has_prev=True),
            )
            return
    await state.update_data(days=days)
    await state.set_state(CreateUser.limit_gb)
    await msg.answer(
        "Лимит трафика GB (дефолт 50, . — пропустить):",
        reply_markup=fsm_nav_kb("menu", has_prev=True),
    )


@router.message(CreateUser.limit_gb)
async def create_limit(msg: Message, state: FSMContext):
    raw = msg.text.strip()
    if raw == ".":
        limit = 50.0
    else:
        try:
            limit = float(raw)
        except ValueError:
            await msg.answer(
                "❌ Нужно число или . для пропуска:",
                reply_markup=fsm_nav_kb("menu", has_prev=True),
            )
            return
        if limit <= 0:
            await msg.answer(
                "❌ Лимит должен быть больше 0 GB:",
                reply_markup=fsm_nav_kb("menu", has_prev=True),
            )
            return
    await state.update_data(limit_gb=limit)
    await state.set_state(CreateUser.tg_id)
    await msg.answer(
        "Telegram ID (необязательно, . — пропустить):",
        reply_markup=fsm_nav_kb("menu", has_prev=True),
    )


@router.message(CreateUser.tg_id)
async def create_tg_id(msg: Message, state: FSMContext):
    raw = msg.text.strip()
    if raw == ".":
        tg_id = None
    else:
        try:
            tg_id = int(raw)
        except ValueError:
            await msg.answer(
                "❌ Нужен числовой ID или . для пропуска:",
                reply_markup=fsm_nav_kb("menu", has_prev=True),
            )
            return
    data = await state.get_data()
    try:
        user = await svc.create(data["name"], data["days"], data["limit_gb"], tg_id)
    except Exception as e:
        await state.clear()
        await msg.answer(f"❌ Ошибка при создании: {e}", reply_markup=generic_back_kb())
        return
    await state.clear()
    await msg.answer(
        f"✅ Создан!\n\n{user_card(user)}",
        reply_markup=user_actions_kb(user["uuid"], user.get("usage_limit_GB") or 0.0),
    )


# ── Search ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "user_search")
async def search_start(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(SearchUser.query)
    await state.update_data(back_cb="menu")
    await cb.message.edit_text(
        "Введи имя, UUID или Telegram ID:",
        reply_markup=fsm_cancel_kb("menu"),
    )


@router.message(SearchUser.query)
async def search_do(msg: Message, state: FSMContext):
    query = msg.text.strip()
    results = await svc.search(query)
    await state.clear()
    if not results:
        await msg.answer(f"🔍 По запросу «{query}» ничего не найдено.", reply_markup=generic_back_kb())
        return
    if len(results) == 1:
        u = results[0]
        await msg.answer(user_card(u), reply_markup=user_actions_kb(u["uuid"], u.get("usage_limit_GB") or 0.0))
    else:
        await msg.answer(f"🔍 «{query}» — найдено: {len(results)}", reply_markup=users_list_kb(results, 0))
