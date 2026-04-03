from pathlib import Path
import fnmatch
from datetime import datetime, timedelta

root = Path(r"c:\#1-CRIAÇÕES-AUTOMAÇÕES-EXTENSÕES\ig-fb-reels-bot - Copia")
max_log_days = 7

def is_old_log(path: Path, max_days: int) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return (datetime.now() - mtime) > timedelta(days=max_days)
    except Exception:
        return False

for item in root.iterdir():
    if not item.is_file(): continue
    item_name = item.name
    
    print(f"Checking: {item_name}")
    if fnmatch.fnmatch(item_name, "final_debug_log*.txt") or item_name == "debug_log.txt":
        if is_old_log(item, max_log_days):
            print(f"  [SAFE] Old Log: {item_name}")
        else:
            print(f"  [REVIEW] Recent Log: {item_name}")
    
    if fnmatch.fnmatch(item_name, "schedule_queue_backup_*.json"):
        print(f"  [REVIEW] Backup: {item_name}")
    
    if fnmatch.fnmatch(item_name, "temp_*.json") or item_name == "temp_save.json":
        print(f"  [SAFE] Temp: {item_name}")
