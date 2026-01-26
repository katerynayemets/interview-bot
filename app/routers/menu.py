from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from app.i18n import tr, DEFAULT_LANG
from app.db.session import SessionLocal
from app.db import crud

router = Router()


async def resolve_lang(state: FSMContext, chat_id: int) -> str:
    data = await state.get_data()
    if data.get("lang"):
        return data["lang"]

    async with SessionLocal() as db:
        us = await crud.ensure_user_settings(db, chat_id)
        lang = us.language or DEFAULT_LANG

    await state.update_data(lang=lang)
    return lang


def lang_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=tr(lang, "lang_uk"), callback_data="set:lang:uk"),
        InlineKeyboardButton(text=tr(lang, "lang_ru"), callback_data="set:lang:ru"),
        InlineKeyboardButton(text=tr(lang, "lang_en"), callback_data="set:lang:en"),
    ]])


def mode_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang, "mode_training"), callback_data="set:mode:training")],
        [InlineKeyboardButton(text=tr(lang, "mode_real"), callback_data="set:mode:real")],
    ])


@router.message(StateFilter("*"), Command("help"))
async def help_cmd(msg: Message, state: FSMContext):
    lang = await resolve_lang(state, msg.chat.id)
    await msg.answer(tr(lang, "help"))


@router.message(StateFilter("*"), Command("settings"))
async def settings_cmd(msg: Message, state: FSMContext):
    lang = await resolve_lang(state, msg.chat.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang, "btn_lang"), callback_data="settings:lang")],
        [InlineKeyboardButton(text=tr(lang, "btn_mode"), callback_data="settings:mode")],
    ])
    await msg.answer(tr(lang, "settings"), reply_markup=kb)


@router.message(StateFilter("*"), Command("language"))
async def language_cmd(msg: Message, state: FSMContext):
    lang = await resolve_lang(state, msg.chat.id)
    await msg.answer(tr(lang, "choose_lang"), reply_markup=lang_kb(lang))


@router.message(StateFilter("*"), Command("mode"))
async def mode_cmd(msg: Message, state: FSMContext):
    lang = await resolve_lang(state, msg.chat.id)
    await msg.answer(tr(lang, "choose_mode"), reply_markup=mode_kb(lang))


@router.message(StateFilter("*"), Command("cancel"))
async def cancel_cmd(msg: Message, state: FSMContext):
    await state.set_state(None)
    lang = await resolve_lang(state, msg.chat.id)
    await msg.answer(tr(lang, "cancelled"))


@router.callback_query(lambda c: c.data == "settings:lang")
async def settings_lang(cb: CallbackQuery, state: FSMContext):
    lang = await resolve_lang(state, cb.message.chat.id)
    await cb.message.answer(tr(lang, "choose_lang"), reply_markup=lang_kb(lang))
    await cb.answer()


@router.callback_query(lambda c: c.data == "settings:mode")
async def settings_mode(cb: CallbackQuery, state: FSMContext):
    lang = await resolve_lang(state, cb.message.chat.id)
    await cb.message.answer(tr(lang, "choose_mode"), reply_markup=mode_kb(lang))
    await cb.answer()


@router.callback_query(lambda c: c.data.startswith("set:lang:"))
async def set_lang(cb: CallbackQuery, state: FSMContext):
    lang = cb.data.split(":")[-1]
    await state.update_data(lang=lang)

    async with SessionLocal() as db:
        await crud.update_user_language(db, cb.message.chat.id, lang)
        s = await crud.get_latest_session(db, cb.message.chat.id)
        if s:
            await crud.update_session_language(db, s.id, lang)
        await db.commit()

    await cb.message.answer(tr(lang, "language_updated"))
    await cb.answer()


@router.callback_query(lambda c: c.data.startswith("set:mode:"))
async def set_mode(cb: CallbackQuery, state: FSMContext):
    mode = cb.data.split(":")[-1]
    await state.update_data(mode=mode)

    lang = await resolve_lang(state, cb.message.chat.id)

    async with SessionLocal() as db:
        await crud.update_user_mode(db, cb.message.chat.id, mode)
        s = await crud.get_latest_session(db, cb.message.chat.id)
        if s:
            await crud.update_session_mode(db, s.id, mode)
        await db.commit()

    await cb.message.answer(tr(lang, "mode_updated"))
    await cb.answer()
