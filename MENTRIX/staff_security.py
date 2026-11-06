"""Local single-TA session gate. NOT production-grade identity management."""
from __future__ import annotations
import os, secrets, time, hmac
from fastapi import APIRouter, Request, HTTPException, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api/auth',tags=['Staff access'])
SESSIONS = {}
FAILED = {}
COOKIE='mentrix_local_staff'
SESSION_SECS=8*60*60

class Login(BaseModel):
    pin:str=Field(min_length=6,max_length=128)

def valid(request:Request):
    token=request.cookies.get(COOKIE,'')
    entry=SESSIONS.get(token)
    if not token or not entry or entry[0]<time.time():return False
    return True

def role(request:Request):
    token=request.cookies.get(COOKIE,'')
    return SESSIONS[token][1] if valid(request) else None

@router.get('/session')
def session(request:Request):
    pin=os.getenv('MENTRIX_STAFF_PIN','')
    return {'authenticated':valid(request),'configured':len(pin)>=6,'role':role(request)}

@router.post('/login')
def login(body:Login,request:Request,response:Response):
    pin=os.getenv('MENTRIX_STAFF_PIN','')
    if len(pin)<6:raise HTTPException(503,'Set MENTRIX_STAFF_PIN (6+ characters) in the server launcher.')
    # Only loopback is supported; prevents browsers from other hosts reaching local sensitive data.
    client=request.client.host if request.client else ''
    if client not in ('127.0.0.1','::1','testclient'):
        raise HTTPException(403,'Local access only')
    now=time.time(); recent=[t for t in FAILED.get(client,[]) if now-t<60]
    if len(recent)>=7:raise HTTPException(429,'Too many attempts. Try again later.')
    admin_pin=os.getenv('MENTRIX_ADMIN_PIN','')
    is_admin=len(admin_pin)>=6 and hmac.compare_digest(body.pin,admin_pin)
    is_ta=hmac.compare_digest(body.pin,pin)
    if not (is_ta or is_admin):
        FAILED[client]=recent+[now]
        raise HTTPException(401,'Incorrect staff PIN')
    FAILED.pop(client,None)
    token=secrets.token_urlsafe(32)
    SESSIONS[token]=(now+SESSION_SECS,'admin' if is_admin else 'ta')
    response.set_cookie(COOKIE,token,httponly=True,samesite='strict',secure=False,max_age=SESSION_SECS,path='/')
    return {'authenticated':True,'role':'admin' if is_admin else 'ta'}

@router.post('/logout')
def logout(request:Request,response:Response):
    SESSIONS.pop(request.cookies.get(COOKIE,''),None)
    response.delete_cookie(COOKIE,path='/')
    return {'authenticated':False}
