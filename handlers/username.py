from aiogram import Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext

from states import OsintState
from services.username_osint import run_username_osint

router = Router()

async def execute_username_osint(message: Message, username: str, state: FSMContext):
    await state.clear()
    status_msg = await message.answer(
        f"⏳ Running **Sherlock** & **Maigret** for `{username}` in parallel threads...\nThis usually takes 30-60 seconds."
    )

    ai_summary, sherlock_out, maigret_out = await run_username_osint(username)

    await status_msg.edit_text("🤖 Synthesizing intelligence with Gemini AI...")

    report_text = f"📊 OSINT Intelligence Report: {username}\n\n{ai_summary}"
    try:
        await message.answer(report_text)
    except Exception:
        await message.answer(report_text[:4000])

    # Send raw logs as documents
    sherlock_file = BufferedInputFile(sherlock_out.encode("utf-8"), filename=f"sherlock_{username}.txt")
    maigret_file = BufferedInputFile(maigret_out.encode("utf-8"), filename=f"maigret_{username}.txt")

    await message.answer_document(document=sherlock_file, caption="📄 Raw Sherlock Output")
    await message.answer_document(document=maigret_file, caption="📄 Raw Maigret Output")


@router.message(Command("u"))
async def cmd_u(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        await execute_username_osint(message, command.args.strip(), state)
    else:
        await state.set_state(OsintState.waiting_for_username)
        await message.answer("🎯 Send the **Username** to scan:")


@router.message(OsintState.waiting_for_username)
async def state_username(message: Message, state: FSMContext):
    await execute_username_osint(message, message.text.strip(), state)
