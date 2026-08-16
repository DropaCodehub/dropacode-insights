#!/usr/bin/env python3
"""
Generates the weekly DropaCode "Technology & Trends" briefing and writes content.json.

Runs on GitHub Actions. No dependency on any laptop, browser or sandbox.
Fails loudly (non-zero exit) rather than committing anything it cannot validate,
so a bad week shows up as a failed Action rather than broken content on the site.
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.anthropic.com/v1"
KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
OUT = "content.json"

if not KEY:
    sys.exit("ANTHROPIC_API_KEY is not set. Add it as a repository secret.")


def api(path, payload=None, timeout=900):
    req = urllib.request.Request(
        API + path,
        method="POST" if payload is not None else "GET",
        headers={
            "x-api-key": KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("API %s failed: HTTP %s %s" % (path, e.code, e.read()[:600].decode("utf8", "replace")))


def pick_model():
    """Choose the newest available Sonnet rather than hardcoding a model id that will age out."""
    try:
        models = api("/models?limit=100")["data"]
    except SystemExit:
        raise
    except Exception as e:
        print("Could not list models (%s); falling back." % e)
        return "claude-sonnet-4-5"
    pref = [m for m in models if "sonnet" in m.get("id", "")] or models
    pref.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    chosen = pref[0]["id"]
    print("Using model:", chosen)
    return chosen


def load_previous():
    try:
        with open(OUT, "r", encoding="utf8") as f:
            return json.load(f)
    except Exception:
        return None


PROMPT = """You write the weekly "Technology & Trends" briefing published on the homepage of DropaCode (www.dropacode.com), a Rome-based IT consultancy doing software development, AI automation and cloud integration. Its clients include the European Commission, the United Nations and the European Investment Bank Group, alongside banking and retail enterprises.

Audience: senior technology and procurement decision-makers in European public institutions and regulated enterprises.

Tone: precise, senior, understated. No hype, no exclamation marks, no marketing language. British English spelling. A sharp analyst note, never a company blog. Never pitch DropaCode's services. Never use first person.

Today's date is {today}.

Research the most relevant developments of the past 10 days across these three areas, using web search:
1. AI automation, cloud integration, custom software delivery, digital transformation.
2. EU digital policy and the public sector - EU AI Act, Digital Omnibus, Cloud and AI Development Act, Tech Sovereignty Package, digital procurement, public-sector modernisation.
3. Enterprise and financial-services technology - DORA, ICT third-party risk, core modernisation, banking technology.

Verify every figure against a primary or high-quality source: the European Commission, official regulators, Gartner/IDC/Forrester press releases, major law-firm analyses, or reputable trade press. Never invent a statistic, date or quote. Only cite URLs that appeared in your search results.

{previous}

Return ONLY a JSON object, with no commentary before or after it, in exactly this shape:

{{
  "updated": "{today}",
  "eyebrow": "Weekly briefing",
  "heading": "Technology & Trends",
  "lead": {{
    "title": "short sharp title, 4-9 words, a point of view rather than a label",
    "body": ["first paragraph, 55-80 words", "second paragraph, 65-95 words"]
  }},
  "items": [
    {{"tag": "2-3 word category", "headline": "8-14 words", "summary": "40-60 words", "source": "publisher name", "url": "https://..."}},
    {{"tag": "...", "headline": "...", "summary": "...", "source": "...", "url": "https://..."}},
    {{"tag": "...", "headline": "...", "summary": "...", "source": "...", "url": "https://..."}}
  ]
}}

The lead paragraph is the differentiator: say what this week's development actually means for an organisation delivering technology inside regulated or public-sector environments, and end on a concrete implication. The three items should span the three areas above where the week's news allows."""


def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        sys.exit("Model returned no JSON object.\n---\n" + text[:2000])
    return json.loads(text[start:end + 1])


def validate(d, today):
    def bad(msg):
        sys.exit("Validation failed: " + msg + "\n---\n" + json.dumps(d, indent=2)[:2000])

    for k in ("updated", "eyebrow", "heading", "lead", "items"):
        if k not in d:
            bad("missing key %r" % k)
    if not isinstance(d["lead"], dict) or "title" not in d["lead"]:
        bad("lead malformed")
    body = d["lead"].get("body")
    if not isinstance(body, list) or not (1 <= len(body) <= 3) or not all(isinstance(p, str) and p.strip() for p in body):
        bad("lead.body must be 1-3 non-empty paragraphs")
    if not isinstance(d["items"], list) or len(d["items"]) != 3:
        bad("expected exactly 3 items")
    for i, it in enumerate(d["items"]):
        for k in ("tag", "headline", "summary", "source", "url"):
            if not isinstance(it.get(k), str) or not it[k].strip():
                bad("item %d missing %r" % (i, k))
        if not it["url"].startswith("https://"):
            bad("item %d url is not https" % i)
    # Force the date rather than trusting the model's arithmetic.
    d["updated"] = today
    d["eyebrow"] = "Weekly briefing"
    d["heading"] = "Technology & Trends"
    return d


def main():
    today = datetime.date.today().isoformat()
    prev = load_previous()
    if prev:
        seen = " | ".join(i.get("headline", "") for i in prev.get("items", []))
        previous = ("Last week's briefing led with \"%s\" and covered: %s. Do not repeat any of these stories; "
                    "find genuinely new developments." % (prev.get("lead", {}).get("title", ""), seen))
    else:
        previous = ""

    payload = {
        "model": pick_model(),
        "max_tokens": 4000,
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}],
        "messages": [{"role": "user", "content": PROMPT.format(today=today, previous=previous)}],
    }

    resp = api("/messages", payload)
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    if not text.strip():
        sys.exit("Model returned no text.\n" + json.dumps(resp)[:2000])

    data = validate(extract_json(text), today)

    with open(OUT, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("Wrote %s for %s" % (OUT, today))
    print("Lead:", data["lead"]["title"])
    for it in data["items"]:
        print(" -", it["headline"], "(%s)" % it["source"])


if __name__ == "__main__":
    main()
