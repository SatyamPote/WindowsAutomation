import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import fnmatch

# Add project root to path so we can import windows_mcp
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from windows_mcp import filesystem

def get_downloads_path():
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location
    return str(Path.home() / "Downloads")

def main():
    parser = argparse.ArgumentParser(description="FM - Simple File Manager CLI")
    parser.add_argument("action", help="Action: create, read, write, append, delete, rename, folder, list, search, move, copy, info, organize, bulk-delete, latest")
    parser.add_argument("target", nargs="?", help="Target file or directory")
    parser.add_argument("extra", nargs="*", help="Extra arguments (content for write, destination for move, etc.)")

    args = parser.parse_args()
    
    action = args.action.lower()
    target = args.target
    extra_args = args.extra
    extra_text = " ".join(extra_args) if extra_args else ""

    try:
        if action == "create":
            if not target: print("Error: Target required"); return
            p = Path(target)
            if p.suffix:
                p.touch()
                print(f"Created file: {p}")
            else:
                p.mkdir(parents=True, exist_ok=True)
                print(f"Created folder: {p}")
        
        elif action == "read":
            if not target: print("Error: Target required"); return
            print(filesystem.read_file(target))
            
        elif action == "write":
            if not target: print("Error: Target required"); return
            print(filesystem.write_file(target, extra_text, append=False))
            
        elif action == "append":
            if not target: print("Error: Target required"); return
            print(filesystem.write_file(target, extra_text, append=True))
            
        elif action == "delete":
            if not target: print("Error: Target required"); return
            print(filesystem.delete_path(target, recursive=True))
            
        elif action == "rename" or action == "move":
            if not target or not extra_text: print("Error: Source and destination required"); return
            print(filesystem.move_path(target, extra_text))
            
        elif action == "copy":
            if not target or not extra_text: print("Error: Source and destination required"); return
            print(filesystem.copy_path(target, extra_text))
            
        elif action == "folder":
            if not target: print("Error: Folder name required"); return
            Path(target).mkdir(parents=True, exist_ok=True)
            print(f"Created folder: {target}")
            
        elif action == "list":
            print(filesystem.list_directory(target or "."))
            
        elif action == "search":
            if not target: print("Error: Pattern required"); return
            print(filesystem.search_files(extra_text or ".", target))
            
        elif action == "info":
            if not target: print("Error: Target required"); return
            print(filesystem.get_file_info(target))
            
        elif action == "organize":
            path = target if target and target.lower() != "downloads" else get_downloads_path()
            print(filesystem.organize_folder(path))
            
        elif action == "bulk-delete":
            if not target: print("Error: Extension required"); return
            path = extra_text or "."
            print(filesystem.bulk_delete_by_extension(path, target))
            
        elif action == "latest":
            print(filesystem.get_latest_file(target or "."))
            
        else:
            print(f"Unknown action: {action}")
            parser.print_help()
            
        else:
            print(f"Unknown action: {action}")
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
