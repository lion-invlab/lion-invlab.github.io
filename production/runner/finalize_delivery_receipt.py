#!/usr/bin/env python3
"""Finalize the preview delivery receipt after GitHub Pages URL verification."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def git_blob(commit:str,path:str)->str:
    return subprocess.check_output(["git","rev-parse",f"{commit}:{path}"],cwd=ROOT,text=True).strip()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--report-date",required=True)
    ap.add_argument("--preview-commit",required=True)
    ap.add_argument("--pages-run-id",required=True)
    ap.add_argument("--pages-conclusion",required=True)
    ap.add_argument("--public-url-verified",choices=["true","false"],required=True)
    ap.add_argument("--public-url-content-sha256",required=True)
    args=ap.parse_args()
    if args.pages_conclusion!="success" or args.public_url_verified!="true":
        raise SystemExit("Cannot mark DELIVERED without successful Pages workflow and public URL verification")
    date=args.report_date
    html_path=f"preview/{date}-review.html"
    qa_path=f"preview/{date}-review.qa.json"
    receipt_path=f"preview/{date}-review.delivery.json"
    for p in (html_path,qa_path,receipt_path):
        if not (ROOT/p).is_file():raise SystemExit(f"Missing preview artifact: {p}")
    subprocess.run(["git","merge-base","--is-ancestor",args.preview_commit,"HEAD"],cwd=ROOT,check=True)
    html_sha=sha(ROOT/html_path)
    qa_sha=sha(ROOT/qa_path)
    if html_sha!=args.public_url_content_sha256:
        raise SystemExit("Public preview content SHA does not match main preview HTML")
    receipt=json.loads((ROOT/receipt_path).read_text(encoding="utf-8"))
    if receipt.get("status")!="PREVIEW_COMMIT_PENDING" or receipt.get("report_date")!=date:
        raise SystemExit("Delivery receipt is not in the expected precommit state")
    if receipt.get("html",{}).get("sha256")!=html_sha or receipt.get("qa",{}).get("sha256")!=qa_sha:
        raise SystemExit("Preview HTML or QA sidecar changed after Pages verification")
    receipt.update({
      "status":"DELIVERED","preview_commit_sha":args.preview_commit,
      "preview_html_git_blob_sha":git_blob(args.preview_commit,html_path),
      "preview_qa_git_blob_sha":git_blob(args.preview_commit,qa_path),
      "pages_workflow_run_id":args.pages_run_id,
      "pages_workflow_conclusion":args.pages_conclusion,
      "public_url_verified":True,
      "public_url_content_sha256":args.public_url_content_sha256,
      "finalized_at_utc":datetime.now(timezone.utc).isoformat(),
      "formal_homepage_modified":False,"history_archive_modified":False
    })
    receipt["delivery_receipt_sha256_after_finalize"]=None
    (ROOT/receipt_path).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt["delivery_receipt_sha256_after_finalize"]=sha(ROOT/receipt_path)
    (ROOT/receipt_path).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"DELIVERED","report_date":date,"preview_commit_sha":args.preview_commit,
      "html_sha256":html_sha,"qa_sha256":qa_sha,"delivery_receipt_sha256":sha(ROOT/receipt_path),
      "pages_run_id":args.pages_run_id,"public_url_verified":True},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
