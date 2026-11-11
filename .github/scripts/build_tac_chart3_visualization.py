#!/usr/bin/env python3
"""Build a chart-ready, provenance-preserving TAC Chart 3 current dataset."""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

SERIES_META={
 "VIXCLS":{"label":"CBOE VIX","frequency":"daily","panel":"volatility","unit":"index points","note":"VIX methodology changed in 2003; treat the pre/post-2003 history as a structural-break-aware series."},
 "NFCI":{"label":"Chicago Fed National Financial Conditions Index","frequency":"weekly","panel":"financial_conditions","unit":"index points","note":"Positive values indicate tighter-than-average financial conditions; negative values indicate looser-than-average conditions."},
 "NFCICREDIT":{"label":"NFCI Credit Subindex","frequency":"weekly","panel":"financial_conditions","unit":"index points","note":"A component of NFCI, not an independent standalone credit index; do not double-count it as an independent measure."},
 "STLFSI4":{"label":"St. Louis Fed Financial Stress Index","frequency":"weekly","panel":"financial_conditions","unit":"index points","note":"Positive values indicate above-average financial stress; negative values indicate below-average financial stress."}
}
def sha_file(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read_csv_gz(path):
 with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def build(root):
 series=[];qa=[]
 for sid,meta in SERIES_META.items():
  sd=root/'series'/sid
  state=json.loads((sd/'state.json').read_text(encoding='utf-8'))
  checks={
   'current_sha256':sha_file(sd/'current.csv.gz')==state['current_sha256'],
   'events_sha256':sha_file(sd/'vintage_events.csv.gz')==state['events_sha256'],
   'initial_release_sha256':sha_file(sd/'initial_release.csv.gz')==state['initial_release_sha256'],
   'vintage_dates_sha256':sha_file(sd/'vintage_dates.json')==state['vintage_dates_sha256']
  }
  if not all(checks.values()):raise RuntimeError(f'{sid}: stored file hash does not match checkpoint: {checks}')
  dates=json.loads((sd/'vintage_dates.json').read_text(encoding='utf-8'))['vintage_dates']
  if not dates or dates[-1]!=state['last_vintage_date']:raise RuntimeError(f'{sid}: vintage index and checkpoint disagree')
  vintage_set=set(dates)
  event_count=0;previous_event=None
  with gzip.open(sd/'vintage_events.csv.gz','rt',encoding='utf-8-sig',newline='') as ef:
   for event in csv.DictReader(ef):
    key=(event['observation_date'],event['vintage_date'])
    if previous_event is not None and key<=previous_event:raise RuntimeError(f'{sid}: vintage events not strictly sorted at {key}')
    if event['vintage_date'] not in vintage_set:raise RuntimeError(f'{sid}: event references unknown vintage {event["vintage_date"]}')
    if event['value'] in ('',None):raise RuntimeError(f'{sid}: blank event value at {key}; blank cells must not become events')
    if event['value']=='.' and event.get('value_status')!='source_missing_value':raise RuntimeError(f'{sid}: dot event missing-value status mismatch at {key}')
    if event['value']!='.' and event.get('value_status')!='source_value':raise RuntimeError(f'{sid}: numeric event status mismatch at {key}')
    if event.get('release_date'):raise RuntimeError(f'{sid}: unsupported release_date was populated at {key}')
    previous_event=key;event_count+=1
  if event_count!=state.get('event_count'):raise RuntimeError(f'{sid}: event row count mismatch: {event_count} vs {state.get("event_count")}')
  initial_count=0;initial_seen=set();previous_initial=None
  with gzip.open(sd/'initial_release.csv.gz','rt',encoding='utf-8-sig',newline='') as inf:
   for initial in csv.DictReader(inf):
    d=initial['observation_date']
    if d in initial_seen:raise RuntimeError(f'{sid}: duplicate initial-release observation {d}')
    if previous_initial is not None and d<=previous_initial:raise RuntimeError(f'{sid}: initial-release rows not strictly sorted at {d}')
    if initial.get('release_date'):raise RuntimeError(f'{sid}: unsupported initial release_date populated at {d}')
    initial_seen.add(d);previous_initial=d;initial_count+=1
  if initial_count!=state.get('initial_release_rows'):raise RuntimeError(f'{sid}: initial-release row count mismatch: {initial_count} vs {state.get("initial_release_rows")}')
  rows=read_csv_gz(sd/'current.csv.gz')
  if len(rows)!=state['current_rows']:raise RuntimeError(f'{sid}: current row count mismatch')
  observations=[];seen=set();valid=[];missing=0
  for row in rows:
   d=row['observation_date']
   if d in seen:raise RuntimeError(f'{sid}: duplicate current observation date {d}')
   seen.add(d)
   if observations and d<=observations[-1]['date']:raise RuntimeError(f'{sid}: current observations not strictly ascending')
   raw=row['value']
   if raw in ('','.'):
    value=None;status='source_missing_value';missing+=1
   else:
    try:value=float(raw)
    except ValueError:raise RuntimeError(f'{sid}: non-numeric source value {raw!r} on {d}')
    status='source_value';valid.append((d,value))
   observations.append({'date':d,'value':value,'value_raw':raw,'value_status':status})
  if len(rows)!=len(observations):raise RuntimeError(f'{sid}: observation count mismatch')
  if not valid:raise RuntimeError(f'{sid}: no valid numeric observations')
  series.append({
   'series_id':sid,'label':meta['label'],'frequency':meta['frequency'],'panel':meta['panel'],'unit':meta['unit'],
   'as_of_vintage':state['last_vintage_date'],'vintage_coverage':{'first':dates[0],'last':dates[-1],'count':len(dates)},
   'observation_span':{'first':observations[0]['date'],'last':observations[-1]['date']},
   'valid_observations':len(valid),'missing_observations':missing,'vintage_event_rows':event_count,'initial_release_rows':initial_count,'latest_valid_observation':{'date':valid[-1][0],'value':valid[-1][1]},
   'source':'Federal Reserve Bank of St. Louis FRED/ALFRED','source_series_id':sid,
   'source_file_sha256':state['current_sha256'],'vintage_events_sha256':state['events_sha256'],
   'initial_release_sha256':state['initial_release_sha256'],'retrieved_at':state['last_success_at'],
   'license_status':'review_required_before_redistribution','note':meta['note'],'observations':observations
  })
  qa.append({'series_id':sid,'status':'PASS','current_rows':len(rows),'valid_rows':len(valid),'missing_rows':missing,'vintage_event_rows':event_count,'initial_release_rows':initial_count,'current_sha256':state['current_sha256'],'vintage_events_sha256':state['events_sha256'],'initial_release_sha256':state['initial_release_sha256'],'vintage_coverage':{'first':dates[0],'last':dates[-1],'count':len(dates)},'hash_checks':checks})
 generated=max(x['retrieved_at'] for x in series)
 obj={'schema_version':'1.0','dataset_id':'TAC_CHART3_MARKET_STRESS','generated_at':generated,
  'method':{'current_snapshot':'FRED observations output_type=1','vintage_history':'ALFRED observations output_type=3 new/revised events only','initial_release':'FRED observations output_type=4','date_alignment':'native observation dates; no resampling or interpolation','missing_values':'preserved as null with source_missing_value status','forward_fill':False,'interpolation':False},
  'panels':[{'panel_id':'volatility','title':'Market Volatility','series_ids':['VIXCLS']},{'panel_id':'financial_conditions','title':'Financial Conditions & Stress','series_ids':['NFCI','NFCICREDIT','STLFSI4']}],
  'series':series}
 out=root/'chart3_market_stress.json';raw=json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode('utf-8');out.write_bytes(raw)
 digest=hashlib.sha256(raw).hexdigest();(root/'chart3_market_stress.sha256').write_text(digest+'  chart3_market_stress.json\n',encoding='utf-8')
 report={'dataset_id':'TAC_CHART3_MARKET_STRESS','status':'PASS','generated_at':generated,'file':'chart3_market_stress.json','bytes':len(raw),'sha256':digest,'series':qa,'rules':{'interpolation':False,'forward_fill':False,'resampling':False,'native_dates_only':True}}
 (root/'chart3_market_stress_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 manifest_path=root/'manifest.json'
 if manifest_path.exists():
  manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
  manifest['chart_dataset']={'file':'chart3_market_stress.json','sha256':digest,'bytes':len(raw),'qa_file':'chart3_market_stress_qa.json','status':'PASS','generated_at':generated}
  manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data-dir',default='data/tac-chart3');a=p.parse_args();build(Path(a.data_dir))
