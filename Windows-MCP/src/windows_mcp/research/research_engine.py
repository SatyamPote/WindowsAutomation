import os
import requests
import wikipediaapi
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import logging
import time
import urllib.parse

logger = logging.getLogger(__name__)

class ResearchEngine:
    def __init__(self, storage_root):
        self.storage_root = storage_root
        self.research_dir = os.path.join(storage_root, "research")
        os.makedirs(self.research_dir, exist_ok=True)
        
        # Wikipedia setup
        self.wiki = wikipediaapi.Wikipedia(
            language='en',
            extract_format=wikipediaapi.ExtractFormat.WIKI,
            user_agent="LotusResearchBot/1.0 (https://github.com/SatyamPote/Lotus)"
        )

    def search_images(self, query, count=3):
        """Enhanced DuckDuckGo image search scraper with relative URL support."""
        images = []
        try:
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}+images"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            img_dir = os.path.join(self.research_dir, "images", query.replace(" ", "_"))
            os.makedirs(img_dir, exist_ok=True)
            
            # Look for images in the DDG results
            found_count = 0
            for img in soup.find_all("img"):
                if found_count >= count: break
                img_url = img.get("src")
                if not img_url: continue
                
                # Resolve relative URLs
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = "https://duckduckgo.com" + img_url
                
                if not img_url.startswith("http"): continue
                # Skip small icons/logos
                if "duckduckgo" in img_url and "logo" in img_url: continue
                
                try:
                    img_data = requests.get(img_url, timeout=5).content
                    img_path = os.path.join(img_dir, f"image_{found_count}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    images.append(img_path)
                    found_count += 1
                except: continue
        except Exception as e:
            logger.error(f"Image search failed: {e}")
        return images

    def perform_research(self, topic):
        """Enhanced multi-source research: Wikipedia -> DDG -> Web Scraping."""
        # Clean query
        query = topic.lower().replace("research", "").replace("about", "").replace("on ", "").strip()
        logger.info(f"Performing deep research on: {query}")

        data = {
            "title": topic.title(),
            "summary": "",
            "points": [],
            "sources": [],
            "images": []
        }

        # ── Step 1: Wikipedia ──
        try:
            page = self.wiki.page(query)
            if page.exists():
                data["title"] = page.title
                data["summary"] = page.summary[:1500]
                data["points"] = [s.strip() for s in page.summary.split(".") if len(s) > 20][:8]
                data["sources"].append(page.fullurl)
        except Exception as e:
            logger.warning(f"Wikipedia failed: {e}")

        # ── Step 2: Fallback to DuckDuckGo/Scraping ──
        if not data["summary"]:
            try:
                search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(search_url, headers=headers, timeout=10)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                snippets = []
                for link in soup.find_all('a', class_='result__snippet')[:5]:
                    snippets.append(link.get_text())
                    # result__a is often the title/link
                    parent = link.find_parent('div', class_='result')
                    if parent:
                        a = parent.find('a', class_='result__a')
                        if a and a.get('href'): data["sources"].append(a.get('href'))
                
                if snippets:
                    data["summary"] = " ".join(snippets)
                    data["points"] = [s[:100] + "..." for s in snippets]
            except Exception as e:
                logger.error(f"Scraping fallback failed: {e}")

        # Final safety check
        if not data["summary"]:
            data["summary"] = f"Information about '{query}' is currently limited. Please verify the topic name."

        # ── Step 3: Images ──
        data["images"] = self.search_images(query, count=5)

        # ── Step 4: Generate PDF ──
        pdf_path = self.generate_pdf(query, data, data["images"])
        
        # ── Step 5: Save Summary Text ──
        summary_txt_path = os.path.join(self.research_dir, f"summary_{query.replace(' ', '_')}.txt")
        with open(summary_txt_path, "w", encoding="utf-8") as f:
            f.write(f"TOPIC: {data['title']}\n\nSUMMARY:\n{data['summary']}\n\nSOURCES:\n" + "\n".join(data["sources"]))

        return {
            "success": pdf_path is not None,
            "pdf": pdf_path,
            "images": data["images"][:3],
            "summary": data["summary"]
        }

    def generate_pdf(self, topic, data, images):
        """Generate a professional PDF report."""
        pdf_filename = f"report_{topic.replace(' ', '_')}.pdf"
        pdf_path = os.path.join(self.research_dir, pdf_filename)
        
        try:
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            
            # Header
            c.setFont("Helvetica-Bold", 24)
            c.drawString(50, height - 50, f"Lotus Research: {data['title']}")
            c.line(50, height - 60, width - 50, height - 60)
            
            # Summary
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 100, "Summary")
            c.setFont("Helvetica", 11)
            text_object = c.beginText(50, height - 120)
            text_object.setLeading(14)
            
            summary = data['summary']
            for i in range(0, len(summary), 95):
                text_object.textLine(summary[i:i+95])
            c.drawText(text_object)
            
            # Images
            y = height - 350
            for img_path in images[:2]:
                try:
                    img = ImageReader(img_path)
                    # Scale image to fit width while maintaining aspect ratio
                    img_w, img_h = img.getSize()
                    aspect = img_h / float(img_w)
                    draw_w = 240
                    draw_h = draw_w * aspect
                    if draw_h > 180:
                        draw_h = 180
                        draw_w = draw_h / aspect
                    c.drawImage(img, 50, y - draw_h + 180, width=draw_w, height=draw_h, preserveAspectRatio=True)
                    y -= (draw_h + 20)
                except: continue
            
            # Key Points
            if y < 150:
                c.showPage()
                y = height - 50
            
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, y, "Key Findings")
            c.setFont("Helvetica", 11)
            y -= 25
            for point in data['points']:
                c.drawString(60, y, f"• {point[:90]}")
                y -= 20
                if y < 50:
                    c.showPage()
                    y = height - 50
            
            # Sources
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y - 20, "References:")
            c.setFont("Helvetica-Oblique", 9)
            y -= 35
            for src in list(set(data['sources']))[:5]:
                c.drawString(50, y, src)
                y -= 15
                
            c.save()
            return pdf_path
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return None
