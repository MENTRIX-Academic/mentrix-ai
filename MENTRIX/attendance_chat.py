"""Strictly grounded structured attendance queries. No LLM needed or permitted for student records."""
from __future__ import annotations
import re
from attendance_integration import connect

TRIGGERS=('حضر','محضر','غياب','غاب','غايب','غيابات','غيبة','حضور','السكشن','سكشن','absence','absent','attendance','present','session','section','attended')
def attendance_intent(q):
    lower=q.lower()
    return any(k in lower for k in TRIGGERS)

def ask_attendance(question):
    s=question.lower().strip()
    english = not bool(re.search(r'[\u0600-\u06ff]', question))
    with connect() as db:
        students=[dict(r) for r in db.execute('SELECT * FROM students ORDER BY student_code')]
        sections={r['section_code'] for r in students}
        sessions=[dict(r) for r in db.execute('SELECT * FROM sessions ORDER BY session_date DESC,id DESC')]
        # Exact code matching against existing database avoids accidental disclosure on ambiguous identifiers.
        matched=[r for r in students if re.search(r'(?<![\w])'+re.escape(r['student_code'].lower())+r'(?![\w])',s)]
        if len(matched)>1:return {'answer':('Please enter one student code.' if english else 'حددي كود طالب واحد فقط في السؤال.'),'kind':'clarification'}
        if not matched:
            matches=[r for r in students if r['student_name'] and re.search(r'(?<![\w])'+re.escape(r['student_name'].lower())+r'(?![\w])',s)]
            if len(matches)==1:matched=matches
            if len(matches)>1:return {'answer':('More than one student has this name. Use the student code.' if english else 'الاسم موجود لأكثر من طالب. استخدمي كود الطالب لتحديده.'),'kind':'clarification'}
        if matched:
            student=matched[0]
            code=student['student_code'];sec=student['section_code']
            rows=[dict(r) for r in db.execute('''SELECT s.session_date,s.topic,a.status FROM sessions s LEFT JOIN attendance a ON a.session_id=s.id AND a.student_code=? WHERE s.section_code=? ORDER BY s.session_date DESC''',(code,sec))]
            present=sum(r['status']=='present' for r in rows)
            absent=sum(r['status']=='absent' for r in rows)
            excused=sum(r['status']=='excused' for r in rows)
            unknown=sum(r['status'] is None for r in rows)
            if any(x in s for x in ('كام مرة','كم مرة','عدد الغياب','عدد مرات','غياباته','غيابها','غيابه','how many','absence count','كم غاب')):
                return {'answer':(f'{code} in {sec}: {absent} recorded absence(s), {present} present, {excused} excused, and {unknown} session(s) without a mark. No mark does not mean absent.' if english else f'الطالب {code} — سكشن {sec}: غاب {absent} مرة مسجلة، حضر {present}، بعذر {excused}، ولسه {unknown} جلسات من غير تسجيل. عدم تسجيل الحالة لا يعني غياب.'),'kind':'student_summary','student_code':code}
            m=re.search(r'\b20\d\d-\d\d-\d\d\b',s)
            selected=next((r for r in rows if r['session_date']==m.group()),None) if m else (rows[0] if rows else None)
            if not selected:
                return {'answer':(f'No session is saved for {code} on that date in {sec}. This is not counted as an absence.' if english else f'مفيش جلسة مسجلة للطالب {code} في التاريخ المطلوب أو السكشن {sec} لسه مفيهوش جلسات. مش هعتبره غايب.'),'kind':'no_record'}
            labels={'present':'حضر','absent':'غاب','excused':'غياب بعذر',None:'لم يتم تسجيل الحضور بعد'}
            return {'answer':(f"{code} in {sec} on {selected['session_date']}: " + {'present':'Present','absent':'Absent','excused':'Excused',None:'Not recorded'}[selected['status']] + (f'. Total: {present} present, {absent} absent.' if not m else '.') if english else f"الطالب {code} — سكشن {sec} — {selected['session_date']}: {labels[selected['status']]}." + (f' الإجمالي: {present} حضور، {absent} غياب.' if not m else '')),'kind':'student_status','student_code':code,'session_date':selected['session_date'],'status':selected['status']}
        # Section aggregate only when explicitly named, otherwise require code/section.
        mentioned=[sec for sec in sections if re.search(r'(?<![\w])'+re.escape(sec.lower())+r'(?![\w])',s)]
        if len(mentioned)==1:
            sec=mentioned[0]
            m=re.search(r'\b20\d\d-\d\d-\d\d\b',s)
            session=next((r for r in sessions if r['section_code']==sec and (not m or r['session_date']==m.group())),None)
            if not session:return {'answer':(f'No session is saved for {sec} on that date.' if english else f'لا توجد جلسة مسجلة للسكشن {sec} في التاريخ المطلوب.'),'kind':'no_record'}
            rows=[dict(r) for r in db.execute('''SELECT s.student_code,a.status FROM students s LEFT JOIN attendance a ON a.student_code=s.student_code AND a.session_id=? WHERE s.section_code=?''',(session['id'],sec))]
            counts={key:sum(r['status']==key for r in rows) for key in ('present','absent','excused')}
            unknown=sum(r['status'] is None for r in rows)
            if any(t in s for t in ('مين غاب','مين غايب','who was absent','who is absent','list absentees','which students were absent')):
                missing=[r['student_code'] for r in rows if r['status']=='absent']
                return {'answer':(f"Recorded absences in {sec} on {session['session_date']}: "+(', '.join(missing) if missing else 'None')+f'. Not recorded: {unknown}.' if english else f"الغياب المسجّل في {sec} يوم {session['session_date']}: "+(', '.join(missing) if missing else 'لا يوجد غياب مسجل')+f'. غير مسجّلين: {unknown}.'),'kind':'section_absent'}
            return {'answer':(f"{sec} on {session['session_date']}: {counts['present']} present, {counts['absent']} absent, {counts['excused']} excused, {unknown} not recorded. Unmarked students are not counted absent." if english else f"السكشن {sec} بتاريخ {session['session_date']}: حضر {counts['present']}، غاب {counts['absent']}، بعذر {counts['excused']}، لم يُسجل {unknown}. غير المسجلين مش محسوبين غياب."),'kind':'section_summary'}
    return {'answer':('Enter a student code (like ST001) or section code (like SEC-A). You can add a date as YYYY-MM-DD. Save attendance first.' if english else 'اكتبي كود الطالب (مثلاً ST001) أو كود السكشن (مثلاً SEC-A)، وممكن تضيفي تاريخًا بصيغة YYYY-MM-DD. لازم نسجل جلسة وحالات الحضور الأول.'),'kind':'clarification'}
