
import sqlite3
from flask import current_app, g


def get_db():
    """获取当前请求使用的数据库连接"""
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db

    return g.db


def close_db(error=None):
    """请求结束后关闭数据库连接"""
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    """自动创建数据库表"""
    db = get_db()

    db.executescript("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT '其他',
            publisher TEXT DEFAULT '',
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notice_deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            deadline_date TEXT NOT NULL,
            status INTEGER NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            FOREIGN KEY (notice_id)
                REFERENCES notices(id)
                ON DELETE CASCADE
        );
    """)

    db.commit()
