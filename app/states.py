from aiogram.fsm.state import State, StatesGroup

class InterviewFSM(StatesGroup):
    choose_track = State()
    choose_lang = State()
    choose_mode = State()

    waiting_cv = State()
    waiting_vacancy = State()

    q1 = State()
    q2 = State()
    q3 = State()

    generating = State()
