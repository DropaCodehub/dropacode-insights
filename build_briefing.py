#!/usr/bin/env python3
"""
Generates the weekly DropaCode "Technology & Trends" briefing and writes content.json.

Runs entirely on GitHub Actions:
  1. pulls real headlines from official and trade RSS feeds,
  2. asks GitHub Models (free with a GitHub account) to select three and write the briefing,
  3. validates hard, then writes content.json.

No API key, no payment, no dependency on any laptop or browser.

Safety property worth keeping: the model may ONLY use links that came from the
feeds, so it is structurally incapable of inventing a source.
"""

import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUT = "content.json"
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
MODELS_BASE = "https://models.github.ai"
UA = "dropacode-insights/1.0 (+https://www.dropacode.com)"
LOOKBACK_DAYS = 14
MAX_CANDIDATES = 45

FEEDS = [
    # Primary / official sources first — these carry the most weight editorially.
    "https://digital-strategy.ec.europa.eu/en/rss.xml",
    "https://ec.europa.eu/commission/presscorner/api/rss?language=en",
    "https://www.enisa.europa.eu/media/news-items/news-wires/RSS",
    "https://www.eba.europa.eu/rss.xml",
    "https://www.esma.europa.eu/rss.xml",
    # Trade press for the delivery / automation / cloud side.
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.infoworld.com/index.rss",
    "https://www.zdnet.com/news/rss.xml",
    "https://feeds.feedburner.com/TheHackersNews",
]


def get(url, timeout=30, headers=None):
    req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"&[a-zA-Z#0-9]+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(raw):
    if not raw:
        return None
    raw = raw.strip()
    fmts = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]
    for f in fmts:
        try:
            d = datetime.datetime.strptime(raw.replace("GMT", "+0000"), f)
            return d.date()
        except ValueError:
            continue
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def tag(el):
    return el.tag.split("}")[-1]


def parse_feed(xml_bytes, source_hint):
    """Handles both RSS 2.0 and Atom without external dependencies."""
    out = []
    root = ET.fromstring(xml_bytes)
    channel_title = ""
    for el in root.iter():
        if tag(el) in ("channel", "feed"):
            for c in el:
                if tag(c) == "title" and c.text:
                    channel_title = strip_html(c.text)
                    break
            break

    for item in root.iter():
        if tag(item) not in ("item", "entry"):
            continue
        title = link = date_raw = summary = ""
        for c in item:
            t = tag(c)
            if t == "title" and c.text:
                title = strip_html(c.text)
            elif t == "link":
                link = (c.get("href") or c.text or "").strip()
            elif t in ("pubDate", "published", "updated", "date"):
                date_raw = date_raw or (c.text or "")
            elif t in ("description", "summary", "content"):
                summary = summary or strip_html(c.text or "")
        if title and link.startswith("https://"):
            out.append({
                "title": title[:220],
                "url": link,
                "date": parse_date(date_raw),
                "summary": summary[:400],
                "source": channel_title or source_hint,
            })
    return out


def collect():
    cutoff = datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)
    items, seen, ok_feeds = [], set(), 0
    for url in FEEDS:
        host = urllib.parse.urlsplit(url).netloc
        try:
            parsed = parse_feed(get(url), host)
        except Exception as e:
            print("  feed failed (%s): %s" % (host, str(e)[:120]))
            continue
        ok_feeds += 1
        kept = 0
        for it in parsed:
            if it["url"] in seen:
                continue
            if it["date"] and it["date"] < cutoff:
                continue
            seen.add(it["url"])
            items.append(it)
            kept += 1
        print("  %-38s %2d recent items" % (host, kept))
    print("Feeds reachable: %d/%d, candidates: %d" % (ok_feeds, len(FEEDS), len(items)))
    items.sort(key=lambda i: i["date"] or datetime.date.min, reverse=True)
    return items[:MAX_CANDIDATES]


def pick_model():
    try:
        cat = json.loads(get(MODELS_BASE + "/catalog/models", headers={
            "Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json"}))
        ids = [m.get("id") or m.get("name") for m in cat if isinstance(m, dict)]
        ids = [i for i in ids if i]
        for want in ("gpt-4.1", "gpt-4o", "llama-3.3-70b", "mistral-large"):
            for i in ids:
                if want in i.lower():
                    print("Using model:", i)
                    return i
        if ids:
            print("Using model:", ids[0])
            return ids[0]
    except Exception as e:
        print("Catalog lookup failed (%s); using default." % str(e)[:150])
    return "openai/gpt-4.1"


SYSTEM = (
    "You write the weekly 'Technology & Trends' briefing on the homepage of DropaCode, a Rome-based "
    "IT consultancy doing software development, AI automation and cloud integration. Its clients include "
    "the European Commission, the United Nations and the European Investment Bank Group, plus banking and "
    "retail enterprises. Readers are senior technology and procurement decision-makers in European public "
    "institutions and regulated enterprises. Write precise, senior, understated British English. No hype, "
    "no exclamation marks, no marketing language, no first person, and never pitch DropaCode's services. "
    "A sharp analyst note, never a company blog. Return JSON only."
)


def build_prompt(cands, today, prev):
    lines = []
    for i, c in enumerate(cands):
        lines.append("[%d] %s\n    source: %s | date: %s\n    url: %s\n    %s"
                     % (i, c["title"], c["source"], c["date"] or "unknown", c["url"], c["summary"][:240]))
    avoid = ""
    if prev:
        old = " | ".join(x.get("headline", "") for x in prev.get("items", []))
        avoid = ("\nLast week's briefing covered: %s\nAvoid repeating those stories.\n" % old)

    return (
        "Today is %s. Below are recent headlines from official EU sources and technology trade press.\n\n"
        "%s\n%s\n"
        "Choose the THREE most relevant to this audience, preferring: EU digital policy and public-sector "
        "technology; enterprise and financial-services technology; AI automation, cloud and software delivery. "
        "Prefer official and primary sources over trade press where both cover the same story.\n\n"
        "Then write a short lead: what this week's most significant development actually means for an "
        "organisation delivering technology inside regulated or public-sector environments, ending on a "
        "concrete implication.\n\n"
        "Return ONLY this JSON, no other text:\n"
        "{\n"
        '  "lead": {"title": "4-9 words, a point of view not a label", '
        '"body": ["paragraph 1, 55-80 words", "paragraph 2, 65-95 words"]},\n'
        '  "items": [{"index": <number from the list above>, "tag": "2-3 word category", '
        '"headline": "8-14 words, rewritten in our voice", "summary": "40-60 words"}, ... exactly 3 ...]\n'
        "}\n\n"
        "The 'index' must be the number in square brackets of the headline you chose. Do not invent URLs; "
        "they are taken from the list automatically. Base every factual claim only on the material above."
        % (today, "\n".join(lines), avoid)
    )


def call_model(model, prompt):
    payload = {
        "model": model,
        "temperature": 0.4,
        "max_tokens": 2000,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        MODELS_BASE + "/inference/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json",
                 "Accept": "application/vnd.github+json", "User-Agent": UA},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit("GitHub Models inference failed: HTTP %s %s"
                 % (e.code, e.read()[:800].decode("utf8", "replace")))
    return body["choices"][0]["message"]["content"]


def extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        sys.exit("Model returned no JSON:\n" + text[:1500])
    return json.loads(text[start:end + 1])


def assemble(raw, cands, today):
    def bad(m):
        sys.exit("Validation failed: %s\n%s" % (m, json.dumps(raw, indent=2)[:1500]))

    lead = raw.get("lead") or {}
    body = lead.get("body")
    if not lead.get("title") or not isinstance(body, list) or not (1 <= len(body) <= 3):
        bad("lead malformed")
    body = [p.strip() for p in body if isinstance(p, str) and p.strip()]
    if not body:
        bad("lead body empty")

    picks = raw.get("items")
    if not isinstance(picks, list) or len(picks) != 3:
        bad("expected exactly 3 items")

    items, used = [], set()
    for p in picks:
        try:
            idx = int(p.get("index"))
        except (TypeError, ValueError):
            bad("item index missing or not a number")
        if not (0 <= idx < len(cands)):
            bad("item index %s out of range" % idx)
        if idx in used:
            bad("duplicate item index %s" % idx)
        used.add(idx)
        src = cands[idx]
        for k in ("tag", "headline", "summary"):
            if not isinstance(p.get(k), str) or not p[k].strip():
                bad("item missing %r" % k)
        items.append({
            "tag": p["tag"].strip()[:28],
            "headline": p["headline"].strip(),
            "summary": p["summary"].strip(),
            "source": src["source"][:40],
            "url": src["url"],          # never model-generated
        })

    return {
        "updated": today,
        "eyebrow": "Weekly briefing",
        "heading": "Technology & Trends",
        "lead": {"title": lead["title"].strip(), "body": body},
        "items": items,
    }


def main():
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is not set.")
    today = datetime.date.today().isoformat()

    print("Collecting headlines...")
    cands = collect()
    if len(cands) < 6:
        sys.exit("Only %d candidate headlines found - refusing to publish a thin briefing." % len(cands))

    try:
        with open(OUT, "r", encoding="utf8") as f:
            prev = json.load(f)
    except Exception:
        prev = None

    text = call_model(pick_model(), build_prompt(cands, today, prev))
    data = assemble(extract_json(text), cands, today)

    with open(OUT, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("\nWrote %s for %s" % (OUT, today))
    print("Lead:", data["lead"]["title"])
    for it in data["items"]:
        print(" -", it["headline"], "(%s)" % it["source"])


if __name__ == "__main__":
    main()
