#!/usr/bin/env python3
"""Regression guard: Builder must preserve mother calendar panel shells."""
from pathlib import Path

SOURCE = Path(__file__).with_name("build_review_html.py").read_text(encoding="utf-8")

def require(fragment: str) -> None:
    if fragment not in SOURCE:
        raise AssertionError(f"Builder is missing required preservation behavior: {fragment}")

def forbid(fragment: str) -> None:
    if fragment in SOURCE:
        raise AssertionError(f"Builder still contains forbidden destructive panel operation: {fragment}")

# The three mother-owned status groups and their headings must survive the render.
require('econ_groups=panels.select(":scope > .calendar-status-group")')
require('if len(econ_groups)!=3:')
require('earnings_groups=ep.select(":scope > .calendar-status-group")')
require('if len(earnings_groups)!=3:')

# Freeze the mother prototypes before removing any rendered event-card instances.
require('template_html=str(template)')
require('earnings_template_html=str(et)')
require('BeautifulSoup(template_html,"html.parser").select_one("details.econ-event")')
require('published_template_html=str(published_template) if published_template is not None else None')
require('card=BeautifulSoup(earnings_template_html,"html.parser").select_one("details.earnings-accordion")')
require('card=BeautifulSoup(published_template_html,"html.parser").select_one("details.earnings-accordion")')
require('update_actual_results_grid(grid,x)')
require('update_published_earnings_detail_fields(details,x,clock)')
require('update_upcoming_earnings_detail_fields(')
forbid("details.clear()")
forbid("grid.clear()")

# Only direct event-card instances inside the approved list slots may be removed.
require('listing.find_all("details",class_="econ-event",recursive=False)')
require('listing.find_all("details",class_="earnings-accordion",recursive=False)')
require('old_card.decompose()')

# Reuse the existing empty-state element in place when the mother has no list slot; never fabricate a wrapper.
require('economic calendar {key} group has neither event-list nor empty-state slot')
require('empty["class"]=classes+["econ-event-list"]')
require('earnings calendar {key} group has neither accordion-list nor empty-state slot')
require('empty["class"]=classes+["earnings-accordion-list"]')

# Whole-panel clears are prohibited. Clearing a list's direct event cards is allowed.
forbid("panels.clear()")
forbid("ep.clear()")

print("PASS: economic and earnings mother panel shells are preserved; only direct event cards are replaced")
