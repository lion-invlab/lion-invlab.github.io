#!/usr/bin/env python3
"""Idempotent FRED/ALFRED incremental updater for the TAC Chart 3 baseline store."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,io,json,os,re,shutil,time,urllib.parse,urllib.request
from pathlib import Path
from datetime import datetime,timezone

BASE='https://api.stlouisfed.org/fred'
SERIES_START={'VIXCLS':'1990-01-01','NFCI':'1971-01-01','NFCICREDIT':'1971-01-01','STLFSI4':'1993-12-01'}
EVENT_FIELDS=['series_id','observation_date','vintage_date','value','value_status','release_date','release_date_status','source_method','source_chunk','artifact_created_at','license_status']
CURRENT_FIELDS=['series_id','observation_date','value','realtime_start','realtime_end','retrieved_at','source_method','license_status','quality_flags']
INITIAL_FIELDS=['series_id','observation_date','value','realtime_start','realtime_end','release_date','release_date_status','retrieved_at','source_method','license_status']

def sha_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def request_json(endpoint,params,key,retries=5):
 url=BASE+'/'+endpoint+'?'+urllib.parse.urlencode(dict(params,api_key=key,file_type='json'))
 last=None
 for i in range(retries):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'TAC-Decision-Charts/1.0'})
   with urllib.request.urlopen(req,timeout=120) as r:data=json.loads(r.read().decode('utf-8'))
   if 'error_code' in data:raise RuntimeError(str(data))
   return data
  except Exception as e:
   last=e
   if i+1<retries:time.sleep(min(3*(2**i),30))
 raise RuntimeError(f'{endpoint} failed: {last}')

def get_vintage_dates(sid,key):
 out=[];offset=0
 while True:
  p=request_json('series/vintagedates',{'series_id':sid,'sort_order':'asc','limit':10000,'offset':offset},key)
  batch=p.get('vintage_dates',[]);out.extend(batch)
  if len(batch)<10000:break
  offset+=len(batch)
 if not out:raise RuntimeError(f'{sid}: empty vintage-date index')
 if out!=sorted(set(out)):raise RuntimeError(f'{sid}: vintage dates not unique and ascending')
 return out

def choose_vintages(all_dates,last_vintage,overlap=5):
 if last_vintage not in all_dates:raise RuntimeError(f'Checkpoint vintage {last_vintage} no longer exists in ALFRED index')
 idx=all_dates.index(last_vintage)
 return all_dates[max(0,idx-overlap+1):]

def parse_event_matrix(sid,payload,retrieved,chunk_name):
 rows={};prefix=sid+'_'
 for row in payload.get('observations',[]):
  obs=row.get('date')
  if not obs:continue
  for col,val in row.items():
   if not col.startswith(prefix) or val in ('',None):continue
   suffix=col[len(prefix):]
   if not re.fullmatch(r'\d{8}',suffix):continue
   vintage=f'{suffix[:4]}-{suffix[4:6]}-{suffix[6:8]}'
   item={'series_id':sid,'observation_date':obs,'vintage_date':vintage,'value':val,'value_status':'source_missing_value' if val=='.' else 'source_value','release_date':'','release_date_status':'exact_release_date_not_supplied_by_observations_endpoint','source_method':'FRED API output_type=3 (new_and_revised_only)','source_chunk':chunk_name,'artifact_created_at':retrieved,'license_status':'review_required_before_redistribution'}
   k=(obs,vintage)
   if k in rows and rows[k]['value']!=val:raise RuntimeError(f'{sid}: conflicting duplicate event {k}')
   rows[k]=item
 return sorted(rows.values(),key=lambda x:(x['observation_date'],x['vintage_date']))

def merge_event_gzip(old_path,new_rows,out_path):
 """Streaming merge; duplicate keys must have identical values; preserves sorted event order."""
 new_rows=sorted(new_rows,key=lambda x:(x['observation_date'],x['vintage_date']))
 out_path.parent.mkdir(parents=True,exist_ok=True)
 with open(old_path,'rb') as old_raw,open(out_path,'wb') as out_raw:
  with gzip.GzipFile(fileobj=old_raw,mode='rb') as old_gz,io.TextIOWrapper(old_gz,encoding='utf-8-sig',newline='') as old_text:
   reader=csv.DictReader(old_text);old=next(reader,None);i=0;added=0;duplicate=0
   with gzip.GzipFile(filename='',fileobj=out_raw,mode='wb',compresslevel=6,mtime=0) as out_gz,io.TextIOWrapper(out_gz,encoding='utf-8-sig',newline='') as out_text:
    writer=csv.DictWriter(out_text,fieldnames=EVENT_FIELDS);writer.writeheader()
    while old is not None or i<len(new_rows):
     new=new_rows[i] if i<len(new_rows) else None
     ok=(old['observation_date'],old['vintage_date']) if old else None
     nk=(new['observation_date'],new['vintage_date']) if new else None
     if old is not None and (new is None or ok<nk):writer.writerow(old);old=next(reader,None)
     elif new is not None and (old is None or nk<ok):writer.writerow(new);i+=1;added+=1
     else:
      if old['value']!=new['value']:raise RuntimeError(f'Conflicting event for {nk}: {old["value"]} vs {new["value"]}')
      writer.writerow(old);old=next(reader,None);i+=1;duplicate+=1
 return {'added':added,'overlap_duplicates':duplicate}

def write_gzip_csv(path,fields,rows):
 with open(path,'wb') as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',compresslevel=6,mtime=0) as gz:
   with io.TextIOWrapper(gz,encoding='utf-8-sig',newline='') as text:
    w=csv.DictWriter(text,fieldnames=fields);w.writeheader();w.writerows(rows)
 return sha_file(path)

def gzip_csv_same_values(path_a,path_b,fields,ignore_fields=()):
 def rows(p):
  with gzip.open(p,'rt',encoding='utf-8-sig',newline='') as f:
   for r in csv.DictReader(f):yield tuple(r.get(k,'') for k in fields if k not in ignore_fields)
 sentinel=object();ia,ib=iter(rows(path_a)),iter(rows(path_b))
 while True:
  a=next(ia,sentinel);b=next(ib,sentinel)
  if a is sentinel or b is sentinel:return a is sentinel and b is sentinel
  if a!=b:return False

def replace_if_hash_changed(tmp_path,final_path):
 new_hash=sha_file(tmp_path)
 if final_path.exists() and sha_file(final_path)==new_hash:
  tmp_path.unlink();return False,new_hash
 os.replace(tmp_path,final_path);return True,new_hash

def fetch_current(sid,key,latest_vintage):
 rows=[];now=datetime.now(timezone.utc).date();y0=int(SERIES_START[sid][:4]);windows=[]
 while y0<=now.year:
  y1=min(y0+9,now.year);windows.append((f'{y0}-01-01',f'{y1}-12-31'));y0=y1+1
 for lo,hi in windows:
  p=request_json('series/observations',{'series_id':sid,'observation_start':max(SERIES_START[sid],lo),'observation_end':hi,'realtime_start':latest_vintage,'realtime_end':latest_vintage,'output_type':1,'sort_order':'asc','limit':100000,'offset':0},key)
  rows.extend(p.get('observations',[]))
 return rows

def fetch_new_events(sid,key,vintages):
 rows=[];now=datetime.now(timezone.utc).date();y0=int(SERIES_START[sid][:4]);windows=[]
 while y0<=now.year:
  y1=min(y0+9,now.year);windows.append((f'{y0}-01-01',f'{y1}-12-31'));y0=y1+1
 for batch_no in range(0,len(vintages),50):
  batch=vintages[batch_no:batch_no+50]
  for lo,hi in windows:
   p=request_json('series/observations',{'series_id':sid,'observation_start':max(SERIES_START[sid],lo),'observation_end':hi,'output_type':3,'vintage_dates':','.join(batch),'sort_order':'asc','limit':100000,'offset':0},key,retries=2)
   rows.extend(parse_event_matrix(sid,p,datetime.now(timezone.utc).isoformat(timespec='seconds'),f'{sid}_incremental_v{batch_no//50+1:03d}_{lo[:4]}_{hi[:4]}.json'))
 return rows

def fetch_initial_release(sid,key,retrieved):
 rows=[];now=datetime.now(timezone.utc).date();y0=int(SERIES_START[sid][:4])
 while y0<=now.year:
  y1=min(y0+9,now.year)
  p=request_json('series/observations',{'series_id':sid,'observation_start':max(SERIES_START[sid],f'{y0}-01-01'),'observation_end':f'{y1}-12-31','output_type':4,'sort_order':'asc','limit':100000,'offset':0},key)
  for r in p.get('observations',[]):
   rows.append({'series_id':sid,'observation_date':r['date'],'value':r['value'],'realtime_start':r.get('realtime_start',''),'realtime_end':r.get('realtime_end',''),'release_date':'','release_date_status':'exact_release_date_not_supplied_by_observations_endpoint','retrieved_at':retrieved,'source_method':'FRED API output_type=4 initial release only','license_status':'review_required_before_redistribution'})
  y0=y1+1
 return rows

def merge_initial_release(old_path,new_rows,out_path):
 existing={}
 with gzip.open(old_path,'rt',encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):existing[r['observation_date']]=r
 added=0
 for r in new_rows:
  d=r['observation_date']
  if d in existing:
   if existing[d]['value']!=r['value']:
    raise RuntimeError(f'Initial-release conflict for {d}: baseline={existing[d]["value"]}, API={r["value"]}; manual review required')
  else:existing[d]=r;added+=1
 if added:
  rows=[existing[k] for k in sorted(existing)]
  write_gzip_csv(out_path,INITIAL_FIELDS,rows)
  return added,sha_file(out_path),len(rows)
 return 0,sha_file(old_path),len(existing)

def reconcile(current_rows,event_path):
 current={r['date']:r['value'] for r in current_rows};needed=set(current);latest={}
 with gzip.open(event_path,'rt',encoding='utf-8-sig',newline='') as f:
  for e in csv.DictReader(f):
   d=e['observation_date']
   if d in needed:latest[d]=(e['vintage_date'],e['value'])
 missing=sorted(needed-set(latest));mismatches=[(d,current[d],latest[d][1]) for d in needed&set(latest) if current[d]!=latest[d][1]]
 if missing or mismatches:raise RuntimeError(f'Current reconciliation failed: no_history={len(missing)}, mismatches={len(mismatches)}; examples={missing[:3]} {mismatches[:3]}')
 return len(current),len(mismatches)

def update_series(sid,root,key,retrieved,overlap=5):
 sd=root/'series'/sid;state=json.loads((sd/'state.json').read_text());dates=get_vintage_dates(sid,key);last=state['last_vintage_date']
 if last not in dates:raise RuntimeError(f'{sid}: checkpoint vintage not present in current ALFRED index')
 new_dates=[d for d in dates if d>last];selected=list(dict.fromkeys(choose_vintages(dates,last,overlap)+new_dates))
 new_events=fetch_new_events(sid,key,selected) if selected else []
 event_tmp=sd/'vintage_events.next.csv.gz';merge_stats=merge_event_gzip(sd/'vintage_events.csv.gz',new_events,event_tmp)
 event_changed,event_sha=replace_if_hash_changed(event_tmp,sd/'vintage_events.csv.gz')
 current=fetch_current(sid,key,dates[-1]);current_rows=[]
 for r in current:
  flags=['source_missing_value'] if r.get('value')=='.' else []
  current_rows.append({'series_id':sid,'observation_date':r['date'],'value':r['value'],'realtime_start':r.get('realtime_start',''),'realtime_end':r.get('realtime_end',''),'retrieved_at':retrieved,'source_method':'FRED API output_type=1 current snapshot','license_status':'review_required_before_redistribution','quality_flags':';'.join(flags)})
 current_tmp=sd/'current.next.csv.gz';write_gzip_csv(current_tmp,CURRENT_FIELDS,current_rows)
 current_same=gzip_csv_same_values(sd/'current.csv.gz',current_tmp,CURRENT_FIELDS,ignore_fields=('retrieved_at',))
 if current_same:
  current_tmp.unlink();current_sha=sha_file(sd/'current.csv.gz');current_changed=False
 else:current_changed,current_sha=replace_if_hash_changed(current_tmp,sd/'current.csv.gz')
 checked,_=reconcile(current,sd/'vintage_events.csv.gz')
 initial_rows=fetch_initial_release(sid,key,retrieved)
 initial_tmp=sd/'initial_release.next.csv.gz'
 initial_added,initial_sha,initial_count=merge_initial_release(sd/'initial_release.csv.gz',initial_rows,initial_tmp)
 initial_changed=False
 if initial_added:
  initial_changed,initial_sha=replace_if_hash_changed(initial_tmp,sd/'initial_release.csv.gz')
 elif initial_tmp.exists():initial_tmp.unlink()
 dates_obj={'series_id':sid,'vintage_dates':dates,'count':len(dates),'source_endpoint':'FRED series/vintagedates'}
 dates_tmp=sd/'vintage_dates.next.json';dates_tmp.write_text(json.dumps(dates_obj,ensure_ascii=False,indent=2))
 dates_changed,dates_sha=replace_if_hash_changed(dates_tmp,sd/'vintage_dates.json')
 changed=event_changed or current_changed or dates_changed or bool(new_dates) or initial_changed
 if changed:
  state.update({'last_vintage_date':dates[-1],'vintage_date_count':len(dates),'vintage_dates_sha256':dates_sha,'event_count':sum(1 for _ in gzip.open(sd/'vintage_events.csv.gz','rt',encoding='utf-8-sig'))-1,'events_sha256':event_sha,'current_rows':checked,'current_sha256':current_sha,'last_success_at':retrieved,'new_vintage_dates':len(new_dates),'queried_vintage_dates':len(selected),'new_event_rows_fetched':len(new_events),'added_event_rows':merge_stats['added'],'overlap_duplicate_rows':merge_stats['overlap_duplicates'],'overlap_window':overlap,'initial_release_rows':initial_count,'initial_release_sha256':initial_sha,'initial_release_added_rows':initial_added})
  (sd/'state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2))
 return {'series_id':sid,'new_vintage_dates':len(new_dates),'queried_vintage_dates':len(selected),'new_event_rows_fetched':len(new_events),'added_event_rows':merge_stats['added'],'overlap_duplicate_rows':merge_stats['overlap_duplicates'],'current_rows':checked,'current_sha256':current_sha,'event_count':sum(1 for _ in gzip.open(sd/'vintage_events.csv.gz','rt',encoding='utf-8-sig'))-1,'events_sha256':event_sha,'initial_release_rows':initial_count,'initial_release_sha256':initial_sha,'initial_release_added_rows':initial_added,'vintage_date_count':len(dates),'vintage_dates_sha256':dates_sha,'latest_vintage_date':dates[-1],'changed':changed}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data-dir',default='data/tac-chart3');ap.add_argument('--overlap',type=int,default=5);args=ap.parse_args()
 key=os.environ.get('FRED_API_KEY','').strip()
 if len(key)!=32 or not key.isalnum() or key.lower()!=key:raise SystemExit('FRED_API_KEY missing or malformed')
 root=Path(args.data_dir)
 if not (root/'manifest.json').is_file():raise SystemExit('Baseline store missing: refusing incremental run')
 for sid in SERIES_START:
  if not (root/'series'/sid/'state.json').is_file():raise SystemExit(f'Baseline state missing for {sid}; refusing incremental run')
 stage=root.with_name(root.name+'.staging');backup=root.with_name(root.name+'.previous')
 if stage.exists():shutil.rmtree(stage)
 shutil.copytree(root,stage)
 retrieved=datetime.now(timezone.utc).isoformat(timespec='seconds');results=[]
 try:
  for sid in SERIES_START:results.append(update_series(sid,stage,key,retrieved,args.overlap))
  if any(x['changed'] for x in results):
   manifest=json.loads((stage/'manifest.json').read_text());manifest['last_incremental_at']=retrieved;manifest['last_incremental_results']=results;manifest['overall_status']='PASS'
   for item in manifest.get('series',[]):
    result=next((x for x in results if x['series_id']==item.get('series_id')),None)
    if result:
     item['current_rows']=result['current_rows'];item['current_sha256']=result.get('current_sha256',item.get('current_sha256'))
     item['event_rows']=result.get('event_count',item.get('event_rows'));item['event_sha256']=result.get('events_sha256',item.get('event_sha256'))
     item['initial_release_rows']=result['initial_release_rows'];item['initial_release_sha256']=result['initial_release_sha256']
     item['vintage_dates']=result.get('vintage_date_count',item.get('vintage_dates'))
     item['vintage_span']={'first':item.get('vintage_span',{}).get('first'),'last':result['latest_vintage_date']}
   (stage/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
  else:print('NO_DATA_CHANGE: preserving baseline files and checkpoint timestamps')
  if backup.exists():shutil.rmtree(backup)
  os.replace(root,backup)
  try:os.replace(stage,root)
  except Exception:
   if backup.exists() and not root.exists():os.replace(backup,root)
   raise
  if backup.exists():shutil.rmtree(backup)
 except Exception:
  if stage.exists():shutil.rmtree(stage)
  raise
 print(json.dumps({'status':'PASS','updated_at':retrieved,'results':results},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
