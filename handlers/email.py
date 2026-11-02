from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from states import OsintState
from services.email_osint import run_email_osint

router = Router()

async def execute_email_osint(message: Message, email: str, state: FSMContext):
    await state.clear()
    status_msg = await message.answer(f"🔍 Analyzing `{email}` via Holehe, DNS/MX & Gravatar...")

    ai_summary = await run_email_osint(email)

    report = f"📧 Email Intelligence Report: {email}\n\n{ai_summary}"
    await message.answer(report)


@router.message(Command("g"))
async def cmd_g(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        await execute_email_osint(message, command.args.strip(), state)
    else:
        await state.set_state(OsintState.waiting_for_email)
        await message.answer("📧 Send the **Email Address** to investigate (Gmail or custom domain):")


@router.message(OsintState.waiting_for_email)
async def state_email(message: Message, state: FSMContext):
    await execute_email_osint(message, message.text.strip(), state)
