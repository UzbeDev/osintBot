from aiogram.fsm.state import State, StatesGroup

class OsintState(StatesGroup):
    waiting_for_username = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_funstat = State()
