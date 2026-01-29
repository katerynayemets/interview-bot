# app/worker/text_processing.py
"""Утилиты для обработки текстов: анонимизация, токенизация, суммаризация"""

import re
from typing import NamedTuple


class ProcessedText(NamedTuple):
    """Результат обработки текста"""
    original: str
    anonymized: str
    token_count: int
    summary: str


# Паттерны для анонимизации персональных данных
ANONYMIZE_PATTERNS = [
    # Email
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),

    # Телефоны (разные форматы)
    (r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{0,4}', '[PHONE]'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]'),
    (r'\b\d{10,12}\b', '[PHONE]'),

    # Социальные сети и мессенджеры
    (r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?', '[LINKEDIN]'),
    (r'(?:https?://)?(?:www\.)?github\.com/[\w-]+/?', '[GITHUB]'),
    (r'(?:https?://)?(?:www\.)?t\.me/[\w-]+/?', '[TELEGRAM]'),
    (r'(?:https?://)?(?:www\.)?facebook\.com/[\w.-]+/?', '[FACEBOOK]'),
    (r'(?:https?://)?(?:www\.)?instagram\.com/[\w.-]+/?', '[INSTAGRAM]'),
    (r'(?:https?://)?(?:www\.)?twitter\.com/[\w-]+/?', '[TWITTER]'),
    (r'@[\w]{3,}', '[SOCIAL_HANDLE]'),  # @username

    # Skype ID
    (r'\bskype:\s*[\w.-]+', '[SKYPE]'),
    (r'\bskype\s*[-:]\s*[\w.-]+', '[SKYPE]'),

    # Адреса (упрощенный паттерн)
    (r'\b(?:вул\.|ул\.|улица|street|str\.)\s*[\w\s,.-]+\d+[\w/-]*', '[ADDRESS]'),
    (r'\b(?:пр\.|просп\.|проспект|avenue|ave\.)\s*[\w\s,.-]+\d+[\w/-]*', '[ADDRESS]'),

    # Паспортные данные
    (r'\b(?:паспорт|passport)\s*[:\s]*[\w\d\s-]{6,20}', '[PASSPORT]'),
    (r'\b(?:ІПН|ИНН|INN|TIN)\s*[:\s]*\d{8,12}', '[TAX_ID]'),

    # Дата рождения (может быть полезна для интервью, но лучше убрать)
    # (r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b', '[DATE]'),
]

# Паттерны для определения уровня (из резюме)
SENIORITY_PATTERNS = {
    'lead': [
        r'\b(?:lead|team\s*lead|tech\s*lead|лид|тимлид|руководитель)\b',
        r'\b(?:head\s+of|director|директор|начальник)\b',
        r'\b(?:principal|staff|архитектор|architect)\b',
    ],
    'senior': [
        r'\b(?:senior|старший|sr\.?|сеньор)\b',
        r'\b(?:10\+|8\+|7\+)\s*(?:years?|років|лет|г\.?)\b',
    ],
    'middle': [
        r'\b(?:middle|мидл|mid)\b',
        r'\b(?:3-5|4-6|5\+)\s*(?:years?|років|лет|г\.?)\b',
    ],
    'junior': [
        r'\b(?:junior|младший|jr\.?|джуниор|джун)\b',
        r'\b(?:intern|стажер|trainee)\b',
        r'\b(?:0-1|1-2|менше\s+року|less\s+than\s+a\s+year)\b',
    ],
}


def anonymize_text(text: str) -> str:
    """
    Удаляет персональные данные из текста.

    Args:
        text: исходный текст (резюме)

    Returns:
        текст с замененными персональными данными
    """
    if not text:
        return ""

    result = text
    for pattern, replacement in ANONYMIZE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Убираем множественные замены подряд
    result = re.sub(r'(\[(?:EMAIL|PHONE|TELEGRAM)\][\s,;]*){2,}', r'\1', result)

    return result.strip()


def estimate_tokens(text: str) -> int:
    """
    Примерная оценка количества токенов в тексте.
    Используем простую эвристику: ~4 символа = 1 токен для английского,
    ~2-3 символа = 1 токен для кириллицы.

    Args:
        text: текст для оценки

    Returns:
        примерное количество токенов
    """
    if not text:
        return 0

    # Считаем кириллические символы
    cyrillic_count = len(re.findall(r'[а-яА-ЯіїєґІЇЄҐ]', text))
    latin_count = len(re.findall(r'[a-zA-Z]', text))
    other_count = len(text) - cyrillic_count - latin_count

    # Эвристика для токенов
    tokens = (cyrillic_count / 2.5) + (latin_count / 4) + (other_count / 4)

    return max(1, int(tokens))


def extract_summary(text: str, max_length: int = 500) -> str:
    """
    Извлекает краткое описание из текста (первые значимые строки).

    Args:
        text: полный текст
        max_length: максимальная длина summary

    Returns:
        краткое описание
    """
    if not text:
        return ""

    # Разбиваем на строки и берем непустые
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    summary = []
    current_length = 0

    for line in lines[:10]:  # Максимум 10 первых строк
        if current_length + len(line) + 1 > max_length:
            # Обрезаем последнюю строку если нужно
            remaining = max_length - current_length - 1
            if remaining > 20:
                summary.append(line[:remaining] + "...")
            break
        summary.append(line)
        current_length += len(line) + 1

    return '\n'.join(summary)


def detect_seniority(text: str) -> str:
    """
    Определяет уровень кандидата из текста резюме/вакансии.

    Args:
        text: текст резюме или вакансии

    Returns:
        уровень: 'junior' | 'middle' | 'senior' | 'lead'
    """
    if not text:
        return "middle"  # дефолт

    text_lower = text.lower()

    # Проверяем от старшего к младшему (чтобы "senior lead" дал "lead")
    for level in ['lead', 'senior', 'middle', 'junior']:
        for pattern in SENIORITY_PATTERNS[level]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return level

    return "middle"  # дефолт если не определили


def process_cv_text(text: str) -> ProcessedText:
    """
    Полная обработка текста резюме:
    - анонимизация
    - подсчет токенов
    - извлечение summary

    Args:
        text: исходный текст резюме

    Returns:
        ProcessedText с результатами обработки
    """
    anonymized = anonymize_text(text)
    token_count = estimate_tokens(anonymized)
    summary = extract_summary(anonymized)

    return ProcessedText(
        original=text,
        anonymized=anonymized,
        token_count=token_count,
        summary=summary,
    )


def process_vacancy_text(text: str) -> ProcessedText:
    """
    Обработка текста вакансии:
    - подсчет токенов
    - извлечение summary
    (анонимизация не нужна для вакансий)

    Args:
        text: исходный текст вакансии

    Returns:
        ProcessedText с результатами обработки
    """
    token_count = estimate_tokens(text)
    summary = extract_summary(text)

    return ProcessedText(
        original=text,
        anonymized=text,  # вакансии не анонимизируем
        token_count=token_count,
        summary=summary,
    )
