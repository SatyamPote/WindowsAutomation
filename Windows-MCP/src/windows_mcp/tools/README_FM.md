# FM - Terminal-Based File Manager

`fm` is a powerful, lightweight CLI tool for managing your Windows filesystem.

## Installation
Add the following to your PATH or use the `fm.bat` wrapper in the `bin` directory:
```bash
python -m windows_mcp.tools.fm <action> <target> [extra]
```

## Supported Commands

| Action | Usage | Description |
|---|---|---|
| `create` | `fm create <name>` | Create a new file (if has extension) or folder |
| `read` | `fm read <file>` | Read file contents |
| `write` | `fm write <file> <content...>` | Overwrite file with new content |
| `append` | `fm append <file> <content...>` | Append text to end of file |
| `delete` | `fm delete <path>` | Delete file or folder (recursive) |
| `rename` | `fm rename <old> <new>` | Rename or move a file/folder |
| `folder` | `fm folder <name>` | Create a directory |
| `list` | `fm list [path]` | List directory contents |
| `search` | `fm search <pattern> [path]`| Search for files by pattern |
| `move` | `fm move <src> <dst>` | Move file/folder |
| `copy` | `fm copy <src> <dst>` | Copy file/folder |
| `info` | `fm info <path>` | Show detailed file/folder metadata |
| `organize` | `fm organize [path]` | Auto-sort files into categories (Images, Docs, etc.) |
| `bulk-delete`| `fm bulk-delete <ext> [path]`| Delete all files with specific extension |
| `latest` | `fm latest [path]` | Find the most recently modified file |

## Examples
- `fm organize downloads`
- `fm write notes.txt Hello World`
- `fm bulk-delete .tmp`
- `fm search *.pdf Documents`

## Requirements
- Python 3.10+
- `pathlib`, `shutil`, `os` (Standard Library)
