"""Grounded local chatbot. Retrieval works offline; optional local Ollama is opt-in.
No private OCR student records, grades or answer keys are added to the KB.
"""
from __future__ import annotations
from collections import Counter
import math, re, json, os
from urllib.request import Request, urlopen
from urllib.error import URLError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from attendance_chat import attendance_intent, ask_attendance

router = APIRouter(prefix='/api/v1/chatbot', tags=['Chatbot (local pilot)'])

KB = [
 {'id':'ocr_workflow','category':'workflow','title':'How to read handwriting',
  'keywords':'رفع صورة upload handwritten OCR photo scan segmentation سطور picture image',
  'answer':'Upload one answer photo, check the line cuts, then run TrOCR. Check the text against the photo before grading. OCR text can be wrong.'},
 {'id':'ocr_quality','category':'workflow','title':'Improve OCR reading',
  'keywords':'دقة تحسين اخطاء improve accuracy ocr handwriting poor wrong mistakes blurry noise quality hallucination',
  'answer':'Use a sharp, bright photo. Keep one answer in each image. Do not cut letters when marking text lines. Compare image modes, then check the words yourself.'},
 {'id':'metrics','category':'workflow','title':'What are CER and WER?',
  'keywords':'CER WER accuracy metric character word error rate دقة معدل اخطاء حروف كلمات',
  'answer':'CER measures character errors. WER measures word errors. Lower is better. These are error rates, not accuracy scores.'},
 {'id':'baseline','category':'workflow','title':'Our OCR test results',
  'keywords':'E01 E02 E03 E04 E05 baseline V2 result result latest phase segmentation تجارب مقارنة نتائج',
  'answer':'On seven new answers, E01 had CER 25.60% and WER 57.69%. Manual line-cut V2 had CER 15.58% and WER 50.09% on the same answers. These small tests do not prove performance on new students.'},
 {'id':'manual_grade','category':'workflow','title':'How are grades approved?',
  'keywords':'grade grading score essay ta review rubric اعتماد درجة معيدة مراجعة تصحيح مقالي',
  'answer':'The OCR text must be checked before grading. Clear multiple-choice, listed short, and verified math answers can get draft scores. Essays and unclear answers need staff review.'},
 {'id':'mcq','category':'workflow','title':'Multiple-choice answers',
  'keywords':'MCQ multiple choice حرف اختيارات اختيار من متعدد',
  'answer':'Use a clear answer like A, B, C, or D. Unclear answers need review. If the answer came from a photo, first check the OCR text. I cannot show private answer keys.'},
 {'id':'short_math','category':'workflow','title':'Short and math answers',
  'keywords':'short answer 1 3 word math sympy equation equivalence رياضيات معادلة اجابات قصيرة',
  'answer':'Short answers are one to three words and use an approved answer list. Math checks use SymPy rules. Unclear cases go to staff review.'},
 {'id':'project_phases','category':'workflow','title':'Project progress',
  'keywords':'phases roadmap next tasks progress project current phase phases next مرحلة الخطوة الجاية',
  'answer':'Phase 1: research and setup. Phase 2: dataset and text review (in progress). Phase 3: grading prototypes. Phase 4: OCR tests and line segmentation. Phases 5–6: local integration prototypes. Phase 7: chatbot and final testing are not complete.'},
 {'id':'signal_types','category':'course','title':'Continuous and discrete signals',
  'keywords':'continuous discrete signal time domain متصل متقطع اشارات زمن',
  'answer':'A continuous-time signal x(t) has a value at each time point. A discrete-time signal x[n] is defined at separate time points. This is about when values are defined.'},
 {'id':'sine_square','category':'course','title':'Sine wave and square wave',
  'keywords':'sine square wave analog digital smooth sharp موجة جيبية مربعة',
  'answer':'A sine wave has a smooth repeating shape. A square wave switches between two levels. Square waves are often used in digital circuits and clock signals.'},
 {'id':'parameters','category':'course','title':'Wave terms',
  'keywords':'amplitude frequency period phase hz t 1/f f 1/t سعة تردد زمن دوري طور',
  'answer':'Amplitude is signal size. Frequency is cycles each second (Hz). Period is the time for one cycle. Phase shows a time shift. T = 1/f for positive frequency.'},
 {'id':'bandwidth','category':'course','title':'Bandwidth',
  'keywords':'bandwidth spectrum frequencies frequency range bandwidth hz نطاق ترددي',
  'answer':'Bandwidth is the difference between the highest and lowest frequencies in a chosen range. For example, 3400 Hz minus 300 Hz is 3100 Hz.'},
]

STOP=set('how what when where why the a an i me my to is are do does can you please tell explain about and of for from in it on this that من في عن هو هي ايه ازاي ازاى يعني عايزه عايزة عايز ممكن اشرحلي شرحلي لو سمحت و على الى ال'.split())
ALIASES={
 'قراءة':'ocr','يقرأ':'ocr','قراءه':'ocr','الخط':'handwriting','الكتابه':'handwriting','الكتابة':'handwriting','صورة':'image','الصوره':'image','الصور':'image',
 'تصحيح':'grading','الدرجات':'grade','درجات':'grade','المعيده':'ta','المعيدة':'ta','المراجعه':'review',
 'اغلاط':'mistakes','اخطاء':'mistakes','غلط':'wrong','تحسين':'improve','التحسين':'improve',
 'مستمره':'continuous','مستمر':'continuous','متصله':'continuous','متصلة':'continuous',
 'متقطع':'discrete','متقطعة':'discrete','جيبيه':'sine','جيبية':'sine','مربعه':'square','مربعة':'square',
 'التردد':'frequency','الطور':'phase','الترددات':'frequency','المعادلات':'math',
 'مراحل':'phases','مرحلة':'phases','خطة':'roadmap','الخطوه':'next','الخطوة':'next',
}

def tokens(text):
    s=text.lower().replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ة','ه')
    pieces=re.findall(r'[\w\u0600-\u06ff]+',s,flags=re.UNICODE)
    return [ALIASES.get(p,p) for p in pieces if len(p)>1 and p not in STOP]

# Separately indexed corpus avoids exposing answer keys/personal records.
INDEX={r['id']:set(tokens(r['title']+' '+r['keywords']+' '+r['answer'])) for r in KB}


def find_docs(query, section='all', top_n=2):
    qt=set(tokens(query))
    if not qt:return []
    scores=[]
    for r in KB:
        if section not in ('all',r['category']):continue
        kw=set(tokens(r['title']+' '+r['keywords']))
        overlap=qt & INDEX[r['id']]
        overlap_kw=qt & kw
        score=(2.5*len(overlap_kw)+len(overlap))/math.sqrt(max(1,len(qt)))
        if score >= 2.0: scores.append((score,r))
    return [r for _,r in sorted(scores,key=lambda a:-a[0])[:top_n]]


class ChatRequest(BaseModel):
    message:str=Field(min_length=2,max_length=1600)
    section:str=Field(default='all',pattern='^(all|workflow|course)$')
    engine:str=Field(default='knowledge',pattern='^(knowledge|ollama)$')


def ollama_answer(message, docs):
    model=os.environ.get('MENTRIX_OLLAMA_MODEL','llama3.2:3b')
    context='\n\n'.join(f"{r['title']}: {r['answer']}" for r in docs)
    system=('You are the local MENTRIX teaching assistant. Use only these sources. '
            'If a fact is missing, say so. Never invent grades or share student records or answer keys. '
            'Only staff can approve grades. Use simple English.\n'+context)
    payload=json.dumps({'model':model, 'messages':[{'role':'system','content':system},
                 {'role':'user','content':message}], 'stream':False, 'options':{'temperature':0.1}},ensure_ascii=False).encode()
    req=Request('http://127.0.0.1:11434/api/chat',data=payload,headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=45) as resp:
        data=json.loads(resp.read(2_000_000))
    answer=data.get('message',{}).get('content','').strip()
    if not answer: raise RuntimeError('Ollama returned an empty response')
    return answer

@router.get('/config')
def config():
    return {'offline_default':True,'engines':['knowledge','ollama'],
            'ollama_model':os.environ.get('MENTRIX_OLLAMA_MODEL','llama3.2:3b'),
            'scope':'staff-only local attendance database queries + course concepts; no LLM access to records'}

@router.post('/ask')
def ask(body:ChatRequest):
    if attendance_intent(body.message):
        result=ask_attendance(body.message)
        return {'answer':result['answer'],'sources':[{'id':'sqlite_attendance','title':'Saved attendance records','category':'records'}], 'engine':'database','grounded':True,'record_kind':result['kind']}
    docs=find_docs(body.message,body.section)
    sources=[{'id':r['id'],'title':r['title'],'category':r['category']} for r in docs]
    if not docs:
        return {'answer':'I do not have a saved answer for that. Ask about attendance, OCR, grading, or course topics.','sources':[], 'engine':'knowledge','grounded':False}
    if body.engine=='ollama':
        try: answer=ollama_answer(body.message,docs)
        except (URLError, OSError, RuntimeError, ValueError, TimeoutError) as e:
            raise HTTPException(503,'Local Ollama is not ready. Choose Offline knowledge instead. '+str(e)[:150]) from e
        return {'answer':answer,'sources':sources,'engine':'ollama','grounded':True,
                'warning':'LLM-generated text may contain errors; verify against cited local sources.'}
    return {'answer':'\n\n'.join(r['answer'] for r in docs),'sources':sources,'engine':'knowledge','grounded':True}
