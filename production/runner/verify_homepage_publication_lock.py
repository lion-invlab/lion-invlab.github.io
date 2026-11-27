#!/usr/bin/env python3
"""Fail-closed guard for the official TAC homepage; preview deployment remains unaffected when index.html is unchanged."""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LOCK_PATH=ROOT/'production/config/homepage-publication-lock.json'
INDEX_PATH='index.html'

def git_text(*args:str)->str:
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def validate_homepage_lock(lock:dict,actual_index_blob:str,preview_blob:str|None,lock_commit_message:str,require_approved:bool=False)->dict:
    if lock.get('schema_version')!='1.0':
        raise ValueError('homepage publication lock schema_version must be 1.0')
    if lock.get('index_git_blob_sha')!=actual_index_blob:
        raise ValueError('index.html Git blob SHA differs from the locked homepage baseline/approval')
    status=lock.get('status')
    if require_approved and status!='APPROVED_PUBLICATION':
        raise ValueError('archive requires an explicitly approved homepage publication')
    if status=='BASELINE_LOCKED':
        if lock.get('approved_by_owner') is not False:
            raise ValueError('baseline homepage lock must not imply publication approval')
        if any(lock.get(k) is not None for k in ('report_date','preview_path','preview_git_blob_sha','approved_at','approval_note')):
            raise ValueError('baseline lock must not contain a publication approval record')
        return {'status':'PASS','mode':'BASELINE_LOCKED','index_git_blob_sha':actual_index_blob}
    if status=='APPROVED_PUBLICATION':
        report_date=str(lock.get('report_date') or '')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',report_date):
            raise ValueError('approved publication requires an exact report_date')
        expected_path=f'preview/{report_date}-review.html'
        if lock.get('preview_path')!=expected_path:
            raise ValueError('approved publication preview_path does not match report_date')
        if not lock.get('approved_by_owner') is True:
            raise ValueError('homepage publication requires explicit approved_by_owner=true')
        if not lock.get('approved_at') or not lock.get('approval_note'):
            raise ValueError('approved publication requires approved_at and approval_note')
        if lock_commit_message.find(f'[publish-tac-report:{report_date}]')<0:
            raise ValueError('homepage lock approval commit lacks the exact publish marker')
        if not preview_blob or lock.get('preview_git_blob_sha')!=preview_blob:
            raise ValueError('approved preview Git blob SHA does not match the current review artifact')
        if actual_index_blob!=preview_blob:
            raise ValueError('official index.html must be byte-identical to the explicitly approved preview')
        return {'status':'PASS','mode':'APPROVED_PUBLICATION','report_date':report_date,'index_git_blob_sha':actual_index_blob,'preview_git_blob_sha':preview_blob}
    raise ValueError(f'unsupported homepage publication lock status: {status!r}')

def main()->None:
    if not LOCK_PATH.is_file():
        raise SystemExit('homepage publication lock is missing; Pages deployment is blocked')
    lock=json.loads(LOCK_PATH.read_text(encoding='utf-8'))
    actual=git_text('rev-parse',f'HEAD:{INDEX_PATH}')
    preview_blob=None
    if lock.get('status')=='APPROVED_PUBLICATION':
        preview_blob=git_text('rev-parse',f"HEAD:{lock.get('preview_path')}")
    lock_message=git_text('log','-1','--format=%s','--','production/config/homepage-publication-lock.json')
    result=validate_homepage_lock(lock,actual,preview_blob,lock_message,require_approved='--require-approved' in __import__('sys').argv)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    main()
