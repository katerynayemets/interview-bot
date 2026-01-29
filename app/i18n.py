# app/i18n.py

DEFAULT_LANG = "uk"  # за замовчуванням українська

# Нотація:
# - lang_*/mode_*/track_* — legacy-ключі
# - btn_lang_*/btn_mode_*/btn_track_* — ключі для inline-кнопок у wizard (routers/start.py)

T = {
    "ru": {
        # --- wizard ---
        "choose_track": "Выбери направление:",
        "choose_lang": "Выбери язык общения:",
        "choose_mode": "Выбери режим:",
        "choose_interview_type": "Выбери тип интервью:",
        "choose_difficulty": "Выбери уровень сложности:",

        "track_data": "📊 Data Analytics",
        "btn_track_data": "📊 Data Analytics",

        "mode_training": "🧪 Тренировка",
        "mode_real": "⏱ Как на реальном",
        "btn_mode_training": "🧪 Тренировка",
        "btn_mode_real": "⏱ Как на реальном",

        # interview types
        "btn_interview_hr_soft": "👔 HR / Soft Skills",
        "btn_interview_technical": "💻 Техническое",
        "btn_interview_mixed": "🔀 Смешанное (рек.)",

        # difficulty levels
        "btn_difficulty_junior": "🌱 Junior",
        "btn_difficulty_middle": "🌿 Middle",
        "btn_difficulty_senior": "🌳 Senior",
        "btn_difficulty_lead": "👑 Lead",
        "difficulty_auto": "Уровень определён автоматически: {level}",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "btn_lang_uk": "🇺🇦 Українська",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_cancel": "✖ Отмена",
        "btn_skip": "⏭ Пропустить",
        "cancel_ok": "Отменено ✅ /start чтобы начать заново",
        "cancelled": "Отменено ✅ /start чтобы начать заново",
        "session_not_found": "Сессия не найдена. Нажми /start чтобы начать заново.",

        "ask_vacancy": "Пришли текст вакансии одним сообщением ИЛИ ссылку на вакансию.\n\nМожешь пропустить, если у тебя есть резюме.",
        "vacancy_fetching": "Ок, пробую прочитать вакансию по ссылке (это может занять 5–15 сек)...",
        "vacancy_fetch_failed": "Не смогла вытащить текст по ссылке 😕\nПожалуйста, вставь текст вакансии одним сообщением.",
        "vacancy_still_pending": "Я всё ещё читаю вакансию… Если долго — просто вставь текст вакансии одним сообщением.",
        "vacancy_need_text": "Я не смогла прочитать вакансию по ссылке 😕\nПожалуйста, вставь текст вакансии одним сообщением.",
        "vacancy_skipped": "Вакансия пропущена. Интервью будет основано на твоём резюме.",

        "ask_cv": "Теперь пришли резюме: текстом или файлом (PDF/DOCX).\n\nМожешь пропустить, если уже прислал вакансию.",
        "cv_received_wait_vacancy": "Резюме сохранено ✅ Я ещё читаю вакансию по ссылке. Начну интервью автоматически.",
        "cv_pdf_only": "Пока поддерживаю только PDF/DOCX. Либо пришли резюме текстом.",
        "cv_pdf_no_text": "В файле не нашла текст (возможно, это скан). Пришли резюме текстом, пожалуйста.",
        "cv_pdf_empty": "В файле не нашла текст (возможно, это скан). Пришли резюме текстом или .docx, пожалуйста.",
        "cv_too_short": "Резюме слишком короткое. Пришли полный текст или файл.",
        "cv_skipped": "Резюме пропущено. Интервью будет основано на вакансии.",
        "cv_anonymized": "Резюме сохранено ✅ (личные данные удалены)",

        "need_cv_or_vacancy": "Нужно прислать хотя бы что-то одно: резюме или вакансию.",

        # --- trial questions ---
        "q1": "Вопрос 1/3:\nКак бы ты посчитала retention D7? Какие данные нужны?",
        "trial_intro": "Вопрос 1/3:\nКак бы ты посчитала retention D7? Какие данные нужны?",
        "q2": "Вопрос 2/3:\nНапиши SQL: топ-3 продукта по выручке за последние 30 дней (orders: user_id, product_id, price, created_at).",
        "q3": "Вопрос 3/3:\nКонверсия упала на 10%. Какие 5 причин/проверок ты сделаешь в первую очередь?",

        "generating": "Принято ✅ Генерирую snapshot-отчёт (в фоне, через очередь)...",
        "snapshot_ready": "🧾 Snapshot готов:",

        # --- menu / settings ---
        "menu": "Меню:",
        "btn_trial": "🧪 Trial (бесплатно)",
        "btn_settings": "⚙️ Настройки",
        "btn_help": "❓ Помощь",

        "settings": "Настройки:",
        "btn_lang": "🌐 Язык",
        "btn_mode": "🎛 Режим",
        "btn_interview_type": "🎯 Тип интервью",
        "btn_difficulty": "📊 Уровень",

        "language_updated": "✅ Язык изменён",
        "mode_updated": "✅ Режим изменён",
        "interview_type_updated": "✅ Тип интервью изменён",
        "difficulty_updated": "✅ Уровень изменён",

        "help": "Это тренажёр интервью под вакансию.\nTrial: 3 вопроса + snapshot.\nДальше подключим LLM и полноценный прогон.",

        # --- LLM interview ---
        "interview_starting": "Отлично! Начинаем интервью. Я буду задавать вопросы один за другим.\nОтвечай текстом, когда будешь готов(а).",
        "question_label": "Вопрос",
        "llm_error": "Произошла ошибка при генерации вопроса. Попробуй ответить ещё раз или нажми /start.",
        "interview_finishing": "Интервью завершено! Генерирую подробный фидбек...",
        "interview_done": "Спасибо за интервью! Выше — твой подробный разбор.\nМожешь оценить интервью или начать новое.",
        "feedback_error": "Не удалось сгенерировать фидбек. Попробуй позже.",
        "feedback_empty": "Не удалось сгенерировать детальный отчёт.",
        "feedback_title": "Результаты интервью",
        "feedback_overall": "Общая оценка",
        "feedback_technical": "Техника",
        "feedback_communication": "Коммуникация",
        "feedback_problem_solving": "Решение проблем",
        "feedback_strengths": "Сильные стороны",
        "feedback_improvements": "Что улучшить",
        "feedback_topics": "Рекомендуем изучить",

        # timer
        "timer_warning": "Осталось {seconds} секунд на ответ!",
        "timer_expired": "Время на ответ вышло. Переходим к следующему вопросу.",

        # post-interview
        "btn_rate_interview": "Оценить интервью",
        "btn_new_interview": "Новое интервью",
        "rate_prompt": "Оцени интервью от 1 до 5:",
        "rate_thanks": "Спасибо за оценку!",
    },

    "uk": {
        # --- wizard ---
        "choose_track": "Оберіть напрям:",
        "choose_lang": "Оберіть мову спілкування:",
        "choose_mode": "Оберіть режим:",
        "choose_interview_type": "Оберіть тип інтерв'ю:",
        "choose_difficulty": "Оберіть рівень складності:",

        "track_data": "📊 Data Analytics",
        "btn_track_data": "📊 Data Analytics",

        "mode_training": "🧪 Тренування",
        "mode_real": "⏱ Як на реальному",
        "btn_mode_training": "🧪 Тренування",
        "btn_mode_real": "⏱ Як на реальному",

        # interview types
        "btn_interview_hr_soft": "👔 HR / Soft Skills",
        "btn_interview_technical": "💻 Технічне",
        "btn_interview_mixed": "🔀 Змішане (рек.)",

        # difficulty levels
        "btn_difficulty_junior": "🌱 Junior",
        "btn_difficulty_middle": "🌿 Middle",
        "btn_difficulty_senior": "🌳 Senior",
        "btn_difficulty_lead": "👑 Lead",
        "difficulty_auto": "Рівень визначено автоматично: {level}",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "btn_lang_uk": "🇺🇦 Українська",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_cancel": "✖ Скасувати",
        "btn_skip": "⏭ Пропустити",
        "cancel_ok": "Скасовано ✅ /start щоб почати заново",
        "cancelled": "Скасовано ✅ /start щоб почати заново",
        "session_not_found": "Сесію не знайдено. Натисніть /start щоб почати заново.",

        "ask_vacancy": "Надішли текст вакансії одним повідомленням АБО посилання на вакансію.\n\nМожеш пропустити, якщо є резюме.",
        "vacancy_fetching": "Ок, читаю вакансію за посиланням (5–15 сек)...",
        "vacancy_fetch_failed": "Не вдалося прочитати вакансію за посиланням 😕\nБудь ласка, надішли текст вакансії одним повідомленням.",
        "vacancy_still_pending": "Я все ще читаю вакансію… Якщо довго — просто надішли текст вакансії одним повідомленням.",
        "vacancy_need_text": "Я не зміг прочитати вакансію за посиланням 😕\nБудь ласка, надішли текст вакансії одним повідомленням.",
        "vacancy_skipped": "Вакансію пропущено. Інтерв'ю буде базуватися на твоєму резюме.",

        "ask_cv": "Тепер надішли резюме: текстом або файлом (PDF/DOCX).\n\nМожеш пропустити, якщо вже надіслав вакансію.",
        "cv_received_wait_vacancy": "Резюме збережено ✅ Я ще читаю вакансію за посиланням. Почну інтерв'ю автоматично.",
        "cv_pdf_only": "Поки підтримую тільки PDF/DOCX. Або надішли резюме текстом.",
        "cv_pdf_no_text": "У файлі не знайшов текст (можливо, скан). Надішли резюме текстом, будь ласка.",
        "cv_pdf_empty": "Не вдалося витягти текст із PDF (можливо, це скан).\nНадішли резюме текстом або .docx.",
        "cv_too_short": "Резюме занадто коротке. Надішли повний текст або файл.",
        "cv_skipped": "Резюме пропущено. Інтерв'ю буде базуватися на вакансії.",
        "cv_anonymized": "Резюме збережено ✅ (персональні дані видалено)",

        "need_cv_or_vacancy": "Потрібно надіслати хоча б щось одне: резюме або вакансію.",

        # --- trial questions ---
        "q1": "Питання 1/3:\nЯк би ти порахувала retention D7? Які дані потрібні?",
        "trial_intro": "Питання 1/3:\nЯк би ти порахувала retention D7? Які дані потрібні?",
        "q2": "Питання 2/3:\nНапиши SQL: топ-3 продукти за виручкою за останні 30 днів (orders: user_id, product_id, price, created_at).",
        "q3": "Питання 3/3:\nКонверсія впала на 10%. Які 5 причин/перевірок зробиш першими?",

        "generating": "Прийнято ✅ Генерую snapshot-звіт (у фоні, через чергу)...",
        "snapshot_ready": "🧾 Snapshot готовий:",

        # --- menu / settings ---
        "menu": "Меню:",
        "btn_trial": "🧪 Trial (безкоштовно)",
        "btn_settings": "⚙️ Налаштування",
        "btn_help": "❓ Допомога",

        "settings": "Налаштування:",
        "btn_lang": "🌐 Мова",
        "btn_mode": "🎛 Режим",
        "btn_interview_type": "🎯 Тип інтерв'ю",
        "btn_difficulty": "📊 Рівень",

        "language_updated": "✅ Мову змінено",
        "mode_updated": "✅ Режим змінено",
        "interview_type_updated": "✅ Тип інтерв'ю змінено",
        "difficulty_updated": "✅ Рівень змінено",

        "help": "Це тренажер інтерв'ю під вакансію.\nTrial: 3 питання + snapshot.\nДалі підключимо LLM і повноцінний прогін.",

        # --- LLM interview ---
        "interview_starting": "Чудово! Починаємо інтерв'ю. Я буду ставити питання одне за одним.\nВідповідай текстом, коли будеш готовий(а).",
        "question_label": "Питання",
        "llm_error": "Виникла помилка при генерації питання. Спробуй відповісти ще раз або натисни /start.",
        "interview_finishing": "Інтерв'ю завершено! Генерую детальний фідбек...",
        "interview_done": "Дякую за інтерв'ю! Вище — твій детальний розбір.\nМожеш оцінити інтерв'ю або почати нове.",
        "feedback_error": "Не вдалося згенерувати фідбек. Спробуй пізніше.",
        "feedback_empty": "Не вдалося згенерувати детальний звіт.",
        "feedback_title": "Результати інтерв'ю",
        "feedback_overall": "Загальна оцінка",
        "feedback_technical": "Техніка",
        "feedback_communication": "Комунікація",
        "feedback_problem_solving": "Вирішення проблем",
        "feedback_strengths": "Сильні сторони",
        "feedback_improvements": "Що покращити",
        "feedback_topics": "Рекомендуємо вивчити",

        # timer
        "timer_warning": "Залишилось {seconds} секунд на відповідь!",
        "timer_expired": "Час на відповідь вичерпано. Переходимо до наступного питання.",

        # post-interview
        "btn_rate_interview": "Оцінити інтерв'ю",
        "btn_new_interview": "Нове інтерв'ю",
        "rate_prompt": "Оціни інтерв'ю від 1 до 5:",
        "rate_thanks": "Дякую за оцінку!",
    },

    "en": {
        # --- wizard ---
        "choose_track": "Choose a track:",
        "choose_lang": "Choose language:",
        "choose_mode": "Choose mode:",
        "choose_interview_type": "Choose interview type:",
        "choose_difficulty": "Choose difficulty level:",

        "track_data": "📊 Data Analytics",
        "btn_track_data": "📊 Data Analytics",

        "mode_training": "🧪 Training",
        "mode_real": "⏱ Real mode",
        "btn_mode_training": "🧪 Training",
        "btn_mode_real": "⏱ Real mode",

        # interview types
        "btn_interview_hr_soft": "👔 HR / Soft Skills",
        "btn_interview_technical": "💻 Technical",
        "btn_interview_mixed": "🔀 Mixed (rec.)",

        # difficulty levels
        "btn_difficulty_junior": "🌱 Junior",
        "btn_difficulty_middle": "🌿 Middle",
        "btn_difficulty_senior": "🌳 Senior",
        "btn_difficulty_lead": "👑 Lead",
        "difficulty_auto": "Difficulty auto-detected: {level}",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "btn_lang_uk": "🇺🇦 Українська",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_cancel": "✖ Cancel",
        "btn_skip": "⏭ Skip",
        "cancel_ok": "Cancelled ✅ /start to begin again",
        "cancelled": "Cancelled ✅ /start to begin again",
        "session_not_found": "Session not found. Use /start to begin again.",

        "ask_vacancy": "Send the vacancy text in one message OR a vacancy link.\n\nYou can skip if you have a resume.",
        "vacancy_fetching": "Ok, fetching vacancy from the link (5–15 sec)...",
        "vacancy_fetch_failed": "Couldn't extract the vacancy text from that link 😕\nPlease paste the vacancy text in one message.",
        "vacancy_still_pending": "Still fetching the vacancy… If it takes too long, just paste the vacancy text in one message.",
        "vacancy_need_text": "I couldn't read the vacancy from that link 😕\nPlease paste the vacancy text in one message.",
        "vacancy_skipped": "Vacancy skipped. Interview will be based on your resume.",

        "ask_cv": "Now send your resume: as text or a file (PDF/DOCX).\n\nYou can skip if you already sent a vacancy.",
        "cv_received_wait_vacancy": "Resume saved ✅ I'm still fetching the vacancy from the link. I'll start the interview automatically.",
        "cv_pdf_only": "Currently supported formats: PDF/DOCX. Or send resume as text.",
        "cv_pdf_no_text": "Couldn't find text in the file (might be a scanned image). Please send resume as text.",
        "cv_pdf_empty": "Couldn't extract text from the PDF (might be a scanned image).\nPlease send the resume as text or .docx.",
        "cv_too_short": "Resume is too short. Please send the full text or a file.",
        "cv_skipped": "Resume skipped. Interview will be based on the vacancy.",
        "cv_anonymized": "Resume saved ✅ (personal data removed)",

        "need_cv_or_vacancy": "You need to provide at least one: resume or vacancy.",

        # --- trial questions ---
        "q1": "Q1/3:\nHow would you compute D7 retention? What data do you need?",
        "trial_intro": "Q1/3:\nHow would you compute D7 retention? What data do you need?",
        "q2": "Q2/3:\nWrite SQL: top-3 products by revenue in the last 30 days (orders: user_id, product_id, price, created_at).",
        "q3": "Q3/3:\nConversion dropped by 10%. What 5 checks would you do first?",

        "generating": "Got it ✅ Generating snapshot report (in background)...",
        "snapshot_ready": "🧾 Snapshot ready:",

        # --- menu / settings ---
        "menu": "Menu:",
        "btn_trial": "🧪 Trial (free)",
        "btn_settings": "⚙️ Settings",
        "btn_help": "❓ Help",

        "settings": "Settings:",
        "btn_lang": "🌐 Language",
        "btn_mode": "🎛 Mode",
        "btn_interview_type": "🎯 Interview type",
        "btn_difficulty": "📊 Difficulty",

        "language_updated": "✅ Language updated",
        "mode_updated": "✅ Mode updated",
        "interview_type_updated": "✅ Interview type updated",
        "difficulty_updated": "✅ Difficulty updated",

        "help": "This is a vacancy-specific interview trainer.\nTrial: 3 questions + snapshot.\nNext: LLM-based full run.",

        # --- LLM interview ---
        "interview_starting": "Great! Let's start the interview. I'll ask questions one by one.\nReply with text when you're ready.",
        "question_label": "Question",
        "llm_error": "Error generating a question. Try answering again or press /start.",
        "interview_finishing": "Interview complete! Generating detailed feedback...",
        "interview_done": "Thanks for the interview! Your detailed review is above.\nYou can rate the interview or start a new one.",
        "feedback_error": "Couldn't generate feedback. Try again later.",
        "feedback_empty": "Couldn't generate a detailed report.",
        "feedback_title": "Interview Results",
        "feedback_overall": "Overall score",
        "feedback_technical": "Technical",
        "feedback_communication": "Communication",
        "feedback_problem_solving": "Problem solving",
        "feedback_strengths": "Strengths",
        "feedback_improvements": "Areas to improve",
        "feedback_topics": "Recommended topics",

        # timer
        "timer_warning": "{seconds} seconds left to answer!",
        "timer_expired": "Time's up. Moving to the next question.",

        # post-interview
        "btn_rate_interview": "Rate interview",
        "btn_new_interview": "New interview",
        "rate_prompt": "Rate the interview from 1 to 5:",
        "rate_thanks": "Thanks for your rating!",
    },
}


def tr(lang: str, key: str) -> str:
    lang = (lang or DEFAULT_LANG).lower()
    if lang not in T:
        lang = DEFAULT_LANG

    if key in T[lang]:
        return T[lang][key]
    if key in T.get(DEFAULT_LANG, {}):
        return T[DEFAULT_LANG][key]
    if key in T.get("ru", {}):
        return T["ru"][key]
    return key
