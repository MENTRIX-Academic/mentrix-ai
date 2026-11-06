"""Reproducible fictional 30-student attendance fixtures for backend integration.
No personal data, actual PIN, hashed credentials or real student grades. No website changes.
"""
from __future__ import annotations
import argparse,json,random
from collections import Counter
from pathlib import Path
from research.sprint5.audit_and_gate import ROOT
OUTPUT=ROOT/'research'/'sprint5'/'mock_data'

def build(out=OUTPUT,seed=42):
    r=random.Random(seed)
    students=[{'student_id':f'MX-DEMO-{n:03d}','display_name':f'Demo Student {n:02d}',
               'section_id':'AI-S01','synthetic':True,'login_enabled':False}
               for n in range(1,31)]
    sessions=[];attendance=[]
    courses=[{'course_id':'AI101','course_name':'Artificial Intelligence'},
             {'course_id':'ML201','course_name':'Machine Learning'}]
    for course in courses:
        for i in range(1,7):
            session_id=f'{course["course_id"]}-S{i:02d}'
            sessions.append({'session_id':session_id,'course_id':course['course_id'],
                             'section_id':'AI-S01','room':'Lab 3','session_number':i,
                             'status':'closed','qr_rotation_seconds':30,
                             'checkin_window_minutes':5,'synthetic':True})
            for student in students:
                checked=r.random()<0.80
                record={'session_id':session_id,'student_id':student['student_id'],
                        'attendance_status':'present' if checked else 'absent',
                        'source':'demo_rotating_qr' if checked else 'no_valid_checkin',
                        'random_check':'verified' if checked and r.random()<0.08 else 'not_selected',
                        'synthetic':True}
                attendance.append(record)
    result={'status':'SYNTHETIC_DEMO_DATA_ONLY','seed':seed,'students':students,'courses':courses,
            'sessions':sessions,'attendance':attendance,
            'notes':['No PINs: the backend must generate and hash credentials securely',
                     'These records are for UI and Chatbot/API testing, NOT for grading model training',
                     'The QR field describes a desired configuration; cryptographic session verification is NOT implemented']}
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'s05_mock_backend_data.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts=Counter(r['attendance_status'] for r in attendance)
    summary={'synthetic':True,'students':len(students),'courses':len(courses),
             'sessions':len(sessions),'attendance_rows':len(attendance),
             'present':counts['present'],'absent':counts['absent']}
    (out/'s05_mock_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=OUTPUT)
    a=p.parse_args();print('DEMO ONLY:',build(a.output))
