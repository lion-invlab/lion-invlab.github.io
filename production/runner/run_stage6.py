#!/usr/bin/env python3
"""Stage 6: deliver only the dated HTML, QA sidecar and delivery receipt to main/preview."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REPO="lion-invlab/lion-invlab.github.io"
ALLOWED=lambda d:[
 f"preview/{d}-review.html",
 f"preview/{d}-review.qa.json",
 f"preview/{d}-review.delivery.json",
]
PROTECTED=("index.html","data/calendar/weeks","production/templates/monday-mother-template.html",
 "production/templates/weekday-mother-template.html","production/config/mother-template-manifest.json")

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def blob(raw:bytes)->str:return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def git(args:list[str],cwd:Path=ROOT)->str:
 p=subprocess.run(["git",*args],cwd=cwd,text=True,capture_output=True)
 if p.returncode:raise RuntimeError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
 return p.stdout.strip()
def gh(args:list[str],env:dict)->dict:
 p=subprocess.run(["gh","api",*args],cwd=ROOT,text=True,capture_output=True,env=env)
 if p.returncode:raise RuntimeError(f"gh api {' '.join(args)} failed: {p.stderr.strip()}")
 return json.loads(p.stdout or "{}")

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--run-dir",required=True)
 ap.add_argument("--pages-timeout-seconds",type=int,default=1200)
 a=ap.parse_args()
 run_dir=Path(a.run_dir)
 if not run_dir.is_absolute():run_dir=ROOT/run_dir
 run_dir=run_dir.resolve()
 runs=ROOT/"production/runs"
 if runs.is_symlink() or runs.resolve()!=runs.absolute() or run_dir.parent!=runs.resolve() or run_dir.is_symlink():
  raise SystemExit("Stage 6 run directory must be a direct non-symlink child of production/runs")
 context=json.loads((run_dir/"run-context.json").read_text(encoding="utf-8"))
 stage5=json.loads((run_dir/"stage5-render-qa-receipt.json").read_text(encoding="utf-8"))
 if stage5.get("status")!="REVIEW_READY" or stage5.get("run_id")!=context.get("run_id"):
  raise SystemExit("Stage 6 requires same-Run Stage 5 REVIEW_READY")
 report_date=context["report_date"]
 if stage5.get("report_date")!=report_date:raise SystemExit("Stage 5 report date mismatch")
 html=run_dir/"review.html"; qa=run_dir/"qa-sidecar.json"
 if not html.is_file() or not qa.is_file():raise SystemExit("Stage 5 HTML or QA sidecar missing")
 html_raw=html.read_bytes();qa_doc=json.loads(qa.read_text(encoding="utf-8"))
 if sha(html_raw)!=stage5.get("html_sha256"):raise SystemExit("Stage 5 HTML SHA changed after QA")
 if sha(qa.read_bytes())!=stage5.get("qa_sidecar_sha256"):raise SystemExit("Stage 5 QA sidecar SHA changed after QA")
 if qa_doc.get("status")!="REVIEW_READY" or qa_doc.get("run_id")!=context["run_id"]:
  raise SystemExit("QA sidecar is not a same-Run REVIEW_READY artifact")
 report_path,qa_path,delivery_path=ALLOWED(report_date)
 if git(["branch","--show-current"])!="main":raise SystemExit("Stage 6 must execute from main checkout")
 git(["fetch","origin","main"])
 base=git(["rev-parse","origin/main"])
 worktree=ROOT.parent/f".tac-delivery-{context['run_id']}"
 if worktree.exists():raise SystemExit("delivery worktree path already exists; refusing to reuse stale worktree")
 git(["worktree","add","--detach",str(worktree),base])
 try:
  git(["config","user.name","github-actions[bot]"],worktree)
  git(["config","user.email","41898282+github-actions[bot]@users.noreply.github.com"],worktree)
  protected_before={p:git(["rev-parse",f"HEAD:{p}"],worktree) for p in PROTECTED if p!="data/calendar/weeks"}
  calendar_tree_before=git(["rev-parse","HEAD:data/calendar/weeks"],worktree)
  for p in (report_path,qa_path,delivery_path):
   target=worktree/p
   target.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():raise SystemExit(f"dated preview target already exists: {p}; do not overwrite an existing review")
  target_html=worktree/report_path;target_html.write_bytes(html_raw)
  qa_doc.update({"delivery_branch":"main","main_report_path":report_path,
   "delivery_payload_commit_sha":"PENDING","delivered_at_utc":datetime.now(timezone.utc).isoformat()})
  qa_bytes=(json.dumps(qa_doc,ensure_ascii=False,indent=2)+"\n").encode()
  (worktree/qa_path).write_bytes(qa_bytes)
  prebuild=run_dir/"prebuild-input-receipt.json"
  builder_blob=qa_doc.get("groups",{}).get("run_integration",{}).get("builder_blob_sha")
  if not builder_blob:builder_blob=json.loads((run_dir/"render-manifest.json").read_text(encoding="utf-8")).get("builder_blob_sha")
  delivery={
   "schema_version":"1.0","status":"DELIVERED_PENDING_PAGES",
   "report_date":report_date,"run_id":context["run_id"],
   "source":{"repository":REPO,"branch":"main","run_path":str(html.relative_to(ROOT)),
    "workflow_run_id":context.get("workflow_run_id"),"workflow_run_attempt":context.get("workflow_run_attempt"),
    "trigger_commit_sha":context.get("main_commit_sha")},
   "targets":{"html":report_path,"qa":qa_path,"delivery_receipt":delivery_path},
   "html":{"sha256":sha(html_raw),"git_blob_sha":blob(html_raw)},
   "qa":{"sha256":sha(qa_bytes),"source_qa_sha256":sha(qa.read_bytes())},
   "builder_sha":builder_blob,
   "prebuild_receipt_sha256":sha(prebuild),
   "protected_files_unchanged":True,
   "protected_paths":list(PROTECTED),
   "delivery_commit_sha":"PENDING"
  }
  (worktree/delivery_path).write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  git(["add","--",report_path,qa_path,delivery_path],worktree)
  staged=git(["diff","--cached","--name-only"],worktree).splitlines()
  if set(staged)!=set((report_path,qa_path,delivery_path)) or len(staged)!=3:
   raise SystemExit(f"Stage 6 first commit path allowlist violation: {staged}")
  git(["commit","-m",f"docs(preview): deliver TAC review {report_date}"],worktree)
  payload_commit=git(["rev-parse","HEAD"],worktree)
  git(["push","origin","HEAD:main"],worktree)
  # Finalize the receipt with the commit that introduced all three approved preview artifacts.
  qa_doc["delivery_payload_commit_sha"]=payload_commit
  qa_doc["delivery_commit_sha"]=payload_commit
  qa_doc["delivery_finalized_at_utc"]=datetime.now(timezone.utc).isoformat()
  qa_bytes=(json.dumps(qa_doc,ensure_ascii=False,indent=2)+"\n").encode()
  (worktree/qa_path).write_bytes(qa_bytes)
  delivery["status"]="DELIVERED"
  delivery["delivery_commit_sha"]=payload_commit
  delivery["delivery_commit_message"]=f"docs(preview): deliver TAC review {report_date}"
  delivery["html"]["remote_git_blob_sha"]=blob((worktree/report_path).read_bytes())
  delivery["qa"]["sha256"]=sha(qa_bytes)
  delivery["qa"]["remote_git_blob_sha"]=blob(qa_bytes)
  (worktree/delivery_path).write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  git(["add","--",qa_path,delivery_path],worktree)
  staged2=git(["diff","--cached","--name-only"],worktree).splitlines()
  if set(staged2)!=set((qa_path,delivery_path)) or len(staged2)!=2:raise SystemExit(f"Stage 6 receipt-finalization path violation: {staged2}")
  git(["commit","-m",f"chore(preview): finalize TAC delivery receipt {report_date}"],worktree)
  final_commit=git(["rev-parse","HEAD"],worktree)
  git(["push","origin","HEAD:main"],worktree)
  # Verify remote main bytes and the complete path set since the delivery base.
  remote_head=git(["ls-remote","origin","refs/heads/main"],worktree).split()[0]
  if remote_head!=final_commit:raise SystemExit("Remote main HEAD differs from final delivery commit")
  for path,expected in ((report_path,html_raw),(qa_path,(worktree/qa_path).read_bytes()),(delivery_path,(worktree/delivery_path).read_bytes())):
   actual=subprocess.run(["git","show",f"{final_commit}:{path}"],cwd=worktree,check=True,capture_output=True).stdout
   if actual!=expected:raise SystemExit(f"Remote readback bytes mismatch: {path}")
  changed=git(["diff","--name-only",base,final_commit],worktree).splitlines()
  if set(changed)!=set((report_path,qa_path,delivery_path)) or len(changed)!=3:
   raise SystemExit(f"Final delivery commit range changed files outside three-file allowlist: {changed}")
  for path,expected in protected_before.items():
   if git(["rev-parse",f"{final_commit}:{path}"],worktree)!=expected:
    raise SystemExit(f"Protected path changed during Stage 6: {path}")
  if git(["rev-parse",f"{final_commit}:data/calendar/weeks"],worktree)!=calendar_tree_before:
   raise SystemExit("Calendar database tree changed during Stage 6")
  # GITHUB_TOKEN pushes do not reliably trigger other workflows; dispatch Pages explicitly.
  env=os.environ.copy()
  token=env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
  if not token:raise SystemExit("GITHUB_TOKEN is required to dispatch the existing Pages workflow")
  env["GH_TOKEN"]=token
  before_runs=gh(["repos/"+REPO+"/actions/workflows/pages.yml/runs?branch=main&per_page=20"],env)
  old_ids={x["id"] for x in before_runs.get("workflow_runs",[])}
  subprocess.run(["gh","api","-X","POST",f"repos/{REPO}/actions/workflows/pages.yml/dispatches","-f","ref=main"],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
  deadline=time.time()+a.pages_timeout_seconds
  pages_run=None
  while time.time()<deadline:
   runs_doc=gh(["repos/"+REPO+"/actions/workflows/pages.yml/runs?branch=main&per_page=20"],env)
   new=[x for x in runs_doc.get("workflow_runs",[]) if x["id"] not in old_ids and x.get("head_sha")==final_commit and x.get("event")=="workflow_dispatch"]
   if new:
    pages_run=sorted(new,key=lambda x:x.get("created_at",""),reverse=True)[0]
    if pages_run.get("status")=="completed":break
   time.sleep(15)
  if not pages_run or pages_run.get("status")!="completed" or pages_run.get("conclusion")!="success":
   raise SystemExit("Pages deployment did not complete successfully before timeout")
  preview_url=f"https://lion-invlab.github.io/{report_path}"
  req=urllib.request.Request(preview_url,headers={"User-Agent":"TAC-Stage6-Preview-Verification/1.0"})
  with urllib.request.urlopen(req,timeout=30) as response:
   public_html=response.read().decode("utf-8","replace")
   if response.status!=200 or f'<meta name="report-date" content="{report_date}"' not in public_html:
    raise SystemExit("Public preview HTTP/date verification failed")
  final_receipt={
   "schema_version":"1.0","status":"DELIVERED_AND_PUBLICLY_VERIFIED",
   "run_id":context["run_id"],"report_date":report_date,
   "payload_commit_sha":payload_commit,"final_receipt_commit_sha":final_commit,
   "pages_workflow_run_id":pages_run["id"],"pages_workflow_conclusion":pages_run["conclusion"],
   "preview_url":preview_url,"public_http_status":200,
   "remote_readback":"PASS","three_file_allowlist":"PASS",
   "protected_paths_unchanged":"PASS","html_sha256":sha(html_raw),
   "qa_sha256":sha((worktree/qa_path).read_bytes()),
   "delivery_receipt_sha256":sha((worktree/delivery_path).read_bytes()),
   "delivered_at_utc":datetime.now(timezone.utc).isoformat()
  }
  (run_dir/"stage6-delivery-receipt.json").write_text(json.dumps(final_receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps(final_receipt,ensure_ascii=False,indent=2))
 finally:
  subprocess.run(["git","worktree","remove","--force",str(worktree)],cwd=ROOT,capture_output=True,text=True)

if __name__=="__main__":main()
