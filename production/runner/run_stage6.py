#!/usr/bin/env python3
"""Stage 6: commit only the dated preview triplet, deploy Pages, then finalize delivery evidence."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from bs4 import BeautifulSoup

from stage_wr_loader import load_stage_wr
from run_state import transition_state, validate_state

ROOT=Path(__file__).resolve().parents[2]
REPO="lion-invlab/lion-invlab.github.io"
def allowed_paths(report_date, context=None):
    # An owner-authorized same-date rerun gets its own preview namespace.
    # The originally approved preview remains intact for the homepage publication lock.
    suffix="-rerun" if context and context.get("supersedes_run_id") else ""
    return [f"preview/main/{report_date}{suffix}-review.html",
            f"preview/main/{report_date}{suffix}-review.qa.json",
            f"preview/main/{report_date}{suffix}-review.delivery.json"]
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
def validate_stage5_handoff(stage5:dict, qa_doc:dict, render_doc:dict, context:dict,
                            html_sha256:str, render_sha256:str, stage4_doc:dict,
                            stage4_sha256:str)->None:
    if (stage5.get("status")!="REVIEW_READY" or stage5.get("run_id")!=context.get("run_id")
            or stage5.get("report_date")!=context.get("report_date")
            or stage5.get("trading_date")!=context.get("trading_date")):
        raise ValueError("Stage 6 requires same-Run Stage 5 REVIEW_READY with exact dates")
    if (qa_doc.get("status")!="REVIEW_READY" or qa_doc.get("run_id")!=context.get("run_id")
            or qa_doc.get("report_date")!=context.get("report_date")
            or qa_doc.get("trading_date")!=context.get("trading_date")):
        raise ValueError("QA sidecar is not a same-Run/date REVIEW_READY artifact")
    if (stage5.get("html_sha256")!=html_sha256
            or stage5.get("render_manifest_sha256")!=render_sha256):
        raise ValueError("Stage 5 artifact SHA handoff mismatch")
    if (render_doc.get("run_id")!=context.get("run_id")
            or render_doc.get("report_date")!=context.get("report_date")
            or render_doc.get("trading_date")!=context.get("trading_date")
            or render_doc.get("output",{}).get("sha256")!=html_sha256
            or render_doc.get("builder_blob_sha")!=stage5.get("builder_blob_sha")):
        raise ValueError("Stage 5 render manifest identity/HTML/Builder binding mismatch")
    binding=stage4_doc.get("editorial_run_binding") or {}
    if (stage4_sha256!=stage5.get("stage4_receipt_sha256")
            or binding.get("run_id")!=context.get("run_id")
            or binding.get("market_snapshot_sha256")!=stage5.get("market_snapshot_sha256")
            or binding.get("research_bundle_sha256")!=stage5.get("research_bundle_sha256")):
        raise ValueError("Stage 5 editorial evidence does not match Stage 4 receipt")

def validate_existing_preview_triplet(worktree:Path, report_path:str, qa_path:str, delivery_path:str, context:dict)->bool:
    """Allow replacement only when all existing preview files prove the exact same delivered Run."""
    paths=(report_path,qa_path,delivery_path)
    targets={ "html":report_path, "qa":qa_path, "delivery_receipt":delivery_path }
    files=[worktree/path for path in paths]
    present=[path.is_file() for path in files]
    if not any(present):
        return False
    if not all(present):
        raise SystemExit("existing dated preview triplet is incomplete; refusing replacement")
    html_raw=(worktree/report_path).read_bytes()
    qa_doc=json.loads((worktree/qa_path).read_text(encoding="utf-8"))
    delivery_doc=json.loads((worktree/delivery_path).read_text(encoding="utf-8"))
    expected_run=context.get("run_id")
    expected_date=context.get("report_date")
    if (delivery_doc.get("status")!="DELIVERED_AND_PUBLICLY_VERIFIED"
            or delivery_doc.get("run_id")!=expected_run
            or delivery_doc.get("report_date")!=expected_date
            or delivery_doc.get("targets")!=targets
            or delivery_doc.get("public_url_verified") is not True):
        raise SystemExit("existing dated preview belongs to another Run/date or is not fully verified; refusing replacement")
    if (delivery_doc.get("html",{}).get("sha256")!=sha(html_raw)
            or delivery_doc.get("html",{}).get("git_blob_sha")!=blob(html_raw)):
        raise SystemExit("existing preview HTML does not match its delivery receipt; refusing replacement")
    if (delivery_doc.get("formal_homepage_modified") is not False
            or delivery_doc.get("history_archive_modified") is not False):
        raise SystemExit("existing preview receipt does not prove protected paths unchanged; refusing replacement")
    if (qa_doc.get("status")!="REVIEW_READY" or qa_doc.get("run_id")!=expected_run
            or qa_doc.get("report_date")!=expected_date):
        raise SystemExit("existing QA sidecar is not bound to the same Run/date; refusing replacement")
    qa_delivery=qa_doc.get("delivery") or {}
    if (qa_delivery.get("status")!="DELIVERED_AND_PUBLICLY_VERIFIED"
            or qa_delivery.get("run_id")!=expected_run
            or qa_delivery.get("html_sha256")!=sha(html_raw)
            or qa_delivery.get("public_url_verified") is not True):
        raise SystemExit("existing QA delivery attestation is not same-Run/publicly verified; refusing replacement")
    return True

def write_json(path:Path,data:dict):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    ap.add_argument("--pages-timeout-seconds",type=int,default=1200)
    a=ap.parse_args()
    run_dir=Path(a.run_dir)
    if not run_dir.is_absolute():run_dir=ROOT/run_dir
    runs=ROOT/"production/runs"
    if runs.is_symlink() or runs.resolve()!=runs.absolute() or run_dir.is_symlink():
        raise SystemExit("Stage 6 run directory must not contain symlinks")
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs.resolve():raise SystemExit("Stage 6 run directory must be a direct child of production/runs")
    context=json.loads((run_dir/"run-context.json").read_text(encoding="utf-8"))
    wr_loaded=load_stage_wr("STAGE_6",context)
    state_path=run_dir/"run-state.json"
    state=json.loads(state_path.read_text(encoding="utf-8"))
    validate_state(state,expected_run_id=context["run_id"])
    if state["stages"]["STAGE_5"]["status"]!="PASS":
        raise SystemExit("Stage 6 requires Stage 5 PASS in the authoritative Run state")
    if state["stages"]["STAGE_6"]["status"]=="FAILED":
        state=transition_state(state,stage="STAGE_6",expected_version=state["state_version"],expected_status="FAILED",new_status="READY",recovery=True)
    elif state["stages"]["STAGE_6"]["status"]=="DEFERRED":
        state=transition_state(state,stage="STAGE_6",expected_version=state["state_version"],expected_status="DEFERRED",new_status="READY")
    if state["stages"]["STAGE_6"]["status"]!="READY":
        raise SystemExit("Stage 6 is not READY in the authoritative Run state")
    state=transition_state(state,stage="STAGE_6",expected_version=state["state_version"],expected_status="READY",new_status="RUNNING",
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),lease_owner="github-actions-stage6",
        lease_expires_at=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat().replace("+00:00","Z"),
        input_sha256=hashlib.sha256((run_dir/"stage5-render-qa-receipt.json").read_bytes()).hexdigest())
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    stage5=json.loads((run_dir/"stage5-render-qa-receipt.json").read_text(encoding="utf-8"))
        report_date=context["report_date"]
    html=run_dir/"review.html";qa=run_dir/"qa-sidecar.json"
    render_path=run_dir/"render-manifest.json";stage4_path=run_dir/"stage4-analysis-receipt.json"
    if not html.is_file() or not qa.is_file() or not render_path.is_file() or not stage4_path.is_file():
        raise SystemExit("Stage 5 HTML, QA, render manifest or Stage 4 receipt missing")
    html_raw=html.read_bytes();qa_source_raw=qa.read_bytes();qa_doc=json.loads(qa_source_raw)
    render_doc=json.loads(render_path.read_text(encoding="utf-8"))
    stage4_doc=json.loads(stage4_path.read_text(encoding="utf-8"))
    try:
        validate_stage5_handoff(stage5,qa_doc,render_doc,context,sha(html_raw),sha(render_path.read_bytes()),stage4_doc,sha(stage4_path.read_bytes()))
    except ValueError as exc:
        raise SystemExit(str(exc))
    if sha(qa_source_raw)!=stage5.get("qa_sidecar_sha256"):
        raise SystemExit("Stage 5 QA sidecar SHA changed after QA")
    report_path,qa_path,delivery_path=allowed_paths(report_date,context)
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
        same_run_replacement=validate_existing_preview_triplet(worktree,report_path,qa_path,delivery_path,context)
        for path in (report_path,qa_path,delivery_path):
            target=worktree/path
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and not same_run_replacement:
                raise SystemExit(f"dated preview target already exists: {path}; refusing overwrite")
        (worktree/report_path).write_bytes(html_raw)
        qa_doc["delivery"]={"status":"PAGES_DEPLOY_PENDING","branch":"main","path":report_path,
            "run_id":context["run_id"],"html_sha256":sha(html_raw)}
        qa_bytes=(json.dumps(qa_doc,ensure_ascii=False,indent=2)+"\n").encode()
        (worktree/qa_path).write_bytes(qa_bytes)
        prebuild=run_dir/"prebuild-input-receipt.json"
        render=json.loads((run_dir/"render-manifest.json").read_text(encoding="utf-8"))
        builder_blob=render.get("builder_blob_sha")
        if not builder_blob:raise SystemExit("render-manifest missing Builder blob SHA")
        delivery={
            "schema_version":"1.0","status":"PAGES_DEPLOY_PENDING","report_date":report_date,"run_id":context["run_id"],
            "source":{"repository":REPO,"branch":"main","run_path":str(html.relative_to(ROOT)),
                "workflow_run_id":context.get("workflow_run_id"),"workflow_run_attempt":context.get("workflow_run_attempt"),
                "trigger_commit_sha":context.get("main_commit_sha")},
            "targets":{"html":report_path,"qa":qa_path,"delivery_receipt":delivery_path},
            "html":{"sha256":sha(html_raw),"git_blob_sha":blob(html_raw)},
            "qa":{"sha256":sha(qa_bytes),"source_qa_sha256":sha(qa_source_raw)},
            "builder_sha":builder_blob,
             "stage_wr_loaded":wr_loaded,"prebuild_receipt_sha256":sha(prebuild.read_bytes()),
            "stage5_receipt_sha256":sha((run_dir/"stage5-render-qa-receipt.json").read_bytes()),
            "protected_paths_unchanged":True,"protected_paths":list(PROTECTED)+["data/calendar/weeks"],
            "formal_homepage_modified":False,"history_archive_modified":False,
            "payload_commit_sha":"PENDING","pages_deployment_commit_sha":"PENDING",
            "pages_workflow_run_id":None,"pages_workflow_conclusion":None,"public_url_verified":False
        }
        write_json(worktree/delivery_path,delivery)
        git(["add","--",report_path,qa_path,delivery_path],worktree)
        staged=git(["diff","--cached","--name-only"],worktree).splitlines()
        if set(staged)!=set((report_path,qa_path,delivery_path)) or len(staged)!=3:
            raise SystemExit(f"Stage 6 payload path allowlist violation: {staged}")
        git(["commit","-m",f"docs(preview): deliver TAC review {report_date}"],worktree)
        payload_commit=git(["rev-parse","HEAD"],worktree)
        git(["push","origin","HEAD:main"],worktree)
        payload_changed=git(["diff","--name-only",base,payload_commit],worktree).splitlines()
        if set(payload_changed)!=set((report_path,qa_path,delivery_path)) or len(payload_changed)!=3:
            raise SystemExit(f"Stage 6 payload commit changed files outside allowlist: {payload_changed}")
        for path,expected in ((report_path,html_raw),(qa_path,qa_bytes),(delivery_path,(worktree/delivery_path).read_bytes())):
            actual=subprocess.run(["git","show",f"{payload_commit}:{path}"],cwd=worktree,check=True,capture_output=True).stdout
            if actual!=expected:raise SystemExit(f"Payload commit bytes mismatch: {path}")
        for path,expected in protected_before.items():
            if git(["rev-parse",f"{payload_commit}:{path}"],worktree)!=expected:
                raise SystemExit(f"Protected path changed during Stage 6: {path}")
        if git(["rev-parse",f"{payload_commit}:data/calendar/weeks"],worktree)!=calendar_tree_before:
            raise SystemExit("Calendar database tree changed during Stage 6")
        env=os.environ.copy()
        token=env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
        if not token:raise SystemExit("GITHUB_TOKEN is required to dispatch Pages")
        env["GH_TOKEN"]=token
        before=gh([f"repos/{REPO}/actions/workflows/pages.yml/runs?branch=main&per_page=20"],env)
        old_ids={x["id"] for x in before.get("workflow_runs",[])}
        subprocess.run(["gh","api","-X","POST",f"repos/{REPO}/actions/workflows/pages.yml/dispatches","-f","ref=main"],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
        deadline=time.time()+a.pages_timeout_seconds
        pages_run=None
        while time.time()<deadline:
            doc=gh([f"repos/{REPO}/actions/workflows/pages.yml/runs?branch=main&per_page=20"],env)
            matches=[x for x in doc.get("workflow_runs",[]) if x["id"] not in old_ids and x.get("head_sha")==payload_commit and x.get("event")=="workflow_dispatch"]
            if matches:
                pages_run=sorted(matches,key=lambda x:x.get("created_at",""),reverse=True)[0]
                if pages_run.get("status")=="completed":break
            time.sleep(15)
        if not pages_run or pages_run.get("status")!="completed" or pages_run.get("conclusion")!="success":
            raise SystemExit("Pages deployment did not complete successfully before timeout")
        preview_url=f"https://lion-invlab.github.io/{report_path}"
        req=urllib.request.Request(preview_url,headers={"User-Agent":"TAC-Stage6-Preview-Verification/1.0"})
        with urllib.request.urlopen(req,timeout=30) as response:
            public_bytes=response.read()
            public_html=public_bytes.decode("utf-8","replace")
            public_meta=BeautifulSoup(public_html,"html.parser").select_one('meta[name="report-date"]')
            if response.status!=200 or public_meta is None or public_meta.get("content")!=report_date:
                raise SystemExit("Public preview HTTP/date verification failed")
            if sha(public_bytes)!=sha(html_raw):raise SystemExit("Public preview HTML bytes do not match Stage 5 artifact")
            if context["run_id"] not in public_html:raise SystemExit("Public preview does not expose expected Run ID provenance")
        qa_doc["delivery"].update({"status":"DELIVERED_AND_PUBLICLY_VERIFIED","payload_commit_sha":payload_commit,
            "pages_workflow_run_id":pages_run["id"],"pages_workflow_conclusion":pages_run["conclusion"],
            "preview_url":preview_url,"public_url_verified":True,"public_html_sha256":sha(public_bytes),
            "verified_at_utc":datetime.now(timezone.utc).isoformat()})
        qa_final=(json.dumps(qa_doc,ensure_ascii=False,indent=2)+"\n").encode()
        (worktree/qa_path).write_bytes(qa_final)
        delivery.update({"status":"DELIVERED_AND_PUBLICLY_VERIFIED","payload_commit_sha":payload_commit,
            "pages_deployment_commit_sha":payload_commit,"pages_workflow_run_id":pages_run["id"],
            "pages_workflow_conclusion":pages_run["conclusion"],"public_url_verified":True,
            "preview_url":preview_url,"public_http_status":200,"public_html_sha256":sha(public_bytes),
            "qa":{"sha256":sha(qa_final),"remote_git_blob_sha":blob(qa_final)},
            "finalized_at_utc":datetime.now(timezone.utc).isoformat()})
        write_json(worktree/delivery_path,delivery)
        git(["add","--",qa_path,delivery_path],worktree)
        staged_final=git(["diff","--cached","--name-only"],worktree).splitlines()
        if set(staged_final)!={qa_path,delivery_path} or len(staged_final)!=2:
            raise SystemExit(f"Stage 6 final sidecar path allowlist violation: {staged_final}")
        git(["commit","-m",f"chore(preview): finalize TAC delivery receipt {report_date}"],worktree)
        final_receipt_commit=git(["rev-parse","HEAD"],worktree)
        git(["push","origin","HEAD:main"],worktree)
        remote_head=git(["ls-remote","origin","refs/heads/main"],worktree).split()[0]
        if remote_head!=final_receipt_commit:raise SystemExit("Remote main HEAD differs from final receipt commit")
        for path in (report_path,qa_path,delivery_path):
            expected=(worktree/path).read_bytes()
            actual=subprocess.run(["git","show",f"{final_receipt_commit}:{path}"],cwd=worktree,check=True,capture_output=True).stdout
            if actual!=expected:raise SystemExit(f"Final remote readback bytes mismatch: {path}")
        changed=git(["diff","--name-only",base,final_receipt_commit],worktree).splitlines()
        if set(changed)!={report_path,qa_path,delivery_path} or len(changed)!=3:
            raise SystemExit(f"Final delivery commit range changed files outside three-file allowlist: {changed}")
        for path,expected in protected_before.items():
            if git(["rev-parse",f"{final_receipt_commit}:{path}"],worktree)!=expected:
                raise SystemExit(f"Protected path changed during Stage 6: {path}")
        if git(["rev-parse",f"{final_receipt_commit}:data/calendar/weeks"],worktree)!=calendar_tree_before:
            raise SystemExit("Calendar database tree changed during Stage 6")
        final_receipt={"schema_version":"1.0","status":"DELIVERED_AND_PUBLICLY_VERIFIED",
            "run_id":context["run_id"],"report_date":report_date,
            "wr_loaded":wr_preflight,
            "payload_commit_sha":payload_commit,"pages_deployment_commit_sha":payload_commit,
            "final_receipt_commit_sha":final_receipt_commit,
            "pages_workflow_run_id":pages_run["id"],"pages_workflow_conclusion":pages_run["conclusion"],
            "preview_url":preview_url,"public_http_status":200,"public_html_sha256":sha(public_bytes),
            "remote_readback":"PASS","three_file_allowlist":"PASS","protected_paths_unchanged":"PASS",
            "html_sha256":sha(html_raw),"qa_sha256":sha(qa_final),
            "delivery_receipt_sha256":sha((worktree/delivery_path).read_bytes()),
            "delivered_at_utc":datetime.now(timezone.utc).isoformat()}
        final_receipt["overall_status"]="AWAITING_APPROVAL"
        final_receipt_path=run_dir/"stage6-delivery-receipt.json"
        write_json(final_receipt_path,final_receipt)
        state=json.loads(state_path.read_text(encoding="utf-8"))
        state=transition_state(state,stage="STAGE_6",expected_version=state["state_version"],expected_status="RUNNING",new_status="PASS",
            now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),input_sha256=hashlib.sha256((run_dir/"stage5-render-qa-receipt.json").read_bytes()).hexdigest(),
            output_sha256=sha(final_receipt_path),receipt_path=str(final_receipt_path.relative_to(ROOT)))
        state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(final_receipt,ensure_ascii=False,indent=2))
    finally:
        subprocess.run(["git","worktree","remove","--force",str(worktree)],cwd=ROOT,capture_output=True,text=True)

if __name__=="__main__":main()
