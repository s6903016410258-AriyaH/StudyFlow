"""Deadline-aware and capacity-limited study planning (local; no AI API)."""
from __future__ import annotations
from datetime import date, timedelta
import math


def _minutes(hours):
    return max(0, int(round(float(hours) * 60)))


def build_schedule(tasks, hours_per_day=3.0, today=None, horizon=14):
    """Return (allocation_rows, warnings).

    Each row includes date, task_id, title, subject, minutes, hours, due_date,
    priority. A deadline is excluded as a study day unless it is *today*.
    Study logs are subtracted. Allocations never exceed the remaining work or
    daily capacity, including fractional minutes recorded by the timer.
    """
    today = today or date.today()
    horizon = max(1, min(int(horizon), 90))
    capacity = _minutes(hours_per_day)
    end = today + timedelta(days=horizon - 1)
    priority = {"สูง": 0, "กลาง": 1, "ต่ำ": 2}
    work = []
    warnings = []

    for t in tasks:
        if t.get("completed"):
            continue
        remaining = _minutes(t["estimated_hours"]) - _minutes(t.get("studied_hours") or 0)
        if remaining <= 0:
            continue
        due = date.fromisoformat(str(t["due_date"]))
        if due < today:
            warnings.append(f"'{t['title']}' เลยกำหนดแล้ว ({due:%d/%m/%Y}) กรุณาปรับวันกำหนดก่อนจัดแผน")
            continue
        last_day = max(today, due - timedelta(days=1))
        work.append(dict(
            id=t["id"], title=t["title"], subject=t["subject"],
            due_date=due, last_day=last_day, priority=t["priority"],
            remaining=remaining,
        ))

    result = []
    for offset in range(horizon):
        day = today + timedelta(days=offset)
        free = capacity
        today_used = {j['id']: 0 for j in work}
        targets = {}
        for j in work:
            days_left = (j['last_day'] - day).days + 1
            if j['remaining'] > 0 and days_left > 0:
                # Fair share prevents finishing distant exams too far in advance.
                targets[j['id']] = math.ceil(j['remaining'] / days_left)

        while free > 0:
            candidates = [j for j in work if j['remaining'] > 0
                          and day <= j['last_day']
                          and today_used[j['id']] < targets.get(j['id'], 0)]
            if not candidates:
                break
            candidates.sort(key=lambda j: (
                -(j['remaining'] / max(1, (j['last_day'] - day).days + 1)),
                j['last_day'], priority.get(j['priority'], 1), j['id']))
            j = candidates[0]
            amount = min(30, free, j['remaining'], targets[j['id']] - today_used[j['id']])
            if amount <= 0:
                break
            j['remaining'] -= amount
            today_used[j['id']] += amount
            free -= amount

        for j in work:
            minutes = today_used[j['id']]
            if minutes:
                result.append(dict(date=day.isoformat(), task_id=j['id'],
                                   title=j['title'], subject=j['subject'],
                                   due_date=j['due_date'].isoformat(),
                                   priority=j['priority'], minutes=minutes,
                                   hours=round(minutes / 60, 4)))

    for j in work:
        if j['remaining'] and j['last_day'] <= end:
            warnings.append(f"'{j['title']}' ยังจัดไม่ครบ {j['remaining']/60:g} ชม. ก่อนกำหนด "
                            "ลองเพิ่มเวลาว่างต่อวันหรือเปลี่ยนกำหนดส่ง")
    return result, warnings


def to_time_slots(rows, start_time="09:00"):
    """Attach start/end local clock strings to each day's sequential allocations."""
    hour, minute = (int(x) for x in start_time.split(':'))
    start = hour * 60 + minute
    cursors = {}
    slots = []
    for r in sorted(rows, key=lambda x: (x['date'], x['due_date'], x['task_id'])):
        cursor = cursors.get(r['date'], start)
        finish = cursor + int(r['minutes'])
        fmt = lambda m: f"{m // 60:02d}:{m % 60:02d}"  # may show 24:xx for large windows
        slots.append({**r, 'start': fmt(cursor), 'end': fmt(finish)})
        cursors[r['date']] = finish
    return slots
