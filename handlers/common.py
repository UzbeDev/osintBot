from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from states import OsintState
from keyboards import main_menu_keyboard

router = Router()

@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🕵️ **OSINT Telegram Bot Suite**\n\n"
        "Select a module from the menu or use direct shortcut commands:\n\n"
        "• `/u [username]` — Scan Target Username (Sherlock + Maigret)\n"
        "• `/g [email]` — Investigate Email / Gmail (Holehe + DNS + Gravatar)\n"
        "• `/p [phone]` — Trace Phone Number (Ignorant + libphonenumber)\n"
        "• `/f [username/id]` — Funstat Telegram Intel (Names & Group history)",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("opt_"))
async def handle_option(query: CallbackQuery, state: FSMContext):
    await query.answer()
    option = query.data.split("_")[1]

    if option == "username":
        await state.set_state(OsintState.waiting_for_username)
        await query.message.answer("🎯 Send the **Username** to scan (or use `/u <username>`):")
    elif option == "email":
        await state.set_state(OsintState.waiting_for_email)
        await query.message.answer("📧 Send the **Email Address** to investigate (or use `/g <email>`):")
    elif option == "phone":
        await state.set_state(OsintState.waiting_for_phone)
        await query.message.answer("📱 Send the **Phone Number** with country code (or use `/p <number>`):")
    elif option == "funstat":
        await state.set_state(OsintState.waiting_for_funstat)
        await query.message.answer("⚡ Send a Telegram **@username** or **Numeric User ID** (or use `/f <user>`):")
