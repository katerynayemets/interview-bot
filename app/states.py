from aiogram.fsm.state import State, StatesGroup


class InterviewFSM(StatesGroup):
    choose_track = State()
    choose_lang = State()
    choose_mode = State()
    choose_interview_type = State()  # hr_soft | technical_hard | mixed
    choose_difficulty = State()  # junior | middle | senior | lead

    waiting_vacancy = State()
    waiting_cv = State()

    q1 = State()
    q2 = State()
    q3 = State()

    generating = State()

    interview_phase = State()
    interview_feedback = State()
