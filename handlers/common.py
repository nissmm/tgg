from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import storage
from filters import IsChannelAdmin
from keyboards import admin_panel_keyboard, hr_panel_keyboard, main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    storage.register_user(message.from_user.id, message.from_user.username)

    is_admin = await IsChannelAdmin()(message, message.bot)
    is_hr = storage.is_hr(message.from_user.id)

    await message.answer("Привет! Выберите действие:", reply_markup=main_menu_keyboard(is_admin, is_hr))


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.answer()
    is_admin = await IsChannelAdmin()(callback, callback.bot)
    is_hr = storage.is_hr(callback.from_user.id)
    await callback.message.edit_text("Выберите действие:", reply_markup=main_menu_keyboard(is_admin, is_hr))


@router.callback_query(F.data == "cancel_fsm")
async def cancel_fsm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    current_state = await state.get_state()
    data = await state.get_data()
    await state.clear()

    is_admin = await IsChannelAdmin()(callback, callback.bot)
    is_hr = storage.is_hr(callback.from_user.id)

    if current_state and current_state.startswith("SelfApply"):
        await callback.message.edit_text("Заявка отменена.", reply_markup=main_menu_keyboard(is_admin, is_hr))
    elif current_state and current_state.startswith("EditRecord"):
        keyboard = (
            admin_panel_keyboard()
            if data.get("admin_scope")
            else hr_panel_keyboard(storage.is_shift_active(callback.from_user.id))
        )
        await callback.message.edit_text("Отменено.", reply_markup=keyboard)
    elif current_state and current_state.startswith("SetPlan"):
        await callback.message.edit_text("Отменено.", reply_markup=admin_panel_keyboard())
    elif current_state and current_state.startswith("NewHRRecord"):
        await callback.message.edit_text(
            "Отменено.", reply_markup=hr_panel_keyboard(storage.is_shift_active(callback.from_user.id))
        )
    else:
        keyboard = (
            admin_panel_keyboard()
            if is_admin
            else hr_panel_keyboard(storage.is_shift_active(callback.from_user.id))
        )
        await callback.message.edit_text("Отменено.", reply_markup=keyboard)
