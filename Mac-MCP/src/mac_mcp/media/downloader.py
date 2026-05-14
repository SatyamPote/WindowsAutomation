"""
Lotus Download Manager (macOS)
==============================
Handles all download operations:
  - YouTube video/audio downloads via yt-dlp + ffmpeg
  - General URL file downloads via curl
  - Image bulk-download via Pinterest / DuckDuckGo / Bing scraping

Downloads run synchronously (call via asyncio.to_thread from the bot).
"""

import logging
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_HOMEBREW_BINS = ["/opt/homebrew/bin", "/usr/local/bin"]
_STORAGE_BASE = Path.home() / "Library" / "Application Support" / "Lotus" / "storage"


def _get_storage_dir(subdir: str) -> Path:
    d = _STORAGE_BASE / subdir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _find_bin(name: str) -> str | None:
    path = shutil.which(name)
    if path:
        return path
    for d in _HOMEBREW_BINS:
        candidate = os.path.join(d, name)
        if os.path.exists(candidate):
            return candidate
    return None


class DownloadManager:
    """Manages all download operations for Lotus (macOS)."""

    # ------------------------------------------------------------------
    # YouTube Downloads
    # ------------------------------------------------------------------

    def download_youtube(
        self, url: str, quality: str = "720", audio_only: bool = False
    ) -> tuple[bool, str]:
        ytdlp = _find_bin("yt-dlp")
        if not ytdlp:
            return False, (
                "❌ yt-dlp not found.\n"
                "Install with: `pip install yt-dlp` or `brew install yt-dlp`"
            )

        if audio_only:
            out_dir = _get_storage_dir("audio")
            cmd = [
                ytdlp,
                "-x", "--audio-format", "mp3",
                "-o", f"{out_dir}/%(title)s.%(ext)s",
                url,
            ]
            mode_str = "🎵 Audio (MP3)"
        else:
            out_dir = _get_storage_dir("videos")
            cmd = [
                ytdlp,
                "-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
                "--merge-output-format", "mp4",
                "-o", f"{out_dir}/%(title)s.%(ext)s",
                url,
            ]
            mode_str = f"🎬 Video ({quality}p)"

        ffmpeg = _find_bin("ffmpeg")
        if ffmpeg:
            cmd += ["--ffmpeg-location", ffmpeg]

        # Enrich PATH so yt-dlp can find ffmpeg on its own too
        env = os.environ.copy()
        env["PATH"] = ":".join(_HOMEBREW_BINS) + ":" + env.get("PATH", "")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, env=env
            )
            if result.returncode == 0:
                return True, (
                    f"✅ *Download complete!*\n"
                    f"📊 Quality: {mode_str}\n"
                    f"📂 Saved to: `{out_dir}`"
                )
            err = (result.stderr or result.stdout).strip()
            return False, f"❌ Download failed:\n```\n{err[:400]}\n```"
        except subprocess.TimeoutExpired:
            return False, "❌ Download timed out (5 min)."
        except Exception as e:
            return False, f"❌ Error: {e}"

    # ------------------------------------------------------------------
    # General URL Downloads
    # ------------------------------------------------------------------

    def download_url(self, url: str) -> tuple[bool, str]:
        out_dir = _get_storage_dir("files")
        fname = os.path.basename(url.split("?")[0]) or "download"
        out_path = str(out_dir / fname)
        try:
            result = subprocess.run(
                ["curl", "-L", "-o", out_path, url],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                size_mb = os.path.getsize(out_path) / (1024 * 1024)
                return True, f"✅ Downloaded `{fname}` ({size_mb:.1f} MB)\n📂 `{out_path}`"
            return False, f"❌ Failed: {result.stderr.strip()[:200]}"
        except subprocess.TimeoutExpired:
            return False, "❌ Download timed out."
        except Exception as e:
            return False, f"❌ Error: {e}"

    # ------------------------------------------------------------------
    # Image Downloads
    # ------------------------------------------------------------------

    def download_images(self, topic: str, count: int = 5) -> tuple[bool, str]:
        out_dir = _get_storage_dir("images")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        query = urllib.parse.quote(topic)
        img_urls: list[str] = []

        # 1. Pinterest
        try:
            req = urllib.request.Request(
                f"https://www.pinterest.com/search/pins/?q={query}", headers=headers
            )
            html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
            img_urls = re.findall(
                r'"(https://i\.pinimg\.com/(?:originals|736x|564x)/[^"]+)"', html
            )
            if not img_urls:
                img_urls = re.findall(
                    r'(https://i\.pinimg\.com/[^"\s]+\.(?:jpg|jpeg|png|webp))', html
                )
        except Exception:
            pass

        # 2. DuckDuckGo fallback
        if not img_urls:
            try:
                req = urllib.request.Request(
                    f"https://duckduckgo.com/?q={query}&iax=images&ia=images",
                    headers=headers,
                )
                html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
                img_urls = re.findall(r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', html)
            except Exception:
                pass

        # 3. Bing fallback
        if not img_urls:
            try:
                bing_url = (
                    f"https://www.bing.com/images/search?q={query}"
                    f"&first=1&count={count * 3}"
                )
                req = urllib.request.Request(bing_url, headers=headers)
                html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
                img_urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html)
                if not img_urls:
                    img_urls = re.findall(
                        r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp))', html
                    )
            except Exception:
                pass

        img_urls = list(dict.fromkeys(img_urls))[:count]
        if not img_urls:
            return False, f"❌ No images found for '{topic}'."

        downloaded = 0
        for i, url in enumerate(img_urls):
            try:
                ext = "jpg"
                for e in [".png", ".webp", ".jpeg", ".gif"]:
                    if e in url.lower():
                        ext = e.replace(".", "")
                        break
                fname = f"{topic.replace(' ', '_')}_{i + 1}.{ext}"
                save_path = out_dir / fname
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    save_path.write_bytes(resp.read())
                downloaded += 1
            except Exception:
                pass

        if downloaded:
            return True, (
                f"✅ Downloaded {downloaded}/{len(img_urls)} image(s) for *{topic}*\n"
                f"📂 Saved to: `{out_dir}`"
            )
        return False, f"❌ Failed to download images for '{topic}'."


download_manager = DownloadManager()
