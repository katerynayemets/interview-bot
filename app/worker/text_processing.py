"""Text processing utilities: anonymization, tokenization, and summarization."""

import re
from typing import NamedTuple


class ProcessedText(NamedTuple):
    original: str
    anonymized: str
    token_count: int
    summary: str


# PII anonymization patterns
ANONYMIZE_PATTERNS = [
    # Email
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),

    # Phone numbers (various formats)
    (r'\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{0,4}', '[PHONE]'),
    (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]'),
    (r'\b\d{10,12}\b', '[PHONE]'),

    # Social profiles and handles
    (r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?', '[LINKEDIN]'),
    (r'(?:https?://)?(?:www\.)?github\.com/[\w-]+/?', '[GITHUB]'),
    (r'(?:https?://)?(?:www\.)?t\.me/[\w-]+/?', '[TELEGRAM]'),
    (r'(?:https?://)?(?:www\.)?facebook\.com/[\w.-]+/?', '[FACEBOOK]'),
    (r'(?:https?://)?(?:www\.)?instagram\.com/[\w.-]+/?', '[INSTAGRAM]'),
    (r'(?:https?://)?(?:www\.)?twitter\.com/[\w-]+/?', '[TWITTER]'),
    (r'@[\w]{3,}', '[SOCIAL_HANDLE]'),

    # Skype ID
    (r'\bskype:\s*[\w.-]+', '[SKYPE]'),
    (r'\bskype\s*[-:]\s*[\w.-]+', '[SKYPE]'),

    # Street addresses
    (r'\b(?:вул\.|ул\.|улица|street|str\.)\s*[\w\s,.-]+\d+[\w/-]*', '[ADDRESS]'),
    (r'\b(?:пр\.|просп\.|проспект|avenue|ave\.)\s*[\w\s,.-]+\d+[\w/-]*', '[ADDRESS]'),

    # Identity documents
    (r'\b(?:паспорт|passport)\s*[:\s]*[\w\d\s-]{6,20}', '[PASSPORT]'),
    (r'\b(?:ІПН|ИНН|INN|TIN)\s*[:\s]*\d{8,12}', '[TAX_ID]'),
]

# Seniority detection patterns
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
    """Replace PII (emails, phones, social handles, addresses) with placeholders."""
    if not text:
        return ""

    result = text
    for pattern, replacement in ANONYMIZE_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    result = re.sub(r'(\[(?:EMAIL|PHONE|TELEGRAM)\][\s,;]*){2,}', r'\1', result)

    return result.strip()


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using character-based heuristics:
    ~2.5 chars per token for Cyrillic, ~4 chars per token for Latin.
    """
    if not text:
        return 0

    cyrillic_count = len(re.findall(r'[а-яА-ЯіїєґІЇЄҐ]', text))
    latin_count = len(re.findall(r'[a-zA-Z]', text))
    other_count = len(text) - cyrillic_count - latin_count

    tokens = (cyrillic_count / 2.5) + (latin_count / 4) + (other_count / 4)

    return max(1, int(tokens))


def extract_summary(text: str, max_length: int = 500) -> str:
    """Return the first meaningful lines of text up to max_length characters."""
    if not text:
        return ""

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    summary = []
    current_length = 0

    for line in lines[:10]:
        if current_length + len(line) + 1 > max_length:
            remaining = max_length - current_length - 1
            if remaining > 20:
                summary.append(line[:remaining] + "...")
            break
        summary.append(line)
        current_length += len(line) + 1

    return '\n'.join(summary)


def detect_seniority(text: str) -> str:
    """
    Infer candidate level from CV or vacancy text.
    Checks from highest to lowest so 'senior lead' resolves to 'lead'.

    Returns: 'junior' | 'middle' | 'senior' | 'lead'
    """
    if not text:
        return "middle"

    text_lower = text.lower()

    for level in ['lead', 'senior', 'middle', 'junior']:
        for pattern in SENIORITY_PATTERNS[level]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return level

    return "middle"


def process_cv_text(text: str) -> ProcessedText:
    """Anonymize CV text, estimate token count, and extract a summary."""
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
    """Estimate token count and extract a summary for vacancy text (no anonymization)."""
    token_count = estimate_tokens(text)
    summary = extract_summary(text)

    return ProcessedText(
        original=text,
        anonymized=text,
        token_count=token_count,
        summary=summary,
    )
