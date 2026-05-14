"""
Lotus Research Engine (v3)
==========================
Multi-source research with PDF report generation.

Source order:
  1. Wikipedia search → page resolution (handles fuzzy queries)
  2. DuckDuckGo HTML scrape (current selectors, with fallbacks)
  3. Plain summary placeholder if both fail

Returns a uniform dict with success/pdf/images/summary so the bot can
render it consistently.
"""

from __future__ import annotations

import logging
import os
import re
import time
import urllib.parse
from typing import Any

import requests
import wikipediaapi
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class ResearchEngine:
    def __init__(self, storage_root: str) -> None:
        self.storage_root = storage_root
        self.research_dir = os.path.join(storage_root, "research")
        os.makedirs(self.research_dir, exist_ok=True)
        self.wiki = wikipediaapi.Wikipedia(
            language="en",
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent="LotusResearchBot/3.0 (https://github.com/SatyamPote/Lotus)",
        )

    # ── Source 1: Wikipedia ─────────────────────────────────────────────

    def _wikipedia_search(self, query: str) -> str | None:
        """Return the best matching Wikipedia page title for a fuzzy query."""
        try:
            r = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": 1,
                    "namespace": 0,
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=8,
            )
            data = r.json()
            if isinstance(data, list) and len(data) > 1 and data[1]:
                return data[1][0]
        except Exception as e:
            logger.debug("Wikipedia opensearch failed: %s", e)
        return None

    def _wikipedia_lookup(self, query: str, data: dict[str, Any]) -> bool:
        try:
            page = self.wiki.page(query)
            if not page.exists():
                title = self._wikipedia_search(query)
                if not title:
                    return False
                page = self.wiki.page(title)
                if not page.exists():
                    return False

            data["title"] = page.title
            summary = page.summary or ""
            data["summary"] = summary[:1800].strip()
            data["points"] = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", summary) if len(s.strip()) > 25
            ][:8]
            data["sources"].append(page.fullurl)
            return bool(data["summary"])
        except Exception as e:
            logger.warning("Wikipedia lookup failed for %r: %s", query, e)
            return False

    # ── Source 2: DuckDuckGo HTML scrape ────────────────────────────────

    def _duckduckgo_lookup(self, query: str, data: dict[str, Any]) -> bool:
        try:
            r = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            logger.warning("DDG fetch failed: %s", e)
            return False

        snippets: list[str] = []
        for sel in ("a.result__snippet", ".result__snippet", ".result__body"):
            for node in soup.select(sel):
                text = node.get_text(" ", strip=True)
                if text and len(text) > 30 and text not in snippets:
                    snippets.append(text)
            if snippets:
                break

        for a in soup.select("a.result__a, a.result__url"):
            href = a.get("href")
            if href and href.startswith("http"):
                data["sources"].append(href)
            if len(data["sources"]) >= 6:
                break

        if snippets:
            data["summary"] = " ".join(snippets[:5])[:1800]
            data["points"] = [s[:140] for s in snippets[:6]]
            return True
        return False

    # ── Images ──────────────────────────────────────────────────────────

    def search_images(self, query: str, count: int = 3) -> list[str]:
        images: list[str] = []
        try:
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}+images"
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            img_dir = os.path.join(self.research_dir, "images", query.replace(" ", "_"))
            os.makedirs(img_dir, exist_ok=True)

            for img in soup.find_all("img"):
                if len(images) >= count:
                    break
                src = img.get("src") or ""
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = "https://duckduckgo.com" + src
                if not src.startswith("http"):
                    continue
                if "duckduckgo" in src and "logo" in src:
                    continue
                try:
                    data = requests.get(src, headers={"User-Agent": USER_AGENT}, timeout=6).content
                    if len(data) < 2048:
                        continue  # skip tiny icons
                    path = os.path.join(img_dir, f"image_{len(images)}.jpg")
                    with open(path, "wb") as f:
                        f.write(data)
                    images.append(path)
                except Exception:
                    continue
        except Exception as e:
            logger.error("Image search failed: %s", e)
        return images

    # ── Public entry point ──────────────────────────────────────────────

    def perform_research(self, topic: str) -> dict[str, Any]:
        query = re.sub(r"\b(research|about|on)\b", "", topic, flags=re.I).strip()
        if not query:
            return {"success": False, "pdf": None, "images": [], "summary": "Empty topic."}

        logger.info("Researching: %s", query)
        data: dict[str, Any] = {
            "title": query.title(),
            "summary": "",
            "points": [],
            "sources": [],
            "images": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
        }

        if not self._wikipedia_lookup(query, data):
            self._duckduckgo_lookup(query, data)

        if not data["summary"]:
            data["summary"] = (
                f"No reliable information could be retrieved for '{query}'. "
                "Try refining the topic or check your internet connection."
            )

        data["images"] = self.search_images(query, count=5)
        pdf_path = self.generate_pdf(query, data, data["images"])

        summary_txt_path = os.path.join(
            self.research_dir, f"summary_{query.replace(' ', '_')}.txt"
        )
        try:
            with open(summary_txt_path, "w", encoding="utf-8") as f:
                f.write(
                    f"TOPIC: {data['title']}\n"
                    f"DATE:  {data['timestamp']}\n\n"
                    f"SUMMARY:\n{data['summary']}\n\n"
                    f"SOURCES:\n" + "\n".join(data["sources"])
                )
        except Exception as e:
            logger.warning("Could not write summary text: %s", e)

        return {
            "success": pdf_path is not None and bool(data["summary"]),
            "pdf": pdf_path,
            "images": data["images"][:3],
            "summary": data["summary"],
        }

    # ── PDF rendering ───────────────────────────────────────────────────

    def generate_pdf(self, topic: str, data: dict[str, Any], images: list[str]) -> str | None:
        pdf_path = os.path.join(self.research_dir, f"report_{topic.replace(' ', '_')}.pdf")
        try:
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter

            c.setFont("Helvetica-Bold", 22)
            c.drawString(50, height - 60, f"Lotus Research: {data['title']}")
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(50, height - 78, f"Generated {data['timestamp']}")
            c.line(50, height - 88, width - 50, height - 88)

            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 115, "Summary")
            c.setFont("Helvetica", 11)
            text = c.beginText(50, height - 135)
            text.setLeading(14)
            for line in self._wrap(data["summary"], 95):
                text.textLine(line)
            c.drawText(text)

            y = height - 360
            for img_path in images[:2]:
                try:
                    img = ImageReader(img_path)
                    iw, ih = img.getSize()
                    aspect = ih / float(iw) if iw else 1
                    draw_w = 240
                    draw_h = min(180, draw_w * aspect)
                    c.drawImage(img, 50, y - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True)
                    y -= draw_h + 18
                except Exception:
                    continue

            if y < 160:
                c.showPage()
                y = height - 60

            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, "Key Findings")
            c.setFont("Helvetica", 11)
            y -= 22
            for point in data["points"]:
                for line in self._wrap(f"• {point}", 90):
                    c.drawString(60, y, line)
                    y -= 16
                    if y < 60:
                        c.showPage()
                        y = height - 60
                y -= 4

            if y < 80:
                c.showPage()
                y = height - 60
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "References")
            c.setFont("Helvetica-Oblique", 9)
            y -= 18
            for src in list(dict.fromkeys(data["sources"]))[:6]:
                c.drawString(50, y, src[:110])
                y -= 14

            c.save()
            return pdf_path
        except Exception as e:
            logger.error("PDF generation failed: %s", e)
            return None

    @staticmethod
    def _wrap(text: str, width: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 > width:
                if cur:
                    lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        return lines
