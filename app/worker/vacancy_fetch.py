# app/worker/vacancy_fetch.py
import json
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from readability import Document

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "uk,ru;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}

ALLOWED_HOSTS = {
    "jobs.dou.ua",
    "djinni.co",
    "www.work.ua",
    "work.ua",
    "robota.ua",
    "www.robota.ua",
}


import re

def _normalize_ws(s: str) -> str:
    if not s:
        return ""
    # NBSP/ZWSP/BOM -> норм
    s = (s
         .replace("\u00a0", " ")
         .replace("\u200b", "")
         .replace("\ufeff", "")
         .replace("\r", ""))
    return s

def _clean_text(text: str) -> str:
    text = _normalize_ws(text)
    # сохраняем переносы, но выравниваем мусор
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _clean_inline(text: str) -> str:
    text = _normalize_ws(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _is_probably_blocked(html: str) -> bool:
    h = (html or "").lower()

    # Cloudflare / challenge
    if "cf-challenge" in h or "cf-turnstile" in h:
        return True
    if "checking your browser" in h or "attention required" in h:
        return True
    if "verify you are human" in h:
        return True

    # "access denied" на блок-страницах
    if "<title>access denied" in h or "request blocked" in h:
        return True

    # ВАЖНО: НЕ проверяем просто "captcha" / "recaptcha" — это часто есть на обычных страницах
    return False


def _extract_jsonld_jobposting(soup: BeautifulSoup) -> str | None:
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for sc in scripts:
        raw = (sc.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        candidates = data if isinstance(data, list) else [data]
        for obj in candidates:
            if not isinstance(obj, dict):
                continue
            t = obj.get("@type")
            ok = ("JobPosting" in t) if isinstance(t, list) else (t == "JobPosting")
            if not ok:
                continue
            desc = obj.get("description")
            if isinstance(desc, str) and len(desc.strip()) > 50:
                desc_soup = BeautifulSoup(desc, "lxml")
                return _clean_text(desc_soup.get_text("\n", strip=True))
    return None


def _extract_readability(html: str) -> str | None:
    try:
        doc = Document(html)
        content_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(content_html, "lxml")
        text = _clean_text(soup.get_text("\n", strip=True))
        return text if len(text) >= 200 else None
    except Exception:
        return None


def _pick_first(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for sel in selectors:
        node = soup.select_one(sel)
        if not node:
            continue
        txt = _clean_text(node.get_text("\n", strip=True))
        if len(txt) >= 200:
            return txt
    return None


async def parse_vacancy_url(url: str) -> str | None:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return None

    timeout = httpx.Timeout(25.0, connect=10.0)
    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        r = await client.get(url)
        if r.status_code >= 400:
            return None
        html = r.text or ""
        if len(html) < 200 or _is_probably_blocked(html):
            return None


    soup = BeautifulSoup(html, "lxml")

    # 1) доменные селекторы (самый надёжный путь)
    if host == "jobs.dou.ua":
        container = soup.select_one("div.l-vacancy") or soup.select_one("article") or soup.body
        all_text = _clean_text(container.get_text("\n", strip=True) if container else soup.get_text("\n", strip=True))

        h1 = soup.find("h1")
        title = _clean_inline(h1.get_text(" ", strip=True)) if h1 else ""

        if title:
            # чтобы матч был устойчивый — тоже чистим all_text в “inline-логике”
            all_text_inline = _clean_inline(all_text)
            title_inline = _clean_inline(title)

            start = all_text_inline.find(title_inline)
            if start != -1:
                markers = [
                    "Відгукнутися на вакансію",
                    "Гарячі",
                    "Схожі вакансії",
                    "© 2005",
                ]
                ends = [all_text_inline.find(m, start) for m in markers if all_text_inline.find(m, start) != -1]
                end = min(ends) if ends else len(all_text_inline)
                chunk = all_text_inline[start:end].strip()
                if len(chunk) >= 200:
                    return chunk

        # fallback: если точный chunk не вышел — пробуем селекторы/читалку
        t = _pick_first(soup, [
            "div.l-vacancy",
            "div.b-typo",
            "article",
            "main",
        ])
        if t:
            return t


    if host == "djinni.co":
        t = _pick_first(soup, [
            "div.job-post__description",
            "div.job-details__description",
            "div[data-testid='job-description']",
            "main",
        ])
        if t:
            return t

    if host in {"work.ua", "www.work.ua"}:
        t = _pick_first(soup, [
            "div#job-description",
            "div.card.wordwrap",
            "div.wordwrap",
            "main",
        ])
        if t:
            return t

    if host in {"robota.ua", "www.robota.ua"}:
        t = _pick_first(soup, [
            "div.full-desc",
            "div.vacancy__description",
            "main",
        ])
        if t:
            return t

    # 2) JSON-LD
    t = _extract_jsonld_jobposting(soup)
    if t and len(t) >= 200:
        return t

    # 3) readability fallback
    t = _extract_readability(html)
    if t:
        return t

    # 4) край — весь текст страницы
    raw = _clean_text(soup.get_text("\n", strip=True))
    return raw if len(raw) >= 200 else None
