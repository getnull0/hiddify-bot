"""Multi-step input flows: create, edit limit or days, link a Telegram id, unblock with a limit."""

from collections.abc import Callable
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import hiddify_bot.services.user_service as svc
from hiddify_bot.formatters import texts
from hiddify_bot.handlers.users.states import CreateUser, EditUser, SetTgId, UnblockUser
from hiddify_bot.handlers.users.views import current_list_page, edit_card, reply_card
from hiddify_bot.keyboards.inline import admin_main_kb, fsm_cancel_kb, fsm_nav_kb
from hiddify_bot.utils.telegram import callback_arg, message_of, text_of
from hiddify_bot.utils.validation import (
    MAX_COMMENT_CHARS,
    MAX_DAYS,
    MAX_LIMIT_GB,
    parse_comment,
    parse_days,
    parse_limit_gb,
    parse_telegram_id,
)

router = Router()

DEFAULT_DAYS = 30
DEFAULT_LIMIT_GB = 50.0
_SKIP = "."

_PROMPT_NAME = "Введи имя нового пользователя:"
_PROMPT_DAYS = f"Количество дней (дефолт {DEFAULT_DAYS}, . — пропустить):"
_PROMPT_LIMIT = f"Лимит трафика GB (дефолт {DEFAULT_LIMIT_GB:.0f}, . — пропустить):"
_PROMPT_TG_ID = "Telegram ID (необязательно, . — пропустить):"
_BAD_LIMIT = f"❌ Нужно положительное число (до {MAX_LIMIT_GB:,} GB)".replace(",", " ")
_BAD_DAYS = f"❌ Нужно целое число дней от 1 до {MAX_DAYS}"
_BAD_TG_ID = "❌ Нужен числовой Telegram ID"

_BAD_COMMENT = f"❌ Заметка должна быть от 1 до {MAX_COMMENT_CHARS} символов"
_NAME_MAX = 64
# Editable user fields: how to parse the typed text and what to say when it is invalid
_EDIT_FIELDS: dict[str, tuple[Callable[[str], Any], str]] = {
    "usage_limit_GB": (parse_limit_gb, _BAD_LIMIT),
    "package_days": (parse_days, _BAD_DAYS),
    "comment": (parse_comment, _BAD_COMMENT),
}


# ── Cancel / back ─────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("fsm_cancel:"))
async def fsm_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    back_cb = callback_arg(cb)
    list_page = await current_list_page(state)
    await state.clear()
    if back_cb.startswith("user:"):
        user = await svc.get(back_cb.split(":", 1)[1])
        await state.update_data(list_page=list_page)
        await cb.answer("Отменено")
        await edit_card(cb, user, list_page)
        return
    await cb.answer("Отменено")
    await message_of(cb).edit_text(texts.ADMIN_MENU, reply_markup=admin_main_kb())


@router.callback_query(F.data == "fsm_back")
async def fsm_back(cb: CallbackQuery, state: FSMContext) -> None:
    current = await state.get_state()
    back_cb = (await state.get_data()).get("back_cb", "menu")
    await cb.answer()
    previous = {
        CreateUser.days.state: (CreateUser.name, _PROMPT_NAME, False),
        CreateUser.limit_gb.state: (CreateUser.days, _PROMPT_DAYS, True),
        CreateUser.tg_id.state: (CreateUser.limit_gb, _PROMPT_LIMIT, True),
    }.get(current)
    if previous is None:
        return
    target_state, prompt, has_prev = previous
    await state.set_state(target_state)
    await message_of(cb).edit_text(prompt, reply_markup=fsm_nav_kb(back_cb, has_prev=has_prev))


def _cancel_kb(data: dict[str, Any]) -> InlineKeyboardMarkup:
    return fsm_cancel_kb(data.get("back_cb", "menu"))


# ── Unblock with a new limit ──────────────────────────────────────────────────


@router.message(UnblockUser.limit_gb)
async def unblock_do(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    limit = parse_limit_gb(text_of(msg))
    if limit is None:
        await msg.answer(f"{_BAD_LIMIT}, попробуй ещё раз:", reply_markup=_cancel_kb(data))
        return
    user = await svc.unblock(data["uuid"], limit)
    await state.clear()
    await reply_card(msg, user, data.get("list_page", 0), note="✅ Разблокирован")


# ── Edit limit / days ─────────────────────────────────────────────────────────


async def _start_edit(cb: CallbackQuery, state: FSMContext, field: str, prompt: str) -> None:
    uuid = callback_arg(cb)
    await cb.answer()
    await state.set_state(EditUser.waiting)
    await state.update_data(uuid=uuid, field=field, back_cb=f"user:{uuid}")
    await message_of(cb).edit_text(prompt, reply_markup=fsm_cancel_kb(f"user:{uuid}"))


@router.callback_query(F.data.startswith("user_set_limit:"))
async def set_limit_start(cb: CallbackQuery, state: FSMContext) -> None:
    await _start_edit(cb, state, "usage_limit_GB", "Введи новый лимит трафика в GB (например: 50):")


@router.callback_query(F.data.startswith("user_set_comment:"))
async def set_comment_start(cb: CallbackQuery, state: FSMContext) -> None:
    await _start_edit(
        cb,
        state,
        "comment",
        "Введи заметку к пользователю (до 200 символов).\n"
        "Панель не позволяет очистить заметку, только заменить её.",
    )


@router.callback_query(F.data.startswith("user_set_days:"))
async def set_days_start(cb: CallbackQuery, state: FSMContext) -> None:
    await _start_edit(cb, state, "package_days", "Введи количество дней (например: 30):")


@router.message(EditUser.waiting)
async def edit_value(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field = data["field"]
    parse, bad = _EDIT_FIELDS[field]
    value = parse(text_of(msg))
    if value is None:
        await msg.answer(f"{bad}, попробуй ещё раз:", reply_markup=_cancel_kb(data))
        return
    user = await svc.update(data["uuid"], **{field: value})
    await state.clear()
    await reply_card(msg, user, data.get("list_page", 0))


# ── Telegram id ───────────────────────────────────────────────────────────────


@router.callback_query(F.data.startswith("user_set_tgid:"))
async def set_tgid_start(cb: CallbackQuery, state: FSMContext) -> None:
    uuid = callback_arg(cb)
    await cb.answer()
    await state.set_state(SetTgId.waiting)
    await state.update_data(uuid=uuid, back_cb=f"user:{uuid}")
    await message_of(cb).edit_text(
        "Введи Telegram ID пользователя\n(числовой ID, например: 123456789):",
        reply_markup=fsm_cancel_kb(f"user:{uuid}"),
    )


@router.message(SetTgId.waiting)
async def set_tgid_do(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    tg_id = parse_telegram_id(text_of(msg))
    if tg_id is None:
        await msg.answer(f"{_BAD_TG_ID}, попробуй ещё раз:", reply_markup=_cancel_kb(data))
        return
    user = await svc.update(data["uuid"], telegram_id=tg_id)
    await state.clear()
    await reply_card(msg, user, data.get("list_page", 0), note=f"✅ Telegram ID {tg_id} привязан.")


# ── Create ────────────────────────────────────────────────────────────────────


@router.callback_query(F.data == "user_create")
async def create_start(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.set_state(CreateUser.name)
    await state.update_data(back_cb="menu")
    await message_of(cb).edit_text(_PROMPT_NAME, reply_markup=fsm_nav_kb("menu", has_prev=False))


@router.message(CreateUser.name)
async def create_name(msg: Message, state: FSMContext) -> None:
    name = text_of(msg)
    if not name or len(name) > _NAME_MAX:
        await msg.answer(
            f"❌ Имя должно быть от 1 до {_NAME_MAX} символов:",
            reply_markup=fsm_nav_kb("menu", has_prev=False),
        )
        return
    await state.update_data(name=name)
    await state.set_state(CreateUser.days)
    await msg.answer(_PROMPT_DAYS, reply_markup=fsm_nav_kb("menu", has_prev=True))


@router.message(CreateUser.days)
async def create_days(msg: Message, state: FSMContext) -> None:
    raw = text_of(msg)
    days = DEFAULT_DAYS if raw == _SKIP else parse_days(raw)
    if days is None:
        await msg.answer(
            f"{_BAD_DAYS} или . для пропуска:", reply_markup=fsm_nav_kb("menu", has_prev=True)
        )
        return
    await state.update_data(days=days)
    await state.set_state(CreateUser.limit_gb)
    await msg.answer(_PROMPT_LIMIT, reply_markup=fsm_nav_kb("menu", has_prev=True))


@router.message(CreateUser.limit_gb)
async def create_limit(msg: Message, state: FSMContext) -> None:
    raw = text_of(msg)
    limit = DEFAULT_LIMIT_GB if raw == _SKIP else parse_limit_gb(raw)
    if limit is None:
        await msg.answer(
            f"{_BAD_LIMIT} или . для пропуска:", reply_markup=fsm_nav_kb("menu", has_prev=True)
        )
        return
    await state.update_data(limit_gb=limit)
    await state.set_state(CreateUser.tg_id)
    await msg.answer(_PROMPT_TG_ID, reply_markup=fsm_nav_kb("menu", has_prev=True))


@router.message(CreateUser.tg_id)
async def create_tg_id(msg: Message, state: FSMContext) -> None:
    raw = text_of(msg)
    tg_id = None if raw == _SKIP else parse_telegram_id(raw)
    if raw != _SKIP and tg_id is None:
        await msg.answer(
            f"{_BAD_TG_ID} или . для пропуска:", reply_markup=fsm_nav_kb("menu", has_prev=True)
        )
        return
    data = await state.get_data()
    user = await svc.create(data["name"], data["days"], data["limit_gb"], tg_id)
    await state.clear()
    await reply_card(msg, user, note="✅ Создан!")
