"""
Lotus Music Player — Terminal TUI
====================================================
Runs INSIDE a visible console window.
Clean white theme — no colors, just elegant box-drawing.

Inspired by kew and cliamp terminal music players.
"""

import argparse
import os
import subprocess
import sys
import threading
import time

ESC      = "\033["
CLEAR    = f"{ESC}2J"
HOME     = f"{ESC}H"
HIDE_CUR = f"{ESC}?25l"
SHOW_CUR = f"{ESC}?25h"
BOLD     = f"{ESC}1m"
DIM      = f""  # No dim, strictly white
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


def set_terminal_size(cols=70, rows=26):
    try:
        os.system(f"mode con: cols={cols} lines={rows}")
    except Exception:
        pass


def render_frame(state: dict):
    title  = state.get("title", "Searching...")
    query  = state.get("query", "")
    status = state.get("status", "loading")
    volume = state.get("volume", 100)

    try:
        w = os.get_terminal_size().columns
    except Exception:
        w = 68
    w = max(w, 50)
    inner = w - 6  # padding inside box

    out = []
    out.append(CLEAR + HOME + HIDE_CUR)

    # ── Top border ──
    out.append("")
    out.append(f"  ╔{'═' * (inner + 2)}╗")
    header = "LOTUS  MUSIC  PLAYER"
    pad_l = (inner + 2 - len(header)) // 2
    pad_r = inner + 2 - len(header) - pad_l
    out.append(f"  ║{' ' * pad_l}{BOLD}{header}{RESET}{' ' * pad_r}║")
    out.append(f"  ╚{'═' * (inner + 2)}╝")
    out.append("")

    # ── Status ──
    icons = {
        "loading": "  [ LOADING... ]",
        "playing": "  [ >> PLAYING ]",
        "paused":  "  [ || PAUSED  ]",
        "stopped": "  [ ## STOPPED ]",
    }
    out.append(f"{BOLD}{icons.get(status, icons['loading'])}{RESET}")
    out.append("")

    # ── Search query ──
    if query:
        out.append(f"{DIM}  Search : {query}{RESET}")

    # ── Track title ──
    if title and title != "Searching...":
        out.append(f"{BOLD}  Track  : {title}{RESET}")
    else:
        out.append(f"  Track  : (resolving...)")
    out.append("")

    # ── Divider ──
    out.append(f"  {'─' * inner}")
    out.append("")

    # ── Progress indicator ──
    bar_w = inner - 12
    if status == "playing":
        pos = int(time.time() * 2) % bar_w
        bar = "░" * pos + "█" + "░" * (bar_w - pos - 1)
    elif status == "paused":
        third = bar_w // 3
        bar = "▓" * third + "░" * (bar_w - third)
    else:
        bar = "░" * bar_w

    out.append(f"  0:00 [{bar}] ?:??")
    out.append("")

    # ── Volume ──
    vol_blocks = int(volume / 100 * 20)
    vol_bar = "█" * vol_blocks + "░" * (20 - vol_blocks)
    out.append(f"  Volume : [{vol_bar}] {volume}%")
    out.append("")

    # ── Divider ──
    out.append(f"  {'─' * inner}")
    out.append("")

    # ── Controls ──
    out.append(f"{BOLD}  Controls (via Telegram):{RESET}")
    out.append(f"    play <song>      Play a new song")
    out.append(f"    pause            Pause playback")
    out.append(f"    resume           Resume playback")
    out.append(f"    stop             Stop & close player")
    out.append(f"    next             Skip track")
    out.append(f"    volume up/down   Adjust volume")
    out.append("")

    # ── Footer ──
    out.append(f"{DIM}  Powered by mpv + yt-dlp{RESET}")

    print("\n".join(out), end="", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--mpv", required=True)
    parser.add_argument("--ytdlp", required=True)
    parser.add_argument("--control", required=True)
    parser.add_argument("--status", required=True)
    args = parser.parse_args()

    enable_ansi()
    set_terminal_size(70, 26)

    try:
        os.system("title Lotus Music Player")
    except Exception:
        pass

    state = {
        "title": "Searching...",
        "query": args.query,
        "status": "loading",
        "volume": 100,
    }

    def write_status():
        try:
            with open(args.status, "w", encoding="utf-8") as f:
                f.write(f"{state['status']}|{state['title']}|{state['volume']}")
        except Exception:
            pass

    write_status()
    render_frame(state)

    # ── Launch mpv (hidden, audio only) ──
    # If query contains commas, it's a playlist
    queries = [q.strip() for q in args.query.split(",") if q.strip()]
    
    cmd = [
        args.mpv,
        "--no-video",
        "--term-status-msg=",
        "--msg-level=all=info",
        f"--script-opts=ytdl_hook-ytdl_path=\"{args.ytdlp}\"",
    ]
    for q in queries:
        cmd.append(f"ytdl://ytsearch:{q}")

    try:
        mpv_proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        state["status"] = "stopped"
        state["title"] = f"ERROR: {e}"
        render_frame(state)
        write_status()
        input("\nPress Enter to close...")
        return

    # ── Read mpv output in background ──
    def read_mpv():
        try:
            for raw in mpv_proc.stdout:
                try:
                    line = raw.decode("utf-8", errors="replace").strip()
                except Exception:
                    continue
                if not line:
                    continue
                low = line.lower()
                
                # Check for track changes
                if "loading:" in low or "playing:" in low:
                    if "ytdl://ytsearch:" in low:
                        # Extract the query being loaded if possible, or just wait for title
                        pass

                if low.startswith("title:"):
                    t = line[6:].strip()
                    if t:
                        state["title"] = t
                        state["status"] = "playing"
                        write_status()
                elif "audio:" in low or "ao:" in low:
                    if state["status"] == "loading":
                        state["status"] = "playing"
                        write_status()
                elif "(exiting)" in low or "end of file" in low:
                    # Don't stop yet if there are more in the playlist
                    # mpv handles the transition itself, we just need to detect title changes
                    pass
        except Exception:
            pass

    threading.Thread(target=read_mpv, daemon=True).start()

    # ── Main loop ──
    running = True
    while running:
        time.sleep(0.5)

        # mpv died?
        if mpv_proc.poll() is not None:
            state["status"] = "stopped"
            render_frame(state)
            write_status()
            time.sleep(1)
            break

        render_frame(state)

        # ── Check control file ──
        try:
            if os.path.exists(args.control):
                with open(args.control, "r", encoding="utf-8") as f:
                    command = f.read().strip()
                if command:
                    os.remove(args.control)

                    if command == "pause":
                        if mpv_proc.stdin:
                            mpv_proc.stdin.write(b"p")
                            mpv_proc.stdin.flush()
                        state["status"] = "paused"
                        write_status()

                    elif command == "resume":
                        if mpv_proc.stdin:
                            mpv_proc.stdin.write(b"p")
                            mpv_proc.stdin.flush()
                        state["status"] = "playing"
                        write_status()

                    elif command == "quit":
                        # Kill mpv
                        if mpv_proc.stdin:
                            try:
                                mpv_proc.stdin.write(b"q")
                                mpv_proc.stdin.flush()
                            except Exception:
                                pass
                        try:
                            mpv_proc.wait(timeout=2)
                        except Exception:
                            mpv_proc.kill()
                        state["status"] = "stopped"
                        render_frame(state)
                        write_status()
                        running = False

                    elif command == "volume_up":
                        if mpv_proc.stdin:
                            mpv_proc.stdin.write(b"0")
                            mpv_proc.stdin.flush()
                        state["volume"] = min(150, state["volume"] + 10)
                        write_status()

                    elif command == "volume_down":
                        if mpv_proc.stdin:
                            mpv_proc.stdin.write(b"9")
                            mpv_proc.stdin.flush()
                        state["volume"] = max(0, state["volume"] - 10)
                        write_status()

                    elif command == "next":
                        if mpv_proc.stdin:
                            # mpv standard key for next is '>'
                            mpv_proc.stdin.write(b">")
                            mpv_proc.stdin.flush()
                        state["status"] = "loading"
                        state["title"] = "Loading next..."
                        write_status()
                    
                    elif command == "prev":
                        if mpv_proc.stdin:
                            # mpv standard key for prev is '<'
                            mpv_proc.stdin.write(b"<")
                            mpv_proc.stdin.flush()
                        state["status"] = "loading"
                        state["title"] = "Loading previous..."
                        write_status()

        except Exception:
            pass

    # Cleanup
    print(SHOW_CUR, end="", flush=True)
    for f in [args.control, args.status]:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass


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
