#!/usr/bin/env python3
"""Run bootstrap with a safe GitHub artifact redirect handler.

GitHub redirects artifact ZIP downloads to a signed object-storage URL.
The Authorization header must not be forwarded to that different host.
"""
import runpy
import sys
import urllib.parse
import urllib.request
from pathlib import Path

class StripAuthOnCrossHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            old_host = urllib.parse.urlparse(req.full_url).netloc
            new_host = urllib.parse.urlparse(newurl).netloc
            if old_host != new_host:
                for name in ("Authorization", "Cookie"):
                    redirected.remove_header(name)
                    redirected.remove_header(name.lower())
        return redirected

_original_urlopen = urllib.request.urlopen

def safe_urlopen(url, *args, **kwargs):
    if isinstance(url, urllib.request.Request) and "/actions/artifacts/" in url.full_url and url.full_url.endswith("/zip"):
        opener = urllib.request.build_opener(StripAuthOnCrossHostRedirect)
        return opener.open(url, *args, **kwargs)
    return _original_urlopen(url, *args, **kwargs)

urllib.request.urlopen = safe_urlopen
script = Path(__file__).with_name("tac_chart3_bootstrap.py")
sys.argv[0] = str(script)
runpy.run_path(str(script), run_name="__main__")
