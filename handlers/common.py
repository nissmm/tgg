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

    if is_admin or is_hr:
        await message.answer("Привет! Выберите действие:", reply_markup=main_menu_keyboard(is_admin, is_hr))
    else:
        await message.answer(
            "Привет! Вы зарегистрированы, но пока у вас нет доступа к функциям бота."
        )


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    is_admin = await IsChannelAdmin()(callback, callback.bot)
    is_hr = storage.is_hr(callback.from_user.id)
    await callback.message.edit_text("Выберите действие:", reply_markup=main_menu_keyboard(is_admin, is_hr))
    await callback.answer()


@router.callback_query(F.data == "cancel_fsm")
async def cancel_fsm(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    await state.clear()

    if current_state and current_state.startswith("NewHRRecord"):
        await callback.message.edit_text("Отменено.", reply_markup=hr_panel_keyboard())
    else:
        is_admin = await IsChannelAdmin()(callback, callback.bot)
        keyboard = admin_panel_keyboard() if is_admin else hr_panel_keyboard()
        await callback.message.edit_text("Отменено.", reply_markup=keyboard)
    await callback.answer()
