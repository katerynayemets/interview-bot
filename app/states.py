from aiogram.fsm.state import State, StatesGroup


class InterviewFSM(StatesGroup):
    # Wizard: настройки
    choose_track = State()
    choose_lang = State()
    choose_mode = State()
    choose_interview_type = State()  # NEW: hr_soft | technical_hard | mixed
    choose_difficulty = State()  # NEW: junior | middle | senior | lead

    # Сбор данных
    waiting_vacancy = State()
    waiting_cv = State()

    # Интервью (legacy trial)
    q1 = State()
    q2 = State()
    q3 = State()

    # Генерация отчета
    generating = State()

    # NEW: Динамические фазы интервью с LLM
    interview_phase = State()  # активная фаза интервью
    interview_feedback = State()  # оценка пользователем
