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
    # КЛЮЧЕВО: просим не отдавать brotli (br), иначе без brotli-библиотеки httpx может получить мусор
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "uk,ru;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}


def _is_probably_blocked(html: str) -> bool:
    h = html.lower()
    return any(
        x in h
        for x in [
            "captcha",
            "cloudflare",
            "attention required",
            "verify you are human",
            "access denied",
        ]
    )


def _clean_text(text: str) -> str:
    text = re.sub(r"\r", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
            if isinstance(t, list):
                ok = "JobPosting" in t
            else:
                ok = (t == "JobPosting")
            if not ok:
                continue
            desc = obj.get("description")
            if isinstance(desc, str) and len(desc.strip()) > 50:
                # description часто HTML — почистим
                desc_soup = BeautifulSoup(desc, "lxml")
                return _clean_text(desc_soup.get_text(" ", strip=True))
    return None


def _extract_readability(html: str) -> str | None:
    try:
        doc = Document(html)
        content_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(content_html, "lxml")
        text = soup.get_text("\n", strip=True)
        text = _clean_text(text)
        return text if len(text) >= 200 else None
    except Exception:
        return None


async def parse_vacancy_url(url: str) -> str | None:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
        timeout=timeout,
    ) as client:
        r = await client.get(url)
        if r.status_code >= 400:
            return None

        html = r.text or ""
        if len(html) < 200 or _is_probably_blocked(html):
            return None

    soup = BeautifulSoup(html, "lxml")

    # 1) JSON-LD JobPosting
    t = _extract_jsonld_jobposting(soup)
    if t:
        return t

    # 2) meta description (иногда реально есть)
    og = soup.find("meta", attrs={"property": "og:description"}) or soup.find("meta", attrs={"name": "description"})
    if og and og.get("content"):
        meta_text = _clean_text(str(og["content"]))
        if len(meta_text) >= 200:
            return meta_text

    # 3) readability fallback
    t = _extract_readability(html)
    if t:
        return t

    # 4) совсем край — весь текст страницы (обычно грязно, но лучше чем ничего)
    raw_text = _clean_text(soup.get_text("\n", strip=True))
    return raw_text if len(raw_text) >= 200 else None
