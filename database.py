"""Persistent local SQLite data store. Compatible with StudyFlow V1 and V2."""
from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'studyflow.db'


def connect():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, subject TEXT NOT NULL, due_date TEXT NOT NULL,
            priority TEXT NOT NULL, estimated_hours REAL NOT NULL DEFAULT 1,
            completed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            name TEXT PRIMARY KEY, value TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL, session_date TEXT NOT NULL,
            hours REAL NOT NULL CHECK(hours > 0), note TEXT DEFAULT '',
            FOREIGN KEY(task_id) REFERENCES tasks(id))''')
        c.execute("INSERT OR IGNORE INTO settings(name,value) VALUES('daily_hours','3.0')")
        c.execute("INSERT OR IGNORE INTO settings(name,value) VALUES('start_time','09:00')")


def setting(name, default):
    with connect() as c:
        r = c.execute('SELECT value FROM settings WHERE name=?', (name,)).fetchone()
    return r['value'] if r else default


def save_setting(name, value):
    with connect() as c:
        c.execute('INSERT OR REPLACE INTO settings(name,value) VALUES(?,?)', (name, str(value)))


def all_tasks():
    with connect() as c:
        rows = c.execute('''SELECT t.*, COALESCE(SUM(s.hours),0) AS studied_hours
            FROM tasks t LEFT JOIN study_sessions s ON t.id=s.task_id
            GROUP BY t.id ORDER BY t.completed,t.due_date,
            CASE t.priority WHEN 'สูง' THEN 0 WHEN 'กลาง' THEN 1 ELSE 2 END,t.id DESC''').fetchall()
    return [dict(r) for r in rows]


def add_task(title, subject, due_date, priority, estimated_hours):
    with connect() as c:
        c.execute('''INSERT INTO tasks(title,subject,due_date,priority,estimated_hours,created_at)
                     VALUES(?,?,?,?,?,?)''', (title,subject,str(due_date),priority,
                        float(estimated_hours),datetime.now().isoformat()))


def update_task(tid, title, subject, due_date, priority, estimated_hours):
    with connect() as c:
        c.execute('''UPDATE tasks SET title=?,subject=?,due_date=?,priority=?,estimated_hours=?
                     WHERE id=?''', (title,subject,str(due_date),priority,float(estimated_hours),tid))


def mark_task(tid, done):
    with connect() as c:
        c.execute('UPDATE tasks SET completed=? WHERE id=?', (int(done), tid))


def delete_task(tid):
    with connect() as c:
        c.execute('DELETE FROM study_sessions WHERE task_id=?', (tid,))
        c.execute('DELETE FROM tasks WHERE id=?', (tid,))


def save_study(tid, session_date, hours, note=''):
    if hours <= 0:
        raise ValueError('Study time must be positive')
    with connect() as c:
        c.execute('''INSERT INTO study_sessions(task_id,session_date,hours,note)
                     VALUES(?,?,?,?)''', (tid,str(session_date),float(hours),note.strip()))


def sessions():
    with connect() as c:
        rows = c.execute('''SELECT s.*,t.title,t.subject FROM study_sessions s
               JOIN tasks t ON t.id=s.task_id ORDER BY s.session_date DESC,s.id DESC''').fetchall()
    return [dict(r) for r in rows]
