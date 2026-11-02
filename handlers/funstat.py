from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from states import OsintState
from services.funstat_osint import run_funstat_osint

router = Router()

async def execute_funstat_osint(message: Message, target: str, state: FSMContext):
    await state.clear()
    status_msg = await message.answer(f"🔎 Querying Funstat / TeleLog database for `{target}`...")

    data, report = await run_funstat_osint(target)
    if "error" in data:
        await status_msg.edit_text(f"❌ {data['error']}")
        return

    await status_msg.delete()
    await message.answer(f"⚡ Funstat Telegram Intelligence: `{target}`\n\n{report}")


@router.message(Command("f"))
async def cmd_f(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        await execute_funstat_osint(message, command.args.strip(), state)
    else:
        await state.set_state(OsintState.waiting_for_funstat)
        await message.answer("⚡ Send a Telegram **@username** or **Numeric User ID** to query Funstat:")


@router.message(OsintState.waiting_for_funstat)
async def state_funstat(message: Message, state: FSMContext):
    await execute_funstat_osint(message, message.text.strip(), state)
