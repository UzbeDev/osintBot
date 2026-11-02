from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from states import OsintState
from services.phone_osint import run_phone_osint

router = Router()

async def execute_phone_osint(message: Message, raw_phone: str, state: FSMContext):
    await state.clear()
    status_msg = await message.answer(f"🔎 Parsing & tracing phone number: `{raw_phone}`...")

    phone_data, ai_summary = await run_phone_osint(raw_phone)
    if "error" in phone_data:
        await status_msg.edit_text(f"❌ {phone_data['error']}")
        return

    await status_msg.delete()
    await message.answer(f"📱 Phone Intelligence Dossier:\n\n{ai_summary}")


@router.message(Command("p"))
async def cmd_p(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        await execute_phone_osint(message, command.args.strip(), state)
    else:
        await state.set_state(OsintState.waiting_for_phone)
        await message.answer("📱 Send the **Phone Number** with country code (e.g. `+998901234567` or `+14155552671`):")


@router.message(OsintState.waiting_for_phone)
async def state_phone(message: Message, state: FSMContext):
    await execute_phone_osint(message, message.text.strip(), state)
