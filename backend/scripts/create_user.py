#!/usr/bin/env python
"""建立或重設一個登入帳號。

這個系統沒有公開註冊端點 - 帳號都是像這樣直接對資料庫手動建立的。

用法（在 backend/ 目錄下執行）：
    python scripts/create_user.py

會互動式詢問帳號與密碼（密碼輸入不會顯示在畫面上，也不會被記錄）。如果帳
號已存在，會問你要不要把密碼重設成新輸入的這組。
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import models  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def main():
    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            confirm = input(f'"{username}" already exists - reset their password? [y/N] ').strip().lower()
            if confirm != "y":
                print("Cancelled.")
                sys.exit(0)

        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        if not password:
            print("Password cannot be empty.")
            sys.exit(1)
        if password != password_confirm:
            print("Passwords didn't match.")
            sys.exit(1)

        if existing:
            existing.password_hash = hash_password(password)
            db.commit()
            print(f'Password updated for "{username}".')
        else:
            user = models.User(username=username, password_hash=hash_password(password))
            db.add(user)
            db.commit()
            print(f'Created account "{username}".')
    finally:
        db.close()


if __name__ == "__main__":
    main()
