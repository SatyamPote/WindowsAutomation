"""
Lotus Download TUI — Terminal Progress Window
==============================================
Runs INSIDE a visible console window.
Shows download progress with a clean white-themed interface.

Modes:
  - youtube: Download YouTube video/audio via yt-dlp
  - url: Download any file from URL
  - images: Bulk download images by topic
"""

import argparse
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import json

ESC      = "\033["
CLEAR    = f"{ESC}2J"
HOME     = f"{ESC}H"
HIDE_CUR = f"{ESC}?25l"
SHOW_CUR = f"{ESC}?25h"
BOLD     = f"{ESC}1m"
RESET    = f"{ESC}0m"


def enable_ansi():
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(handle, ctypes.byref(mode))
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass


def set_terminal_size(cols=75, rows=22):
    try:
        os.system(f"mode con: cols={cols} lines={rows}")
    except Exception:
        pass


def render_frame(state: dict):
    """Render the download progress frame."""
    mode    = state.get("mode", "download")
    status  = state.get("status", "starting")
    title   = state.get("title", "Preparing...")
    percent = state.get("percent", 0)
    speed   = state.get("speed", "-- KB/s")
    eta     = state.get("eta", "--:--")
    saved   = state.get("saved", "")

    try:
        w = os.get_terminal_size().columns
    except Exception:
        w = 73
    w = max(w, 50)
    inner = w - 6

    out = []
    out.append(CLEAR + HOME + HIDE_CUR)

    # Header
    out.append("")
    out.append(f"  ╔{'═' * (inner + 2)}╗")
    header = "LOTUS  DOWNLOAD  MANAGER"
    pad_l = (inner + 2 - len(header)) // 2
    pad_r = inner + 2 - len(header) - pad_l
    out.append(f"  ║{' ' * pad_l}{BOLD}{header}{RESET}{' ' * pad_r}║")
    out.append(f"  ╚{'═' * (inner + 2)}╝")
    out.append("")

    # Status
    icons = {
        "starting":   "  [ PREPARING... ]",
        "downloading": "  [ >> DOWNLOADING ]",
        "converting":  "  [ ~~ CONVERTING ]",
        "complete":    "  [ OK COMPLETE ]",
        "error":       "  [ !! ERROR ]",
    }
    out.append(f"{BOLD}{icons.get(status, icons['starting'])}{RESET}")
    out.append("")

    # Title
    if title:
        display_title = title[:inner - 10] + "..." if len(title) > inner - 10 else title
        out.append(f"{BOLD}  File  : {display_title}{RESET}")
    out.append(f"  Mode  : {mode.upper()}")
    out.append("")

    # Divider
    out.append(f"  {'─' * inner}")
    out.append("")

    # Progress bar
    bar_w = inner - 16
    filled = int(bar_w * percent / 100) if percent else 0
    bar = "█" * filled + "░" * (bar_w - filled)
    out.append(f"  {percent:3.0f}% [{bar}]")
    out.append(f"  Speed : {speed}    ETA : {eta}")
    out.append("")

    # Save location
    if saved:
        out.append(f"  Saved : {saved}")
        out.append("")

    # Divider
    out.append(f"  {'─' * inner}")
    out.append("")

    # Footer
    out.append(f"  Powered by yt-dlp + Lotus")

    print("\n".join(out), end="", flush=True)


def download_youtube(args):
    """Download YouTube content natively via yt_dlp."""
    state = {
        "mode": "YouTube Audio" if args.audio_only == "True" else f"YouTube {args.quality}p",
        "status": "starting",
        "title": "Resolving...",
        "percent": 0,
        "speed": "-- KB/s",
        "eta": "--:--",
        "saved": "",
    }
    render_frame(state)

    try:
        import yt_dlp
        import time

        def progress_hook(d):
            if d['status'] == 'downloading':
                # Parse total
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    pct = (downloaded / total) * 100
                    state["percent"] = pct
                
                # Parse speed
                speed = d.get('speed', 0)
                if speed:
                    speed_kbps = speed / 1024
                    state["speed"] = f"{speed_kbps:.1f} KB/s" if speed_kbps < 1024 else f"{(speed_kbps/1024):.1f} MB/s"
                
                # Parse ETA
                eta = d.get('eta', 0)
                if eta:
                    state["eta"] = f"{int(eta)//60}:{int(eta)%60:02d}"
                
                state["status"] = "downloading"
                
                # Parse title/filename
                filename = d.get('filename', '')
                if filename:
                    state["title"] = os.path.basename(filename)[:50]
                
                render_frame(state)
            elif d['status'] == 'finished':
                state["percent"] = 100
                state["status"] = "converting"
                render_frame(state)

        ydl_opts = {
            'outtmpl': os.path.join(args.output, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }

        if args.audio_only == "True":
            # Extract audio, fallback to m4a if ffmpeg is missing
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            # Download best single file format
            ydl_opts['format'] = 'best'

        url = args.url

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                title = info.get('title', 'Unknown Title')
                state["title"] = title[:50]
            
        state["status"] = "complete"
        state["percent"] = 100
        state["speed"] = "Done"
        state["eta"] = "0:00"
        state["saved"] = args.output
        render_frame(state)
        time.sleep(2)

    except yt_dlp.utils.DownloadError as e:
        state["status"] = "error"
        err_msg = str(e).replace('ERROR: ', '')
        if "Unsupported URL" in err_msg or "..." in args.url:
            err_msg = "Invalid or truncated URL! Please paste the full link (no '...')."
        state["title"] = err_msg[:150]
        render_frame(state)
        time.sleep(5)
    except Exception as e:
        state["status"] = "error"
        err_msg = str(e)
        if "list index out of range" in err_msg:
            err_msg = "No videos found for your search query."
        state["title"] = err_msg[:150]
        render_frame(state)
        time.sleep(5)

    render_frame(state)
    print(f"\n\n  {'─' * 40}")
    input("\n  Press Enter to close...")


def download_url(args):
    """Download any file from a URL."""
    state = {
        "mode": "Direct Download",
        "status": "starting",
        "title": args.url.split("/")[-1] or "file",
        "percent": 0,
        "speed": "-- KB/s",
        "eta": "--:--",
        "saved": "",
    }
    render_frame(state)

    try:
        req = urllib.request.Request(args.url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Lotus/2.0"
        })
        resp = urllib.request.urlopen(req, timeout=30)

        # Get filename from URL or headers
        fname = args.url.split("/")[-1].split("?")[0]
        if not fname or "." not in fname:
            cd = resp.headers.get("Content-Disposition", "")
            match = re.search(r'filename="?(.+?)"?$', cd)
            fname = match.group(1) if match else f"download_{int(time.time())}"

        total = int(resp.headers.get("Content-Length", 0))
        save_path = os.path.join(args.output, fname)
        state["title"] = fname
        state["status"] = "downloading"

        downloaded = 0
        start_time = time.time()

        with open(save_path, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)

                elapsed = time.time() - start_time
                if elapsed > 0:
                    speed = downloaded / elapsed
                    state["speed"] = f"{speed / 1024:.0f} KB/s"
                    if total > 0:
                        state["percent"] = (downloaded / total) * 100
                        remaining = (total - downloaded) / speed if speed > 0 else 0
                        mins, secs = divmod(int(remaining), 60)
                        state["eta"] = f"{mins}:{secs:02d}"

                render_frame(state)

        state["status"] = "complete"
        state["percent"] = 100
        state["speed"] = "Done"
        state["eta"] = "0:00"
        state["saved"] = save_path

    except Exception as e:
        state["status"] = "error"
        state["title"] = str(e)

    render_frame(state)
    input("\n\n  Press Enter to close...")


def download_images(args):
    """Download images by topic using Pinterest search scraping."""
    state = {
        "mode": f"Images: {args.query}",
        "status": "starting",
        "title": f"Searching Pinterest for '{args.query}'...",
        "percent": 0,
        "speed": "",
        "eta": "",
        "saved": "",
    }
    render_frame(state)

    count = int(args.count) if hasattr(args, "count") else 5
    query = urllib.parse.quote(args.query)

    # Try Pinterest search first, then DuckDuckGo as fallback
    img_urls = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        # Pinterest source
        pinterest_url = f"https://www.pinterest.com/search/pins/?q={query}"
        req = urllib.request.Request(pinterest_url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")

        # Extract image URLs from Pinterest
        # Pinterest embeds images in originals/ paths
        img_urls = re.findall(r'"(https://i\.pinimg\.com/(?:originals|736x|564x)/[^"]+)"', html)
        if not img_urls:
            # Fallback: any pinimg URLs
            img_urls = re.findall(r'(https://i\.pinimg\.com/[^"\s]+\.(?:jpg|jpeg|png|webp))', html)

    except Exception:
        pass

    # Fallback: DuckDuckGo image search if Pinterest fails
    if not img_urls:
        try:
            state["title"] = f"Trying DuckDuckGo for '{args.query}'..."
            render_frame(state)
            ddg_url = f"https://duckduckgo.com/?q={query}&iax=images&ia=images"
            req = urllib.request.Request(ddg_url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=15)
            html = resp.read().decode("utf-8", errors="replace")
            img_urls = re.findall(r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', html)
        except Exception:
            pass

    # Final fallback: Bing
    if not img_urls:
        try:
            state["title"] = f"Trying Bing for '{args.query}'..."
            render_frame(state)
            bing_url = f"https://www.bing.com/images/search?q={query}&first=1&count={count * 3}"
            req = urllib.request.Request(bing_url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=15)
            html = resp.read().decode("utf-8", errors="replace")
            img_urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', html)
            if not img_urls:
                img_urls = re.findall(r'src="(https?://[^"]+\.(?:jpg|jpeg|png|webp))', html)
        except Exception:
            pass

    try:
        # Deduplicate and limit
        img_urls = list(dict.fromkeys(img_urls))[:count]

        if not img_urls:
            state["status"] = "error"
            state["title"] = "No images found"
            render_frame(state)
            input("\n\n  Press Enter to close...")
            return

        state["title"] = f"Found {len(img_urls)} images — downloading..."
        state["status"] = "downloading"
        render_frame(state)

        downloaded = 0
        for i, url in enumerate(img_urls):
            try:
                ext = "jpg"
                for e in [".png", ".webp", ".jpeg", ".gif"]:
                    if e in url.lower():
                        ext = e.replace(".", "")
                        break

                fname = f"{args.query.replace(' ', '_')}_{i + 1}.{ext}"
                save_path = os.path.join(args.output, fname)

                req = urllib.request.Request(url, headers=headers)
                img_resp = urllib.request.urlopen(req, timeout=10)
                data = img_resp.read()

                # Only save if it looks like a real image (>5KB)
                if len(data) > 5000:
                    with open(save_path, "wb") as f:
                        f.write(data)
                    downloaded += 1
                    state["percent"] = (downloaded / len(img_urls)) * 100
                    state["title"] = f"Downloaded: {fname}"
                    render_frame(state)

            except Exception:
                continue

        state["status"] = "complete"
        state["percent"] = 100
        state["title"] = f"Downloaded {downloaded}/{len(img_urls)} images"
        state["saved"] = args.output

    except Exception as e:
        state["status"] = "error"
        state["title"] = str(e)

    render_frame(state)
    input("\n\n  Press Enter to close...")


def main():
    parser = argparse.ArgumentParser(description="Lotus Download TUI")
    parser.add_argument("--mode", required=True, choices=["youtube", "url", "images"])
    parser.add_argument("--url", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--quality", default="720")
    parser.add_argument("--audio-only", default="False")
    parser.add_argument("--ytdlp", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--count", default="5")
    parser.add_argument("--control", default="")
    parser.add_argument("--status", default="")
    args = parser.parse_args()

    enable_ansi()
    set_terminal_size(75, 22)

    try:
        os.system("title Lotus Download Manager")
    except Exception:
        pass

    if args.mode == "youtube":
        download_youtube(args)
    elif args.mode == "url":
        download_url(args)
    elif args.mode == "images":
        download_images(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        print("\n\n❌ CRITICAL ERROR IN TUI:", e)
        traceback.print_exc()
        input("\nPress Enter to exit...")
