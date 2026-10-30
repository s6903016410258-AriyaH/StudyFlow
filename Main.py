"""StudyFlow V3 · Run with: python -m streamlit run Main.py"""
from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta
from html import escape
import time

import plotly.graph_objects as go
import streamlit as st

import database as storage
from scheduler import build_schedule, to_time_slots

st.set_page_config(page_title='StudyFlow | Smart Study Planner', page_icon='📚',
                   layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'Prompt','Tahoma','Segoe UI',sans-serif}
.stApp {background:#0d1426;color:#e9eeff}
[data-testid="stSidebar"] {background:#131d35;border-right:1px solid #263755}
[data-testid="stHeader"] {background:transparent}
h1,h2,h3 {color:#f6f8ff!important;letter-spacing:-.02em}
h1 {font-size:2.1rem!important} h2,h3 {font-size:1.25rem!important}
[data-testid="stMetric"] {background:linear-gradient(150deg,#202d4a,#18223b);
    border:1px solid #324467;border-radius:18px;padding:15px 17px}
[data-testid="stMetricLabel"] {color:#b4c5e8}
[data-testid="stMetricValue"] {color:#fff}
.stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"]
    {background:linear-gradient(110deg,#766af2,#5a91e7);color:white;border:0}
.stButton button:hover {border-color:#aca5ff}
[data-testid="stForm"], [data-testid="stExpander"] {border-color:#324363}
.hero {background:linear-gradient(115deg,#24345f,#20274d 56%,#3b2c62);
      border:1px solid #3e5182;border-radius:22px;padding:23px 28px;margin-bottom:22px}
.hero-title {color:white;font-size:1.65rem;font-weight:700;margin:0}
.hero-small {color:#c4cffa;margin-top:8px;font-size:.95rem}
.small-muted {color:#abbcdf;font-size:.85rem}
.task-row {background:#1a2944;border:1px solid #32425f;border-radius:12px;
  padding:12px 15px;margin:7px 0}
.task-row small {color:#b7c6e3}
.week-card {background:#17233d;border:1px solid #314260;border-radius:14px;
    padding:12px 10px;min-height:190px;height:100%}
.week-label {font-weight:700;color:#f2f5ff;font-size:.92rem}
.week-date {color:#aebdde;font-size:.78rem;margin-bottom:12px}
.slot {background:#283957;border-left:3px solid #9687ff;border-radius:7px;
      padding:8px;margin:7px 0;line-height:1.45;font-size:.81rem;overflow-wrap:anywhere}
.slot-time {color:#b7d7ff;font-size:.75rem;margin-bottom:3px}
.kpi-sub {color:#adbfe0;font-size:.8rem}
div[data-testid="stRadio"] label {font-size:.96rem}
</style>''', unsafe_allow_html=True)

storage.init_db()
tasks = storage.all_tasks()
pending = [t for t in tasks if not t['completed']]
done = [t for t in tasks if t['completed']]
sessions = storage.sessions()
today = date.today()
daily_hours = float(storage.setting('daily_hours', '3'))
start_time = storage.setting('start_time', '09:00')
plan, issues = build_schedule(pending, daily_hours, today=today, horizon=35)
slots = to_time_slots(plan, start_time)
by_date = defaultdict(list)
for slot in slots:
    by_date[slot['date']].append(slot)
progress = len(done)/len(tasks) if tasks else 0
studied_total = sum(s['hours'] for s in sessions)


def remaining(task):
    return max(0, float(task['estimated_hours'])-float(task['studied_hours']))


def deadline_delta(task):
    return (date.fromisoformat(task['due_date'])-today).days


def due_label(task):
    d = deadline_delta(task)
    if d < 0: return f'เลยกำหนด {abs(d)} วัน'
    if d == 0: return 'ถึงกำหนดวันนี้'
    if d == 1: return 'เหลือ 1 วัน'
    return f'เหลือ {d} วัน'


urgent = sorted([t for t in pending if deadline_delta(t) <= 3],
                key=lambda t: (t['due_date'], t['id']))


def notice():
    """In-app notification only; this does not send push/email alerts."""
    if urgent:
        st.warning(f'🔔 มีงานใกล้กำหนดหรือเลยกำหนด {len(urgent)} งาน')
        for t in urgent[:6]:
            st.markdown(f'**{escape(t["title"])}** · {escape(t["subject"])} · {due_label(t)}')


def card(task):
    badge = '🔴' if deadline_delta(task) <= 1 else ('🟠' if deadline_delta(task) <= 3 else '🔵')
    st.markdown(f'<div class="task-row">{badge} <b>{escape(task["title"])}</b><br>'
        f'<small>{escape(task["subject"])} · {escape(task["due_date"])} · '
        f'{due_label(task)} · เหลือ {remaining(task):.2f} ชม.</small></div>',
        unsafe_allow_html=True)


with st.sidebar:
    st.markdown('## 📚 StudyFlow')
    st.caption('SMART STUDY PLANNER · V3')
    st.divider()
    page = st.radio('เมนู', [
        '🏠 Dashboard', '➕ เพิ่มงาน', '📝 งานทั้งหมด', '🧠 Smart Schedule',
        '📅 Weekly Calendar', '🍅 Pomodoro Timer', '⏱️ บันทึกเวลาอ่าน',
        '📊 สถิติ', '⚙️ ตั้งค่า'
    ], label_visibility='collapsed')
    st.divider()
    if urgent:
        st.markdown(f'🔔 **แจ้งเตือน {len(urgent)} งาน**')
        st.caption('มีงานถึงกำหนดภายใน 3 วัน หรือเกินกำหนด')
    st.caption('💾 ข้อมูลอยู่ใน studyflow.db บนเครื่องของคุณ')

if page == '🏠 Dashboard':
    st.markdown('''<div class="hero"><div class="hero-title">👋 พร้อมลุยกันต่อไหม?</div>
    <div class="hero-small">จัดการการบ้าน เตรียมสอบ และทำตามแผนอ่านหนังสือในที่เดียว</div></div>''',
    unsafe_allow_html=True)
    columns = st.columns(4)
    for c, label, value in zip(columns,
            ['📚 งานทั้งหมด', '✅ ทำเสร็จ', '⏳ ค้างอยู่', '🎯 ความคืบหน้า'],
            [len(tasks), len(done), len(pending), f'{progress:.0%}']):
        c.metric(label, value)
    st.markdown('### ความคืบหน้าโดยรวม')
    st.progress(progress)
    st.caption(f'เสร็จ {len(done)}/{len(tasks)} งาน · เวลาอ่านจริงสะสม {studied_total:.2f} ชั่วโมง')
    notice()
    left, right = st.columns([1.35, 1], gap='large')
    with left:
        st.subheader('📌 งานที่ต้องทำต่อ')
        if not pending: st.info('ยังไม่มีงานค้าง ไปที่เมนู เพิ่มงาน ได้เลย')
        for task in pending[:5]: card(task)
    with right:
        st.subheader('📅 แผนอ่านวันนี้')
        entries = by_date.get(today.isoformat(), [])
        if not entries: st.info('วันนี้ยังไม่มีรายการที่ต้องอ่าน')
        for row in entries:
            with st.container(border=True):
                st.markdown(f'**{escape(row["title"])}**')
                st.caption(f'{row["start"]}–{row["end"]} · {row["hours"]:.2f} ชม.')
        if issues: st.warning(f'มี {len(issues)} รายการที่จัดแผนไม่ครบ/เกินกำหนด ดูที่ Smart Schedule')

elif page == '➕ เพิ่มงาน':
    st.title('➕ เพิ่มงานใหม่')
    st.write('เพิ่มการบ้าน งานโปรเจกต์ หรือเนื้อหาที่ต้องอ่านก่อนสอบ')
    with st.form('create_task', clear_on_submit=True):
        title = st.text_input('ชื่องาน *', placeholder='อ่านสอบ Python Functions')
        subject = st.text_input('รายวิชา *', placeholder='Python Programming')
        due = st.date_input('กำหนดส่ง / วันสอบ', value=today + timedelta(days=4))
        p = st.selectbox('ความสำคัญ', ['กลาง','สูง','ต่ำ'])
        hours = st.number_input('ชั่วโมงที่ต้องใช้ทั้งหมด', min_value=0.5,
                                max_value=200.0, value=4.0, step=0.5)
        submitted = st.form_submit_button('💾 บันทึกงาน', type='primary')
    if submitted:
        if not title.strip() or not subject.strip():
            st.error('กรุณากรอกชื่องานและรายวิชา')
        else:
            storage.add_task(title.strip(), subject.strip(), due, p, hours)
            st.rerun()

elif page == '📝 งานทั้งหมด':
    st.title('📝 จัดการงานทั้งหมด')
    if not tasks: st.info('ยังไม่มีงาน เริ่มจากเมนู เพิ่มงาน')
    for task in tasks:
        with st.container(border=True):
            first, second = st.columns([5,1])
            with first:
                checked = st.checkbox(task['title'], bool(task['completed']),
                                      key=f'completed_{task["id"]}')
                st.caption(f'{task["subject"]} · ส่ง {task["due_date"]} · '
                           f'ระดับ {task["priority"]} · อ่าน {task["studied_hours"]:.2f}/'
                           f'{task["estimated_hours"]:g} ชม.')
                if checked != bool(task['completed']):
                    storage.mark_task(task['id'], checked)
                    st.rerun()
            with second:
                if st.button('🗑️ ลบ', key=f'delete_{task["id"]}'):
                    storage.delete_task(task['id'])
                    st.rerun()
            with st.expander('✏️ แก้ไขงาน'):
                with st.form(f'edit_{task["id"]}'):
                    nt = st.text_input('ชื่องาน', task['title'])
                    ns = st.text_input('รายวิชา', task['subject'])
                    nd = st.date_input('วันกำหนด', date.fromisoformat(task['due_date']))
                    priorities = ['สูง','กลาง','ต่ำ']
                    np = st.selectbox('ความสำคัญ', priorities,
                                      index=priorities.index(task['priority']) if task['priority'] in priorities else 1)
                    nh = st.number_input('ชั่วโมงทั้งหมด', min_value=0.5, max_value=200.,
                                         value=float(task['estimated_hours']), step=0.5)
                    if st.form_submit_button('บันทึกการแก้ไข'):
                        if nt.strip() and ns.strip():
                            storage.update_task(task['id'], nt.strip(), ns.strip(), nd, np, nh)
                            st.rerun()
                        else: st.error('ชื่องานและวิชาห้ามว่าง')

elif page == '🧠 Smart Schedule':
    st.title('🧠 Smart Schedule')
    st.write('ระบบแบ่งชั่วโมงให้อัตโนมัติจากวันกำหนด เวลาที่ต้องอ่าน และเวลาว่างต่อวัน')
    a, b, c = st.columns(3)
    a.metric('เวลาว่างต่อวัน', f'{daily_hours:g} ชม.')
    b.metric('เวลาเริ่มต้น', start_time)
    c.metric('ชั่วโมงในแผน 35 วัน', f'{sum(x["hours"] for x in plan):.2f} ชม.')
    st.caption('ระบบพยายามอ่านให้เสร็จก่อนวันสอบ และกระจายชั่วโมงอย่างเหมาะสม โดยไม่เกินเวลาที่ตั้งไว้')
    for msg in issues: st.warning(msg)
    if not pending: st.info('เพิ่มงานที่ยังไม่เสร็จเพื่อสร้างแผน')
    elif not plan: st.info('ยังไม่มีชั่วโมงที่จัดลงตาราง ตรวจสอบวันกำหนดและชั่วโมงคงเหลือ')
    else:
        st.subheader('📆 แผนอ่านหนังสือรายวัน')
        for i in range(14):
            day = today + timedelta(days=i)
            items = by_date.get(day.isoformat(), [])
            if not items: continue
            total = sum(r['minutes'] for r in items)/60
            with st.expander(f'📅 {day:%d/%m/%Y} · {total:.2f}/{daily_hours:g} ชม.',
                             expanded=(i == 0)):
                for row in items:
                    st.markdown(f'**{row["start"]}–{row["end"]}** · '
                                f'{escape(row["title"])} ({escape(row["subject"])}) '
                                f'· {row["hours"]:.2f} ชม.')
        xs = [today + timedelta(days=i) for i in range(14)]
        values = [sum(r['minutes'] for r in by_date.get(x.isoformat(), []))/60 for x in xs]
        fig = go.Figure(go.Bar(x=[x.isoformat() for x in xs], y=values,
                               marker_color='#978aff', name='แผนอ่าน'))
        fig.add_hline(y=daily_hours, line_dash='dash', line_color='#4bd1c7')
        fig.update_layout(height=320, margin=dict(l=12,r=10,t=25,b=15),
            xaxis_title='วันที่',yaxis_title='ชั่วโมง',paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',font_color='#e7edff')
        st.plotly_chart(fig, use_container_width=True)
        st.info('📅 ดูช่วงเวลาจริงในหน้า Weekly Calendar และตั้งเวลาเริ่มต้นได้ในหน้า ตั้งค่า')

elif page == '📅 Weekly Calendar':
    st.title('📅 Weekly Calendar')
    st.write('ดูแผนการอ่านหนังสือเป็นรายสัปดาห์ พร้อมเวลาเริ่มต้น–สิ้นสุดของแต่ละวิชา')
    week = st.select_slider('สัปดาห์ที่ต้องการ', options=list(range(1,6)),
                            value=1, format_func=lambda n: f'สัปดาห์ {n}')
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week-1)
    st.caption(f'แผนสำหรับ {monday:%d/%m/%Y} – {(monday+timedelta(days=6)):%d/%m/%Y} '
               f'· เวลาเริ่ม {start_time} · ว่าง {daily_hours:g} ชม./วัน')
    columns = st.columns(7, gap='small')
    weekday_names = ['จันทร์','อังคาร','พุธ','พฤหัส','ศุกร์','เสาร์','อาทิตย์']
    for offset, col in enumerate(columns):
        day = monday + timedelta(days=offset)
        entry = by_date.get(day.isoformat(), [])
        inside = f'<div class="week-label">{weekday_names[offset]}</div><div class="week-date">{day:%d/%m}</div>'
        if entry:
            for e in entry:
                inside += ('<div class="slot"><div class="slot-time">'
                          f'{e["start"]}–{e["end"]}</div>'
                          f'<b>{escape(e["subject"])}</b><div>{escape(e["title"])}</div></div>')
        else:
            inside += '<div class="small-muted">ไม่มีแผน</div>'
        with col:
            st.markdown(f'<div class="week-card">{inside}</div>',unsafe_allow_html=True)
    if issues: st.warning(f'มี {len(issues)} งานที่ต้องตรวจสอบกำหนดส่ง/เวลาว่าง ดูรายละเอียดใน Smart Schedule')
    st.caption('ตารางนี้เป็นเวลาที่แนะนำ ไม่ใช่การจองเวลาจริงในปฏิทิน Google และยังไม่คำนึงถึงคาบเรียนหรือการเดินทาง')

elif page == '🍅 Pomodoro Timer':
    st.title('🍅 Pomodoro Timer')
    st.write('อ่านหนังสือ 25 นาที พัก 5 นาที และบันทึกเวลาอ่านจริงลง StudyFlow')
    if not pending:
        st.info('ต้องมีงานที่ยังไม่เสร็จก่อน จึงจะบันทึกเวลาอ่านด้วย Timer ได้')
    else:
        options = {f'#{t["id"]} · {t["title"]}':t['id'] for t in pending}
        selected = st.selectbox('กำลังอ่านงานไหน?', list(options))
        selected_id = options[selected]
        for key, value in {
            'timer_mode':'focus', 'timer_running':False, 'timer_remaining':1500,
            'timer_total':1500, 'timer_end':0., 'timer_task':None
        }.items():
            if key not in st.session_state: st.session_state[key] = value

        @st.fragment(run_every='1s')
        def timer_panel():
            s = st.session_state
            if s.timer_running:
                remaining_seconds = max(0, int(s.timer_end - time.time() + .5))
                if remaining_seconds == 0:
                    s.timer_running = False
                    s.timer_remaining = 0
            else:
                remaining_seconds = int(s.timer_remaining)
            elapsed = s.timer_total - remaining_seconds
            mode_name = '📖 ช่วงตั้งใจอ่าน' if s.timer_mode == 'focus' else '☕ ช่วงพัก'
            st.subheader(mode_name)
            st.markdown(f'### {remaining_seconds//60:02d}:{remaining_seconds%60:02d}')
            st.progress(min(1., max(0., elapsed/max(1,s.timer_total))))
            if remaining_seconds == 0:
                st.success('⏰ หมดเวลาแล้ว! กดบันทึกเพื่อเก็บเวลาอ่าน หรือสลับช่วงพัก')
            if s.timer_task is not None and s.timer_mode == 'focus':
                st.caption(f'กำลังจับเวลาให้งานรหัส #{s.timer_task}')
            a,b,c = st.columns(3)
            with a:
                if s.timer_running:
                    if st.button('⏸ หยุดชั่วคราว', use_container_width=True):
                        s.timer_remaining = remaining_seconds
                        s.timer_running = False
                        st.rerun()
                elif remaining_seconds > 0:
                    if st.button('▶ เริ่ม / ต่อเวลา', type='primary', use_container_width=True):
                        if s.timer_mode == 'focus' and s.timer_task is None:
                            s.timer_task = selected_id
                        s.timer_end = time.time() + s.timer_remaining
                        s.timer_running = True
                        st.rerun()
            with b:
                if st.button('↻ เริ่มรอบใหม่', use_container_width=True):
                    s.timer_running = False
                    s.timer_total = 1500 if s.timer_mode == 'focus' else 300
                    s.timer_remaining = s.timer_total
                    s.timer_task = None
                    st.rerun()
            with c:
                if st.button('☕ สลับ อ่าน / พัก', use_container_width=True):
                    s.timer_running = False
                    s.timer_mode = 'break' if s.timer_mode == 'focus' else 'focus'
                    s.timer_total = 1500 if s.timer_mode == 'focus' else 300
                    s.timer_remaining = s.timer_total
                    s.timer_task = None
                    st.rerun()
            if s.timer_mode == 'focus':
                duration_minutes = elapsed / 60
                st.caption(f'อ่านจริงในรอบนี้ {duration_minutes:.1f} นาที (นับเฉพาะเวลาที่จับอยู่)')
                if st.button('💾 จบรอบและบันทึกเวลาอ่าน', disabled=(duration_minutes < 1),
                             type='primary', use_container_width=True):
                    task_id = s.timer_task or selected_id
                    storage.save_study(task_id, today, round(duration_minutes/60, 6),
                                       'บันทึกจาก Pomodoro Timer')
                    s.timer_running = False
                    s.timer_total = 1500
                    s.timer_remaining = 1500
                    s.timer_task = None
                    st.rerun()
            else:
                st.caption('ช่วงพักไม่ถูกบันทึกเป็นเวลาอ่านหนังสือ')
        timer_panel()
        st.caption('Timer ใช้เวลาในเบราว์เซอร์และ session ของ Streamlit เมื่อรีสตาร์ทโปรแกรมเวลาในรอบที่ยังไม่บันทึกอาจหายได้ ควรกดบันทึกหลังอ่านเสร็จ')

elif page == '⏱️ บันทึกเวลาอ่าน':
    st.title('⏱️ บันทึกเวลาอ่าน')
    st.write('บันทึกเวลาที่อ่านจริง เพื่อให้ Smart Schedule ปรับเวลาคงเหลือ')
    if pending:
        options = {f'#{t["id"]} · {t["title"]} ({t["subject"]})':t['id'] for t in pending}
        with st.form('log_study', clear_on_submit=True):
            chosen = st.selectbox('เลือกงาน', list(options))
            when = st.date_input('วันที่อ่าน', value=today, max_value=today)
            hours = st.number_input('อ่านกี่ชั่วโมง', min_value=0.25,
                                    max_value=16., value=1., step=.25)
            note = st.text_input('หมายเหตุ', placeholder='เช่น ทบทวนบท Functions')
            if st.form_submit_button('💾 บันทึกเวลาอ่าน', type='primary'):
                storage.save_study(options[chosen], when, hours, note)
                st.rerun()
    else: st.info('ยังไม่มีงานที่ยังไม่เสร็จ')
    st.subheader('ประวัติการอ่าน')
    if not sessions: st.info('ยังไม่มีประวัติการอ่าน')
    for s in sessions[:30]:
        st.markdown(f'**{escape(s["title"])}** · {s["session_date"]} · {s["hours"]:.2f} ชม.')
        if s['note']: st.caption(s['note'])

elif page == '📊 สถิติ':
    st.title('📊 Study Statistics')
    a,b,c = st.columns(3)
    a.metric('งานที่เสร็จ', f'{len(done)}/{len(tasks)}')
    b.metric('ชั่วโมงที่อ่านจริง', f'{studied_total:.2f}')
    c.metric('งานคงเหลือ', len(pending))
    st.progress(progress)
    if sessions:
        by_day = defaultdict(float)
        for s in sessions: by_day[s['session_date']] += s['hours']
        days = sorted(by_day)
        fig = go.Figure(go.Bar(x=days, y=[round(by_day[d],2) for d in days],
                               marker_color='#8b86f7'))
        fig.update_layout(title='ชั่วโมงอ่านจริงในแต่ละวัน', height=350,
           margin=dict(l=20,r=20,t=50,b=25), yaxis_title='ชั่วโมง',
           paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
           font_color='#edf1ff')
        st.plotly_chart(fig,use_container_width=True)
        subjects = defaultdict(float)
        for s in sessions: subjects[s['subject']] += s['hours']
        chart = go.Figure(go.Pie(labels=list(subjects),values=list(subjects.values()),hole=.58))
        chart.update_layout(title='สัดส่วนเวลาอ่านตามวิชา', height=350,
            margin=dict(l=15,r=15,t=55,b=25), paper_bgcolor='rgba(0,0,0,0)',
            font_color='#edf1ff')
        st.plotly_chart(chart,use_container_width=True)
    else: st.info('เมื่อบันทึกเวลาอ่านแล้ว กราฟสถิติจะแสดงที่นี่')

elif page == '⚙️ ตั้งค่า':
    st.title('⚙️ ตั้งค่าตารางอ่านหนังสือ')
    st.write('เลือกเวลาว่างต่อวันและเวลาเริ่มต้นที่ต้องการ')
    with st.form('settings'):
        new_hours = st.number_input('เวลาว่างต่อวัน (ชั่วโมง)', min_value=.5,
                                    max_value=12., step=.5, value=daily_hours)
        parsed = dt_time.fromisoformat(start_time)
        new_start = st.time_input('เริ่มอ่านหนังสือเวลา', value=parsed, step=1800)
        if st.form_submit_button('💾 บันทึกการตั้งค่า',type='primary'):
            if new_start.hour * 60 + new_start.minute + int(new_hours*60) > 24*60:
                st.error('ช่วงเวลาอ่านเกินเที่ยงคืน กรุณาลดจำนวนชั่วโมงหรือเลื่อนเวลาเริ่มให้เร็วขึ้น')
            else:
                storage.save_setting('daily_hours', new_hours)
                storage.save_setting('start_time', new_start.strftime('%H:%M'))
                st.rerun()
    st.info('แจ้งเตือนเฉพาะตอนเปิดเว็บ StudyFlow ไม่มีการส่งแจ้งเตือนผ่านอีเมลหรือโทรศัพท์')
    st.caption('ข้อมูลของคุณเก็บในไฟล์ studyflow.db ภายในโฟลเดอร์ V3 เท่านั้น')
