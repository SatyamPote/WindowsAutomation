"""Filesystem service — structured file operations for macOS."""

import fnmatch
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from mac_mcp.filesystem.views import MAX_READ_SIZE, MAX_RESULTS, Directory, File

logger = logging.getLogger(__name__)


def read_file(
    path: str, offset: int | None = None, limit: int | None = None, encoding: str = "utf-8"
) -> str:
    file_path = Path(path).resolve()
    if not file_path.exists():
        return f"Error: File not found: {file_path}"
    if not file_path.is_file():
        return f"Error: Path is not a file: {file_path}"
    if file_path.stat().st_size > MAX_READ_SIZE:
        return (
            f"Error: File too large ({file_path.stat().st_size:,} bytes). "
            f"Maximum is {MAX_READ_SIZE:,} bytes. Use offset/limit or the Shell tool."
        )
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            if offset is not None or limit is not None:
                lines = f.readlines()
                start = max(0, (offset or 1) - 1)
                end = start + limit if limit else len(lines)
                content = "".join(lines[start:end])
                return f"File: {file_path}\nLines {start + 1}-{min(end, len(lines))} of {len(lines)}:\n{content}"
            return f"File: {file_path}\n{f.read()}"
    except UnicodeDecodeError:
        return f'Error: Unable to read file as text with encoding "{encoding}". File may be binary.'
    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(
    path: str,
    content: str,
    append: bool = False,
    encoding: str = "utf-8",
    create_parents: bool = True,
) -> str:
    file_path = Path(path).resolve()
    try:
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "a" if append else "w", encoding=encoding) as f:
            f.write(content)
        action = "Appended to" if append else "Written to"
        return f"{action} {file_path} ({file_path.stat().st_size:,} bytes)"
    except PermissionError:
        return f"Error: Permission denied: {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


def copy_path(source: str, destination: str, overwrite: bool = False) -> str:
    src = Path(source).resolve()
    dst = Path(destination).resolve()
    if not src.exists():
        return f"Error: Source not found: {src}"
    if dst.exists() and not overwrite:
        return f"Error: Destination already exists: {dst}. Set overwrite=True to replace."
    try:
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            return f"Copied file: {src} -> {dst}"
        elif src.is_dir():
            if dst.exists() and overwrite:
                shutil.rmtree(str(dst))
            shutil.copytree(str(src), str(dst))
            return f"Copied directory: {src} -> {dst}"
        return f"Error: Unsupported file type: {src}"
    except PermissionError:
        return "Error: Permission denied."
    except Exception as e:
        return f"Error copying: {e}"


def move_path(source: str, destination: str, overwrite: bool = False) -> str:
    src = Path(source).resolve()
    dst = Path(destination).resolve()
    if not src.exists():
        return f"Error: Source not found: {src}"
    if dst.exists() and not overwrite:
        return f"Error: Destination already exists: {dst}. Set overwrite=True to replace."
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and overwrite:
            shutil.rmtree(str(dst)) if dst.is_dir() else dst.unlink()
        shutil.move(str(src), str(dst))
        return f"Moved: {src} -> {dst}"
    except PermissionError:
        return "Error: Permission denied."
    except Exception as e:
        return f"Error moving: {e}"


def delete_path(path: str, recursive: bool = False) -> str:
    target = Path(path).resolve()
    if not target.exists():
        return f"Error: Path not found: {target}"
    try:
        if target.is_file() or target.is_symlink():
            target.unlink()
            return f"Deleted file: {target}"
        elif target.is_dir():
            if not recursive:
                if any(target.iterdir()):
                    return f"Error: Directory is not empty: {target}. Set recursive=True to delete non-empty directories."
                target.rmdir()
            else:
                shutil.rmtree(str(target))
            return f"Deleted directory: {target}"
        return f"Error: Unsupported file type: {target}"
    except PermissionError:
        return f"Error: Permission denied: {target}"
    except Exception as e:
        return f"Error deleting: {e}"


def list_directory(
    path: str, pattern: str | None = None, recursive: bool = False, show_hidden: bool = False
) -> str:
    dir_path = Path(path).resolve()
    if not dir_path.exists():
        return f"Error: Directory not found: {dir_path}"
    if not dir_path.is_dir():
        return f"Error: Path is not a directory: {dir_path}"
    try:
        entries: list[str] = []
        count = 0
        iterator = dir_path.rglob(pattern or "*") if recursive else dir_path.iterdir()
        for entry in sorted(iterator, key=lambda e: (not e.is_dir(), e.name.lower())):
            if not show_hidden and entry.name.startswith("."):
                continue
            if pattern and not recursive and not fnmatch.fnmatch(entry.name, pattern):
                continue
            count += 1
            if count > MAX_RESULTS:
                entries.append(f"... (truncated, {MAX_RESULTS}+ items)")
                break
            try:
                size = entry.stat().st_size if entry.is_file() else 0
            except OSError:
                size = 0
            rel = str(entry.relative_to(dir_path)) if recursive else entry.name
            entries.append(Directory(name=entry.name, is_dir=entry.is_dir(), size=size).to_string(relative_path=rel))
        if not entries:
            filter_msg = f' matching "{pattern}"' if pattern else ""
            return f"Directory {dir_path} is empty{filter_msg}."
        header = f"Directory: {dir_path}"
        if pattern:
            header += f" (filter: {pattern})"
        return f"{header}\n" + "\n".join(entries)
    except PermissionError:
        return f"Error: Permission denied: {dir_path}"
    except Exception as e:
        return f"Error listing directory: {e}"


def search_files(path: str, pattern: str, recursive: bool = True) -> str:
    search_root = Path(path).resolve()
    if not search_root.exists():
        return f"Error: Search path not found: {search_root}"
    if not search_root.is_dir():
        return f"Error: Search path is not a directory: {search_root}"
    try:
        results: list[str] = []
        count = 0
        iterator = search_root.rglob(pattern) if recursive else search_root.glob(pattern)
        for match in sorted(iterator, key=lambda e: e.name.lower()):
            count += 1
            if count > MAX_RESULTS:
                results.append(f"... (truncated, {MAX_RESULTS}+ matches)")
                break
            try:
                size = match.stat().st_size if match.is_file() else 0
            except OSError:
                size = 0
            rel = str(match.relative_to(search_root))
            results.append(Directory(name=match.name, is_dir=match.is_dir(), size=size).to_string(relative_path=rel))
        if not results:
            return f'No matches found for "{pattern}" in {search_root}'
        return f'Search: "{pattern}" in {search_root} ({min(count, MAX_RESULTS)} matches)\n' + "\n".join(results)
    except PermissionError:
        return f"Error: Permission denied: {search_root}"
    except Exception as e:
        return f"Error searching: {e}"


def get_file_info(path: str) -> str:
    target = Path(path).resolve()
    if not target.exists():
        return f"Error: Path not found: {target}"
    try:
        stat = target.stat()
        file_type = (
            "Directory" if target.is_dir()
            else "File" if target.is_file()
            else "Symlink" if target.is_symlink()
            else "Other"
        )
        f = File(
            path=str(target),
            type=file_type,
            size=stat.st_size,
            created=datetime.fromtimestamp(stat.st_ctime),
            modified=datetime.fromtimestamp(stat.st_mtime),
            accessed=datetime.fromtimestamp(stat.st_atime),
            read_only=not os.access(target, os.W_OK),
        )
        if target.is_dir():
            try:
                items = list(target.iterdir())
                f.contents_dirs = sum(1 for i in items if i.is_dir())
                f.contents_files = sum(1 for i in items if i.is_file())
            except PermissionError:
                pass
        if target.is_file():
            f.extension = target.suffix or "(none)"
        if target.is_symlink():
            f.link_target = str(os.readlink(target))
        return f.to_string()
    except PermissionError:
        return f"Error: Permission denied: {target}"
    except Exception as e:
        return f"Error getting file info: {e}"


def get_latest_file(path: str) -> str:
    target_path = Path(path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        return f"Error: Invalid path: {target_path}"
    try:
        files = [f for f in target_path.iterdir() if f.is_file()]
        if not files:
            return "No files found in directory."
        latest = max(files, key=lambda f: f.stat().st_mtime)
        mod_time = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"Latest File: {latest.name}\nModified: {mod_time}\n"
            f"Size: {latest.stat().st_size:,} bytes\nPath: {latest}"
        )
    except Exception as e:
        return f"Error finding latest file: {e}"


def bulk_delete_by_extension(path: str, extension: str) -> str:
    target_path = Path(path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        return f"Error: Invalid path: {target_path}"
    if not extension.startswith("."):
        extension = "." + extension
    try:
        files_to_delete = list(target_path.glob(f"*{extension}"))
        if not files_to_delete:
            return f'No files matching "*{extension}" found in {target_path}'
        for f in files_to_delete:
            f.unlink()
        return f"Deleted {len(files_to_delete)} files with extension {extension} in {target_path}"
    except Exception as e:
        return f"Error during bulk delete: {e}"


def organize_folder(path: str) -> str:
    target_path = Path(path).resolve()
    if not target_path.exists() or not target_path.is_dir():
        return f"Error: Path does not exist or is not a directory: {target_path}"
    categories = {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic"],
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".pages", ".numbers", ".key"],
        "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".aiff"],
        "Video": [".mp4", ".mkv", ".flv", ".wmv", ".mov", ".avi", ".m4v"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".dmg", ".pkg"],
        "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".php", ".json", ".xml", ".swift", ".go", ".rs"],
    }
    try:
        moved_count = 0
        for item in target_path.iterdir():
            if not item.is_file():
                continue
            ext = item.suffix.lower()
            dest_category = next(
                (cat for cat, exts in categories.items() if ext in exts), "Others" if ext else None
            )
            if dest_category is None:
                continue
            dest_dir = target_path / dest_category
            dest_dir.mkdir(exist_ok=True)
            dest_file = dest_dir / item.name
            if dest_file.exists():
                dest_file = dest_dir / f"{item.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{item.suffix}"
            shutil.move(str(item), str(dest_file))
            moved_count += 1
        return f"Organized {target_path}: moved {moved_count} files into categories."
    except Exception as e:
        return f"Error organizing folder: {e}"
