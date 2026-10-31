#!/usr/bin/env python3
"""Integration tests for TAC editorial HTML binding on both approved mothers."""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from assemble_tac_daily_content import empty_content
from render_tac_full_report import render_full
from validate_tac_daily_snapshot import load_validator, sample_snapshot

MOTHERS={
 "monday":ROOT/"母版專區"/"TAC_母版_週一_2026-10-28_最終定版.html",
 "weekday":ROOT/"母版專區"/"TAC_母版_週二至週五_2026-10-28_最終定版.html",
}
def sample(report_date,template):
    data=empty_content(report_date,"2026-10-30","2026-10-31T21:00:00+08:00")
    data["meta"]["news_window_start"]="2026-10-30T12:00:00+08:00"
    data["meta"]["news_window_end"]=report_date+"T05:00:00+08:00"
    def news(prefix,count,category):
        return [{
          "id":f"{prefix}-{i}","category":category,
          "headline":f"Synthetic {prefix} headline {i}",
          "summary":f"Synthetic {prefix} summary {i}; test-only content.",
          "published_at":f"2026-10-31T{8+i:02d}:00:00+08:00",
          "source":{"name":"Synthetic source","url":f"https://example.com/{prefix}/{i}",
            "published_at":f"2026-10-31T{8+i:02d}:00:00+08:00",
            "observed_at":"2026-10-31T21:00:00+08:00"},
          "status":"verified","impact":None
        } for i in range(1,count+1)]
    data["focus_news"]=news("focus",5,"macro")
    data["market_headlines"]=news("headline",10,"market")
    for group in ("focus_news","market_headlines"):
        data["coverage"][group]={
          "status":"complete","source_refs":[f"synthetic-{group}-batch"],
          "checked_at":"2026-10-31T21:00:00+08:00"
        }
    def src(tag):
        return {"name":"Synthetic calendar source","url":f"https://example.com/{tag}",
          "published_at":"2026-10-31T12:00:00+08:00","observed_at":"2026-10-31T21:00:00+08:00"}
    event_day="2026-11-03" if report_date=="2026-11-02" else "2026-11-04"
    data["economic_calendar"]=[{
      "id":"econ-current","event_date":event_day+"T20:30:00+08:00",
      "region":"美國","event_name":"Synthetic CPI release","importance_stars":3,
      "previous":"2.0%","forecast":"2.1%","actual":None,"status":"upcoming",
      "impact_judgment":"測試用市場影響判讀","source":src("econ-current")
    }]
    data["earnings_calendar"]=[{
      "id":"earn-current","event_date":event_day+"T21:00:00+08:00",
      "company":"Synthetic Co","ticker":"SYN","session":"after_market",
      "importance_stars":None,"importance_basis":"major_event_assessment",
      "importance_basis_source":"Synthetic test-only major event assessment",
      "importance_rating_source":None,"eps_estimate":1.2,"eps_actual":None,
      "revenue_estimate":100.0,"revenue_actual":None,"status":"upcoming",
      "stock_price_reaction":None,"source":src("earn-current")
    }]
    if template=="monday":
        data["previous_economic_calendar"]=[{
          "id":"econ-previous","event_date":"2026-10-30T20:30:00+08:00","region":"美國",
          "event_name":"Synthetic prior CPI release","importance_stars":3,
          "previous":"2.0%","forecast":"2.1%","actual":"2.2%","status":"released",
          "impact_judgment":"測試用實際值判讀","source":src("econ-previous")
        }]
        data["previous_earnings_calendar"]=[{
          "id":"earn-previous","event_date":"2026-10-30T21:00:00+08:00","company":"Prior Synthetic Co",
          "ticker":"PSYN","session":"after_market","importance_stars":None,
          "importance_basis":"major_event_assessment","importance_basis_source":"Synthetic test-only assessment",
          "importance_rating_source":None,"eps_estimate":1.0,"eps_actual":1.1,
          "revenue_estimate":90.0,"revenue_actual":92.0,"status":"released",
          "stock_price_reaction":"測試用股價反應","source":src("earn-previous")
        }]
    return data
def run_case(kind,report_date,weekday):
    data=sample(report_date,kind)
    with tempfile.TemporaryDirectory(prefix="tac-editorial-render-test-") as tmp:
        base=Path(tmp); snapshot_path=base/"snapshot.json"; output=base/"editorial.html"; payload=base/"content.json"
        validator,schema=load_validator()
        snapshot=sample_snapshot(schema)
        snapshot["meta"]["report_date"]=report_date
        snapshot["meta"]["trading_date"]="2026-10-30"
        snapshot["meta"]["generated_at"]="2026-10-31T21:00:00+08:00"
        snapshot_path.write_text(json.dumps(snapshot,ensure_ascii=False),encoding="utf-8")
        payload.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        result=render_full(snapshot_path,payload,output)
        html=output.read_text(encoding="utf-8")
        soup=BeautifulSoup(html,"html.parser")
        assert result["editorial"]["focus_news"]==5 and result["editorial"]["market_headlines"]==10
        assert len(soup.select("#global-focus .newsitem"))==5
        assert len(soup.select("#headlines .newsitem"))==10
        assert "Synthetic focus headline 1" in soup.select_one("#global-focus").get_text()
        assert "Synthetic headline headline 10" in soup.select_one("#headlines").get_text()
        assert "Reuters" not in soup.select_one("#global-focus").get_text()
        assert len(soup.select("#calendar .econ-event"))==1
        assert len(soup.select("#earnings .earnings-accordion"))==1
        assert soup.select_one("#calendar .econ-stars").get_text(strip=True)=="★★★"
        assert soup.select_one("#earnings .earnings-stars").get_text(strip=True)=="未評星"
        assert "Synthetic CPI release" in soup.select_one("#calendar").get_text()
        assert "Synthetic Co" in soup.select_one("#earnings").get_text()
        assert "待核實" in soup.select_one("#view").get_text()
        assert "Synthetic source" in soup.select_one("#global-focus").get_text()
        if kind=="monday":
            assert len(soup.select("#last-week-calendar .econ-event"))==1
            assert len(soup.select("#last-week-earnings .earnings-accordion"))==1
            assert "Synthetic prior CPI release" in soup.select_one("#last-week-calendar").get_text()
            assert "Prior Synthetic Co" in soup.select_one("#last-week-earnings").get_text()
        else:
            assert not soup.select("#last-week-calendar")
        return result
def main():
    a=run_case("monday","2026-11-02","一")
    b=run_case("weekday","2026-11-03","二")
    print("PASS: Monday editorial renderer integration",a)
    print("PASS: weekday editorial renderer integration",b)
    print("PASS: old calendar event content cleared; incomplete sources remain pending")
if __name__=="__main__": main()
