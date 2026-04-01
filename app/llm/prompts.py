"""Prompt templates for interview phases, question generation, and feedback."""

from dataclasses import dataclass
from typing import Any


@dataclass
class InterviewPrompts:
    system: str
    question_generation: str
    answer_evaluation: str
    feedback_generation: str


SYSTEM_PROMPTS = {
    "base": """Ты — опытный интервьюер с 10+ годами опыта в IT.
Твоя задача — провести качественное интервью, которое поможет кандидату подготовиться к реальным собеседованиям.

Основные принципы:
- Будь дружелюбным, но профессиональным
- Задавай один вопрос за раз
- Адаптируй сложность под уровень кандидата
- Давай конструктивную обратную связь
- Используй язык: {language}
""",

    "hr_soft": """Ты — HR-специалист, проводящий первичное собеседование на soft skills.
Фокус на:
- Мотивация и карьерные цели
- Командная работа и коммуникация
- Решение конфликтов
- Адаптивность и обучаемость
- Культурное соответствие компании

Вакансия: {vacancy_summary}
Резюме кандидата: {cv_summary}
Уровень: {difficulty}
Язык общения: {language}
""",

    "technical_hard": """Ты — технический интервьюер для позиции {track}.
Фокус на:
- Глубокое понимание технологий
- Практические навыки решения задач
- Алгоритмическое мышление
- Системный дизайн (для senior+)
- Опыт с реальными проектами

Вакансия: {vacancy_summary}
Резюме кандидата: {cv_summary}
Уровень: {difficulty}
Язык общения: {language}
""",

    "mixed": """Ты — интервьюер, проводящий комплексное собеседование.
Комбинируй soft skills и технические вопросы.

Вакансия: {vacancy_summary}
Резюме кандидата: {cv_summary}
Направление: {track}
Уровень: {difficulty}
Язык общения: {language}
""",
}


PHASE_PROMPTS = {
    "intro": """Фаза: Знакомство и введение.
Задача: Представься и создай комфортную атмосферу.
- Поприветствуй кандидата
- Кратко расскажи о формате интервью
- Попроси кандидата рассказать о себе в 2-3 предложениях
""",

    "warmup": """Фаза: Разминка.
Задача: Простые вопросы для разогрева.
- Начни с общих вопросов об опыте
- Спроси про текущий/последний проект
- Уточни интересные моменты из резюме
Сложность: легкая, для снятия напряжения.
""",

    "technical_deep": """Фаза: Глубокое техническое интервью.
Задача: Проверить hard skills.
- Задавай вопросы по релевантным технологиям из вакансии
- Включай практические задачи (SQL, код, расчеты)
- Углубляйся в детали при хороших ответах
- Для {difficulty} уровня адаптируй сложность

Примеры тем для Data Analytics:
- SQL (joins, window functions, optimization)
- Python/pandas для анализа данных
- Статистика и A/B тесты
- Визуализация и storytelling
- ETL и работа с данными
""",

    "behavioral": """Фаза: Поведенческое интервью (STAR метод).
Задача: Оценить soft skills через примеры из опыта.
Используй вопросы формата:
- "Расскажи о ситуации, когда..."
- "Приведи пример..."
- "Как ты справился с..."

Темы:
- Работа в команде
- Конфликты и их решение
- Сложные дедлайны
- Ошибки и уроки
- Инициативность
""",

    "questions_to_company": """Фаза: Вопросы кандидата.
Задача: Дать возможность задать вопросы.
- Спроси, есть ли вопросы о компании/команде/проекте
- Отвечай от лица гипотетического представителя компании
- Это также показывает интерес кандидата к позиции
""",

    "closing": """Фаза: Завершение.
Задача: Подвести итоги и попрощаться.
- Поблагодари за интервью
- Кратко скажи, что будет дальше
- Пожелай удачи
""",
}


QUESTION_GENERATION_PROMPT = """
Контекст интервью:
{system_context}

Текущая фаза: {phase_type}
{phase_instructions}

История диалога (последние сообщения):
{conversation_history}

Задача: Сгенерируй ОДИН следующий вопрос для кандидата.

Требования:
- Вопрос должен быть релевантен фазе и контексту
- Учитывай предыдущие ответы кандидата
- Сложность соответствует уровню {difficulty}
- Язык: {language}
- Не повторяй уже заданные вопросы

Ответь ТОЛЬКО вопросом, без пояснений.
"""


ANSWER_EVALUATION_PROMPT = """
Контекст:
- Позиция: {track}
- Уровень: {difficulty}
- Тип интервью: {interview_type}

Вопрос интервьюера:
{question}

Ответ кандидата:
{answer}

Резюме кандидата (кратко):
{cv_summary}

Оцени ответ кандидата по следующим критериям (1-10):

1. **Техническая корректность** - насколько ответ правильный
2. **Полнота ответа** - все ли аспекты вопроса раскрыты
3. **Ясность изложения** - понятно ли объяснено
4. **Релевантный опыт** - привел ли примеры из практики

Верни JSON:
{{
    "technical_score": <1-10>,
    "completeness_score": <1-10>,
    "clarity_score": <1-10>,
    "experience_score": <1-10>,
    "overall_score": <1-10>,
    "brief_feedback": "<1-2 предложения что хорошо и что улучшить>",
    "follow_up_needed": <true/false>,
    "suggested_follow_up": "<уточняющий вопрос если нужен>"
}}
"""


FEEDBACK_GENERATION_PROMPT = """
Интервью завершено. Сгенерируй итоговый фидбек.

Информация об интервью:
- Позиция: {track}
- Уровень: {difficulty}
- Тип: {interview_type}
- Язык: {language}

Резюме кандидата:
{cv_summary}

Вакансия:
{vacancy_summary}

Полный диалог интервью:
{full_conversation}

Оценки по вопросам:
{question_scores}

Задача: Сгенерируй развернутый фидбек.

Верни JSON:
{{
    "technical_score": <1-10>,
    "communication_score": <1-10>,
    "problem_solving_score": <1-10>,
    "overall_score": <1-10>,
    "verdict": "<hire/maybe/no_hire>",
    "strengths": ["<сильная сторона 1>", "<сильная сторона 2>", ...],
    "improvements": ["<что улучшить 1>", "<что улучшить 2>", ...],
    "recommended_topics": ["<тема для изучения 1>", "<тема 2>", ...],
    "detailed_feedback": "<развернутый фидбек на 3-5 абзацев>"
}}
"""


class PromptManager:
    """Builds context-aware prompts for each interview phase."""

    def __init__(
        self,
        interview_type: str,
        track: str,
        difficulty: str,
        language: str,
        cv_summary: str | None = None,
        vacancy_summary: str | None = None,
    ):
        self.interview_type = interview_type
        self.track = track
        self.difficulty = difficulty
        self.language = language
        self.cv_summary = cv_summary or "Не предоставлено"
        self.vacancy_summary = vacancy_summary or "Не предоставлена"

    def get_system_prompt(self) -> str:
        base = SYSTEM_PROMPTS["base"].format(language=self._get_language_name())

        specific = SYSTEM_PROMPTS.get(self.interview_type, SYSTEM_PROMPTS["mixed"])
        specific = specific.format(
            track=self.track,
            difficulty=self._get_difficulty_name(),
            language=self._get_language_name(),
            cv_summary=self.cv_summary[:500],
            vacancy_summary=self.vacancy_summary[:500],
        )

        return f"{base}\n\n{specific}"

    def get_phase_instructions(self, phase_type: str) -> str:
        instructions = PHASE_PROMPTS.get(phase_type, "")
        return instructions.format(difficulty=self._get_difficulty_name())

    def build_question_prompt(
        self,
        phase_type: str,
        conversation_history: list[dict],
    ) -> str:
        history_text = self._format_conversation(conversation_history)

        return QUESTION_GENERATION_PROMPT.format(
            system_context=self.get_system_prompt(),
            phase_type=phase_type,
            phase_instructions=self.get_phase_instructions(phase_type),
            conversation_history=history_text,
            difficulty=self._get_difficulty_name(),
            language=self._get_language_name(),
        )

    def build_evaluation_prompt(
        self,
        question: str,
        answer: str,
    ) -> str:
        return ANSWER_EVALUATION_PROMPT.format(
            track=self.track,
            difficulty=self._get_difficulty_name(),
            interview_type=self.interview_type,
            question=question,
            answer=answer,
            cv_summary=self.cv_summary[:300],
        )

    def build_feedback_prompt(
        self,
        full_conversation: list[dict],
        question_scores: list[dict],
    ) -> str:
        conversation_text = self._format_conversation(full_conversation)
        scores_text = "\n".join([
            f"Q{i+1}: {s.get('overall_score', 'N/A')}/10 - {s.get('brief_feedback', '')}"
            for i, s in enumerate(question_scores)
        ])

        return FEEDBACK_GENERATION_PROMPT.format(
            track=self.track,
            difficulty=self._get_difficulty_name(),
            interview_type=self.interview_type,
            language=self._get_language_name(),
            cv_summary=self.cv_summary[:500],
            vacancy_summary=self.vacancy_summary[:500],
            full_conversation=conversation_text,
            question_scores=scores_text,
        )

    def _format_conversation(self, messages: list[dict], max_messages: int = 10) -> str:
        recent = messages[-max_messages:] if len(messages) > max_messages else messages
        lines = []
        for msg in recent:
            role = "Интервьюер" if msg.get("role") == "assistant" else "Кандидат"
            lines.append(f"{role}: {msg.get('content', msg.get('text', ''))}")
        return "\n\n".join(lines)

    def _get_language_name(self) -> str:
        names = {
            "uk": "украинский",
            "ru": "русский",
            "en": "английский",
        }
        return names.get(self.language, "русский")

    def _get_difficulty_name(self) -> str:
        names = {
            "junior": "Junior (начинающий)",
            "middle": "Middle (средний)",
            "senior": "Senior (опытный)",
            "lead": "Lead (ведущий)",
        }
        return names.get(self.difficulty, "Middle")
