#!/usr/bin/env python
"""把「指令大全」資料匯入 bash_commands 表(見 app/models/bash_command.py、
routers/bash_reference.py 的搜尋功能用這張表)。

用法(在 backend/ 目錄下執行):
    python scripts/import_bash_commands.py data.json

data.json 是一個陣列,每筆至少要有 command / description 兩個欄位,例如:
    [
      {"command": "grep", "description": "在檔案內容中搜尋符合樣式的行"},
      {"command": "chmod", "description": "變更檔案或目錄的權限"}
    ]

同一個 command 重複匯入會直接覆蓋舊的 description(用 command 當 key upsert),
所以這支腳本可以重複執行來更新資料,不用先清空資料表。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_bash_commands.py <data.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        print("Expected a JSON array of {command, description} objects.")
        sys.exit(1)

    db = SessionLocal()
    try:
        created, updated = 0, 0
        for entry in entries:
            command = (entry.get("command") or "").strip()
            description = (entry.get("description") or "").strip()
            if not command or not description:
                continue
            existing = db.query(models.BashCommand).filter(models.BashCommand.command == command).first()
            if existing:
                existing.description = description
                updated += 1
            else:
                db.add(models.BashCommand(command=command, description=description))
                created += 1
        db.commit()
        print(f"Done - {created} created, {updated} updated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
