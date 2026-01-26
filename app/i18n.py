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

        "track_data": "📊 Data Analytics",
        "btn_track_data": "📊 Data Analytics",

        "mode_training": "🧪 Тренировка",
        "mode_real": "⏱ Как на реальном",
        "btn_mode_training": "🧪 Тренировка",
        "btn_mode_real": "⏱ Как на реальном",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "btn_lang_uk": "🇺🇦 Українська",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_cancel": "✖ Отмена",
        "cancel_ok": "Отменено ✅ /start чтобы начать заново",
        "cancelled": "Отменено ✅ /start чтобы начать заново",
        "session_not_found": "Сессия не найдена. Нажми /start чтобы начать заново.",

        "ask_vacancy": "Пришли текст вакансии одним сообщением ИЛИ ссылку на вакансию.",
        "vacancy_fetching": "Ок, пробую прочитать вакансию по ссылке (это может занять 5–15 сек)...",
        "vacancy_fetch_failed": "Не смогла вытащить текст по ссылке 😕\nПожалуйста, вставь текст вакансии одним сообщением.",
        "vacancy_still_pending": "Я всё ещё читаю вакансию… Если долго — просто вставь текст вакансии одним сообщением.",
        "vacancy_need_text": "Я не смогла прочитать вакансию по ссылке 😕\nПожалуйста, вставь текст вакансии одним сообщением.",

        "ask_cv": "Теперь пришли резюме: текстом или файлом (PDF/DOCX).",
        "cv_received_wait_vacancy": "Резюме сохранено ✅ Я ещё читаю вакансию по ссылке. Начну интервью автоматически.",
        "cv_pdf_only": "Пока поддерживаю только PDF/DOCX. Либо пришли резюме текстом.",
        "cv_pdf_no_text": "В файле не нашла текст (возможно, это скан). Пришли резюме текстом, пожалуйста.",
        # legacy alias
        "cv_pdf_empty": "В файле не нашла текст (возможно, это скан). Пришли резюме текстом или .docx, пожалуйста.",
        "cv_too_short": "Резюме слишком короткое. Пришли полный текст или файл.",

        # --- trial questions ---
        "q1": "Вопрос 1/3:\nКак бы ты посчитала retention D7? Какие данные нужны?",
        # legacy alias
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

        "language_updated": "✅ Язык изменён",
        "mode_updated": "✅ Режим изменён",

        "help": "Это тренажёр интервью под вакансию.\nTrial: 3 вопроса + snapshot.\nДальше подключим LLM и полноценный прогон.",
    },

    "uk": {
        # --- wizard ---
        "choose_track": "Оберіть напрям:",
        "choose_lang": "Оберіть мову спілкування:",
        "choose_mode": "Оберіть режим:",

        "track_data": "📊 Data Analytics",
        "btn_track_data": "📊 Data Analytics",

        "mode_training": "🧪 Тренування",
        "mode_real": "⏱ Як на реальному",
        "btn_mode_training": "🧪 Тренування",
        "btn_mode_real": "⏱ Як на реальному",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "btn_lang_uk": "🇺🇦 Українська",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_cancel": "✖ Скасувати",
        "cancel_ok": "Скасовано ✅ /start щоб почати заново",
        "cancelled": "Скасовано ✅ /start щоб почати заново",
        "session_not_found": "Сесію не знайдено. Натисніть /start щоб почати заново.",

        "ask_vacancy": "Надішли текст вакансії одним повідомленням АБО посилання на вакансію.",
        "vacancy_fetching": "Ок, читаю вакансію за посиланням (5–15 сек)...",
        "vacancy_fetch_failed": "Не вдалося прочитати вакансію за посиланням 😕\nБудь ласка, надішли текст вакансії одним повідомленням.",
        "vacancy_still_pending": "Я все ще читаю вакансію… Якщо довго — просто надішли текст вакансії одним повідомленням.",
        "vacancy_need_text": "Я не зміг прочитати вакансію за посиланням 😕\nБудь ласка, надішли текст вакансії одним повідомленням.",

        "ask_cv": "Тепер надішли резюме: текстом або файлом (PDF/DOCX).",
        "cv_received_wait_vacancy": "Резюме збережено ✅ Я ще читаю вакансію за посиланням. Почну інтерв’ю автоматично.",
        "cv_pdf_only": "Поки підтримую тільки PDF/DOCX. Або надішли резюме текстом.",
        "cv_pdf_no_text": "У файлі не знайшов текст (можливо, скан). Надішли резюме текстом, будь ласка.",
        # legacy alias
        "cv_pdf_empty": "Не вдалося витягти текст із PDF (можливо, це скан).\nНадішли резюме текстом або .docx.",
        "cv_too_short": "Резюме занадто коротке. Надішли повний текст або файл.",

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

        "language_updated": "✅ Мову змінено",
        "mode_updated": "✅ Режим змінено",

        "help": "Це тренажер інтерв'ю під вакансію.\nTrial: 3 питання + snapshot.\nДалі підключимо LLM і повноцінний прогін.",
    },

    "en": {
        # --- wizard ---
        "choose_track": "Choose a track:",
        "choose_lang": "Choose language:",
        "choose_mode": "Choose mode:",

        "track_data": "📊 Data Analytics",
        "btn_track_data": "📊 Data Analytics",

        "mode_training": "🧪 Training",
        "mode_real": "⏱ Real mode",
        "btn_mode_training": "🧪 Training",
        "btn_mode_real": "⏱ Real mode",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",
        "btn_lang_uk": "🇺🇦 Українська",
        "btn_lang_ru": "🇷🇺 Русский",
        "btn_lang_en": "🇬🇧 English",

        "btn_cancel": "✖ Cancel",
        "cancel_ok": "Cancelled ✅ /start to begin again",
        "cancelled": "Cancelled ✅ /start to begin again",
        "session_not_found": "Session not found. Use /start to begin again.",

        "ask_vacancy": "Send the vacancy text in one message OR a vacancy link.",
        "vacancy_fetching": "Ok, fetching vacancy from the link (5–15 sec)...",
        "vacancy_fetch_failed": "Couldn't extract the vacancy text from that link 😕\nPlease paste the vacancy text in one message.",
        "vacancy_still_pending": "Still fetching the vacancy… If it takes too long, just paste the vacancy text in one message.",
        "vacancy_need_text": "I couldn't read the vacancy from that link 😕\nPlease paste the vacancy text in one message.",

        "ask_cv": "Now send your resume: as text or a file (PDF/DOCX).",
        "cv_received_wait_vacancy": "Resume saved ✅ I'm still fetching the vacancy from the link. I'll start the interview automatically.",
        "cv_pdf_only": "Currently supported formats: PDF/DOCX. Or send resume as text.",
        "cv_pdf_no_text": "Couldn't find text in the file (might be a scanned image). Please send resume as text.",
        # legacy alias
        "cv_pdf_empty": "Couldn't extract text from the PDF (might be a scanned image).\nPlease send the resume as text or .docx.",
        "cv_too_short": "Resume is too short. Please send the full text or a file.",

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

        "language_updated": "✅ Language updated",
        "mode_updated": "✅ Mode updated",

        "help": "This is a vacancy-specific interview trainer.\nTrial: 3 questions + snapshot.\nNext: LLM-based full run.",
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
