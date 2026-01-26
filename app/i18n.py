# app/i18n.py

T = {
    "ru": {
        "choose_lang": "Выбери язык общения:",
        "choose_track": "Выбери направление:",
        "choose_mode": "Выбери режим:",

        "track_data": "📊 Data Analytics",

        "mode_training": "🧪 Тренировка",
        "mode_real": "⏱ Как на реальном",

        "menu": "Меню:",
        "btn_trial": "🧪 Trial (бесплатно)",
        "btn_settings": "⚙️ Настройки",
        "btn_help": "❓ Помощь",

        "settings": "Настройки:",
        "btn_lang": "🌐 Язык",
        "btn_mode": "🎛 Режим",

        "language_updated": "✅ Язык изменён",
        "mode_updated": "✅ Режим изменён",
        "cancelled": "Отменено ✅ /start чтобы начать заново",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",

        "ask_vacancy": "Пришли текст вакансии одним сообщением ИЛИ ссылку на вакансию.",
        "ask_cv": "Теперь пришли резюме: текстом или PDF-файлом.",

        "vacancy_fetching": "Ок, пробую прочитать вакансию по ссылке (это может занять 5–15 сек)...",
        "vacancy_fetch_failed": "Не смогла вытащить текст по ссылке 😕\nПожалуйста, вставь текст вакансии одним сообщением.",

        "cv_pdf_empty": "Я не смогла извлечь текст из PDF (возможно, это скан).\nПожалуйста, пришли резюме текстом или в формате .docx.",

        "trial_intro": "Поехали. Вопрос 1/3:\nКак бы ты посчитала retention D7? Какие данные нужны?",
        "q2": "Вопрос 2/3:\nНапиши SQL: топ-3 продукта по выручке за последние 30 дней (orders: user_id, product_id, price, created_at).",
        "q3": "Вопрос 3/3:\nКонверсия упала на 10%. Какие 5 причин/проверок ты сделаешь в первую очередь?",

        "generating": "Принято ✅ Генерирую snapshot-отчёт (фон, через очередь)...",

        "help": "Это тренажёр интервью под вакансию.\nTrial: 3 вопроса + snapshot.\nСкоро добавим full sprint и оплату.",
    },

    "uk": {
        "choose_lang": "беріть мову:",
        "choose_track": "Оберіть напрям:",
        "choose_mode": "Оберіть режим:",

        "track_data": "📊 Data Analytics",

        "mode_training": "🧪 Тренування",
        "mode_real": "⏱ Як на реальному",

        "menu": "Меню:",
        "btn_trial": "🧪 Trial (безкоштовно)",
        "btn_settings": "⚙️ Налаштування",
        "btn_help": "❓ Допомога",

        "settings": "Налаштування:",
        "btn_lang": "🌐 Мова",
        "btn_mode": "🎛 Режим",

        "language_updated": "✅ Мову змінено",
        "mode_updated": "✅ Режим змінено",
        "cancelled": "Скасовано ✅ /start щоб почати заново",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",

        "ask_vacancy": "Надішли текст вакансії одним повідомленням АБО посилання на вакансію.",
        "ask_cv": "Тепер надішли резюме: текстом або PDF-файлом.",

        
        "cv_received_wait_vacancy": "Резюме збережено ✅ Я ще читаю вакансію за посиланням. Почну інтерв’ю автоматично.",
        "vacancy_need_text": "Я не зміг прочитати вакансію за посиланням. Будь ласка, надішли текст вакансії одним повідомленням.",
        "vacancy_fetch_failed": "Не вдалося прочитати вакансію за посиланням. Надішли, будь ласка, текст вакансії.",
        "vacancy_still_pending": "Я все ще читаю вакансію… Якщо довго — просто надішли текст вакансії.",
        "cv_pdf_empty": "Не вдалося витягти текст із PDF (можливо, це скан).\nНадішли резюме текстом або .docx.",
        "cv_pdf_only": "Поки що підтримую тільки PDF. Або надішли резюме текстом.",
        "cv_pdf_no_text": "У PDF не знайшов текст (можливо, скан). Надішли резюме текстом, будь ласка.",
        "cv_too_short": "Резюме занадто коротке. Надішли повний текст або PDF.",

        "trial_intro": "Поїхали. Питання 1/3:\nЯк би ти порахувала retention D7? Які дані потрібні?",
        "q2": "Питання 2/3:\nНапиши SQL: топ-3 продукти за виручкою за останні 30 днів (orders: user_id, product_id, price, created_at).",
        "q3": "Питання 3/3:\nКонверсія впала на 10%. Які 5 причин/перевірок зробиш першими?",

        "generating": "Прийнято ✅ Генерую snapshot-звіт (у фоні, через чергу)...",

        "help": "Це тренажер інтерв'ю під вакансію.\nTrial: 3 питання + snapshot.\nДалі додамо full sprint та оплату.",
    },

    "en": {
        "choose_lang": "Choose language:",
        "choose_track": "Choose a track:",
        "choose_mode": "Choose mode:",

        "track_data": "📊 Data Analytics",

        "mode_training": "🧪 Training",
        "mode_real": "⏱ Real mode",

        "menu": "Menu:",
        "btn_trial": "🧪 Trial (free)",
        "btn_settings": "⚙️ Settings",
        "btn_help": "❓ Help",

        "settings": "Settings:",
        "btn_lang": "🌐 Language",
        "btn_mode": "🎛 Mode",

        "language_updated": "✅ Language updated",
        "mode_updated": "✅ Mode updated",
        "cancelled": "Cancelled ✅ /start to begin again",

        "lang_uk": "🇺🇦 Українська",
        "lang_ru": "🇷🇺 Русский",
        "lang_en": "🇬🇧 English",

        "ask_vacancy": "Send the vacancy text in one message OR a vacancy link.",
        "ask_cv": "Now send your resume: as text or a PDF file.",

        "vacancy_fetching": "Ok, fetching vacancy from the link (5–15 sec)...",
        "vacancy_fetch_failed": "Couldn't extract the vacancy text from that link 😕\nPlease paste the vacancy text in one message.",

        "cv_pdf_empty": "Couldn't extract text from the PDF (might be a scanned image).\nPlease send the resume as text or .docx.",

        "trial_intro": "Let's go. Q1/3:\nHow would you compute D7 retention? What data do you need?",
        "q2": "Q2/3:\nWrite SQL: top-3 products by revenue in the last 30 days (orders: user_id, product_id, price, created_at).",
        "q3": "Q3/3:\nConversion dropped by 10%. What 5 checks would you do first?",

        "generating": "Got it ✅ Generating snapshot report (in background)...",

        "help": "This is a vacancy-specific interview trainer.\nTrial: 3 questions + snapshot.\nFull sprint & payments next.",
    },
}

DEFAULT_LANG = "uk"

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
