#!/usr/bin/env python3
"""Stage 6 pre-commit: create only the three main/preview review-delivery artifacts."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    args=ap.parse_args()
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute():run_dir=ROOT/run_dir
    runs=ROOT/"production/runs"
    if runs.is_symlink() or runs.resolve()!=runs.absolute() or run_dir.is_symlink():
        raise SystemExit("Stage 6 run path must not contain symlinks")
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs.resolve():raise SystemExit("Stage 6 run directory must be a direct child of production/runs")
    context=json.loads((run_dir/"run-context.json").read_text(encoding="utf-8"))
    stage5=json.loads((run_dir/"stage5-render-qa-receipt.json").read_text(encoding="utf-8"))
    qa=json.loads((run_dir/"qa-sidecar.json").read_text(encoding="utf-8"))
    render=json.loads((run_dir/"render-manifest.json").read_text(encoding="utf-8"))
    html=run_dir/"review.html"
    if stage5.get("status")!="REVIEW_READY" or qa.get("status")!="REVIEW_READY":
        raise SystemExit("Stage 6 requires Stage 5 REVIEW_READY")
    if stage5.get("run_id")!=context["run_id"] or qa.get("run_id")!=context["run_id"] or render.get("run_id")!=context["run_id"]:
        raise SystemExit("Stage 5 artifacts do not share the Stage 1 Run ID")
    if sha(html)!=stage5.get("html_sha256") or sha(html)!=render.get("output",{}).get("sha256"):
        raise SystemExit("Review HTML SHA differs across Stage 5 receipts")
    report_date=context["report_date"]
    destinations={
      "html":ROOT/f"preview/{report_date}-review.html",
      "qa":ROOT/f"preview/{report_date}-review.qa.json",
      "delivery":ROOT/f"preview/{report_date}-review.delivery.json"
    }
    for key,path in destinations.items():
        if path.exists() and path.is_symlink():raise SystemExit(f"Preview destination is a symlink: {path}")
    if destinations["html"].exists() and sha(destinations["html"])!=sha(html):
        raise SystemExit("A different preview HTML already exists for this report date; refusing overwrite")
    if destinations["qa"].exists():
        existing=json.loads(destinations["qa"].read_text(encoding="utf-8"))
        if existing.get("run_id")!=context["run_id"]:
            raise SystemExit("A QA sidecar from a different Run ID already exists; refusing overwrite")
    if destinations["delivery"].exists():
        existing=json.loads(destinations["delivery"].read_text(encoding="utf-8"))
        if existing.get("run_id")!=context["run_id"]:
            raise SystemExit("A delivery receipt from a different Run ID already exists; refusing overwrite")
    destinations["html"].parent.mkdir(parents=True,exist_ok=True)
    destinations["html"].write_bytes(html.read_bytes())
    qa["delivery"]={"status":"PREVIEW_COMMIT_PENDING","branch":"main","path":str(destinations["html"].relative_to(ROOT)),
      "run_id":context["run_id"],"html_sha256":sha(html),"source_main_commit_sha":context["main_commit_sha"]}
    destinations["qa"].write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt={
      "schema_version":"1.0","status":"PREVIEW_COMMIT_PENDING",
      "run_id":context["run_id"],"report_date":report_date,
      "source_main_commit_sha":context["main_commit_sha"],
      "mother":context["mother"],"render_manifest_sha256":sha(run_dir/"render-manifest.json"),
      "stage5_receipt_sha256":sha(run_dir/"stage5-render-qa-receipt.json"),
      "html":{"path":str(destinations["html"].relative_to(ROOT)),"sha256":sha(destinations["html"])},
      "qa":{"path":str(destinations["qa"].relative_to(ROOT)),"sha256":sha(destinations["qa"])},
      "delivery":{"path":str(destinations["delivery"].relative_to(ROOT))},
      "expected_public_url":f"https://lion-invlab.github.io/preview/{report_date}-review.html",
      "formal_homepage_modified":False,"history_archive_modified":False,
      "created_at_utc":datetime.now(timezone.utc).isoformat()
    }
    destinations["delivery"].write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    precommit={"status":"PREVIEW_COMMIT_PENDING","run_id":context["run_id"],"report_date":report_date,
      "files":{k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)} for k,v in destinations.items()}}
    (run_dir/"stage6-precommit-receipt.json").write_text(json.dumps(precommit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(precommit,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
