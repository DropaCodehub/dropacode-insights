#!/usr/bin/env python3
"""
Builds the weekly DropaCode "Technology & Trends" briefing and writes content.json.

Runs entirely on GitHub Actions, free, forever:
  1. pulls headlines from official EU and technology trade feeds,
  2. scores them against DropaCode's audience using an explicit keyword model,
  3. picks the three strongest, from three different sources,
  4. writes content.json.

No AI service, no API key, no payment, and no dependency on any laptop or browser.
Every headline, summary and link comes verbatim from the source feed, so nothing
here can be fabricated.
"""

import datetime
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUT = "content.json"
UA = "dropacode-insights/1.0 (+https://www.dropacode.com)"
LOOKBACK_DAYS = 14

# weight, tag shown on the card, matching terms
CATEGORIES = [
    (5.0, "EU Regulation", [
        "ai act", "digital omnibus", "digital services act", "digital markets act", "data act",
        "gdpr", "nis2", "nis 2", "cyber resilience act", "regulation", "directive", "compliance",
        "enforcement", "supervisory", "european commission", "brussels",
    ]),
    (4.5, "Cloud & Sovereignty", [
        "sovereign", "sovereignty", "cloud", "data centre", "data center", "hyperscaler",
        "infrastructure", "migration", "on-premise", "chips act",
    ]),
    (4.0, "Finance & Risk", [
        "dora", "operational resilience", "ict risk", "third-party risk", "bank", "banking",
        "financial", "payments", "fintech", "esma", "eba", "insurer", "capital markets",
    ]),
    (3.5, "AI & Automation", [
        "artificial intelligence", " ai ", "ai-", "machine learning", "agentic", "ai agent",
        "automation", "large language model", "llm", "generative", "copilot", "model",
    ]),
    (3.0, "Public Sector", [
        "procurement", "public sector", "public administration", "government", "member state",
        "digital transformation", "e-government", "interoperability",
    ]),
    (2.0, "Security", [
        "cybersecurity", "breach", "vulnerability", "ransomware", "threat", "enisa", "incident",
    ]),
]

# Official / primary sources are worth more than trade press to this audience.
FEEDS = [
    ("https://digital-strategy.ec.europa.eu/en/rss.xml", "European Commission", 4.0),
    ("https://ec.europa.eu/commission/presscorner/api/rss?language=en", "European Commission", 4.0),
    ("https://www.eba.europa.eu/rss.xml", "European Banking Authority", 3.5),
    ("https://www.esma.europa.eu/rss.xml", "ESMA", 3.5),
    ("https://www.eiopa.europa.eu/rss.xml", "EIOPA", 3.5),
    ("https://www.enisa.europa.eu/media/news-items/RSS", "ENISA", 3.0),
    # EU policy trade press - high volume, well matched to this audience.
    ("https://www.euractiv.com/sections/digital/feed/", "Euractiv", 2.0),
    ("https://www.euractiv.com/sections/economy-jobs/feed/", "Euractiv", 1.5),
    # Enterprise technology press - the delivery, cloud and automation side.
    ("https://www.computerweekly.com/rss/All-Computer-Weekly-content.xml", "Computer Weekly", 1.5),
    ("https://www.theregister.com/headlines.atom", "The Register", 1.0),
    ("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica", 0.5),
    ("https://techcrunch.com/feed/", "TechCrunch", 0.0),
    ("https://www.theverge.com/rss/index.xml", "The Verge", 0.0),
    ("https://feeds.feedburner.com/TheHackersNews", "The Hacker News", 0.5),
    ("https://www.bleepingcomputer.com/feed/", "BleepingComputer", 0.5),
]

NOISE = [
    # consumer / entertainment
    "deal", "discount", "best laptop", "review:", "iphone", "android phone", "gaming",
    "streaming", "netflix", "tv show", "trailer", "smartwatch", "headphones", "black friday",
    # events and housekeeping - never worth a homepage slot
    "join the", "forum", "webinar", "conference", "summit", "workshop", "save the date",
    "call for applications", "call for expression", "award", "prize", "vacancy",
    "job opening", "newsletter", "podcast", "registration is open", "anniversary",
    # roundups and procedural filler that read badly as a headline
    "daily news", "weekly roundup", "midday express", "board of appeal", "dismisses appeal",
    "agenda", "minutes of", "speech by", "statement by the president",
]

# A story must clear this to be publishable at all. Better an unchanged week
# than three weak cards on the homepage.
MIN_SCORE = 10.0


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(s):
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&[a-zA-Z#0-9]+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(raw):
    if not raw:
        return None
    raw = raw.strip().replace("GMT", "+0000")
    for f in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
              "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(raw, f).date()
        except ValueError:
            pass
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def tag_of(el):
    return el.tag.split("}")[-1]


def parse_feed(xml_bytes, source, bonus):
    out = []
    root = ET.fromstring(xml_bytes)
    for item in root.iter():
        if tag_of(item) not in ("item", "entry"):
            continue
        title = link = date_raw = summary = ""
        for c in item:
            t = tag_of(c)
            if t == "title" and c.text:
                title = clean(c.text)
            elif t == "link":
                link = link or (c.get("href") or c.text or "").strip()
            elif t in ("pubDate", "published", "updated", "date"):
                date_raw = date_raw or (c.text or "")
            elif t in ("description", "summary", "content"):
                summary = summary or clean(c.text or "")
        if title and link.startswith("https://"):
            out.append({"title": title[:200], "url": link, "date": parse_date(date_raw),
                        "summary": summary, "source": source, "bonus": bonus})
    return out


def score(item):
    hay = (" " + item["title"] + " " + item["summary"][:400] + " ").lower()
    if any(n in hay for n in NOISE):
        return 0.0, None
    total, matched = 0.0, []
    for weight, tag, terms in CATEGORIES:
        hits = sum(1 for t in terms if t in hay)
        if hits:
            total += weight + (hits - 1) * 0.4
            matched.append((hits, weight, tag))
    if not matched:
        return 0.0, None
    # Label by what the story is mostly about (most term hits), not by whichever
    # category happens to carry the biggest weight. This is what mis-tagged a
    # ransomware story as "Cloud & Sovereignty" on one keyword.
    matched.sort(key=lambda m: (m[0], m[1]), reverse=True)
    best = matched[0][2]
    # Pure security stories are not what this audience comes to the page for;
    # they only earn a slot when they also touch regulation, finance or cloud.
    if best == "Security" and len(matched) == 1:
        return 0.0, None
    total += item["bonus"]
    if item["date"]:
        age = (datetime.date.today() - item["date"]).days
        total += max(0.0, 3.0 - age * 0.25)      # freshness matters, gently
    return total, best


def trim_words(text, lo=38, hi=58):
    words = text.split()
    if len(words) <= hi:
        return text.rstrip(" .,;:") + ("." if text and not text.endswith(".") else "")
    cut = " ".join(words[:hi])
    dot = cut.rfind(".")
    if dot > len(" ".join(words[:lo])):
        return cut[:dot + 1]
    return cut.rstrip(" .,;:") + "…"


def collect():
    cutoff = datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)
    items, seen, reachable = [], set(), 0
    for url, source, bonus in FEEDS:
        host = urllib.parse.urlsplit(url).netloc
        try:
            parsed = parse_feed(get(url), source, bonus)
        except Exception as e:
            print("  feed failed (%s): %s" % (host, str(e)[:110]))
            continue
        reachable += 1
        kept = 0
        for it in parsed:
            if it["url"] in seen or (it["date"] and it["date"] < cutoff):
                continue
            seen.add(it["url"])
            items.append(it)
            kept += 1
        print("  %-34s %-28s %2d recent" % (host, source, kept))
    print("Feeds reachable: %d/%d | candidates: %d" % (reachable, len(FEEDS), len(items)))
    return items


def select(items, n=3, exclude=()):
    """Rank on merit, skip anything already on the page, then cap each source at two.

    Excluding what is currently published is what keeps the section moving. The
    official regulators publish slowly, so without this the same three strong
    stories win every run and the page looks frozen even though it is updating.
    """
    scored = []
    for it in items:
        if it["url"] in exclude:
            continue
        s, tag = score(it)
        if s >= MIN_SCORE and tag:
            scored.append((s, tag, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    print("Stories clearing the quality bar (%.1f): %d" % (MIN_SCORE, len(scored)))

    chosen, per_source = [], {}
    for s, tag, it in scored:
        if per_source.get(it["source"], 0) >= 2:
            continue
        per_source[it["source"]] = per_source.get(it["source"], 0) + 1
        chosen.append((s, tag, it))
        if len(chosen) == n:
            break
    return chosen


def main():
    today = datetime.date.today().isoformat()

    try:
        with open(OUT, "r", encoding="utf8") as f:
            existing = json.load(f)
    except Exception:
        existing = None
    on_page = {i.get("url") for i in (existing or {}).get("items", [])}

    print("Collecting headlines...")
    candidates = collect()

    # Quality first: take the three best stories on merit, whatever they are.
    picks = select(candidates)
    if len(picks) < 3:
        print("Only %d stories cleared the bar - leaving the existing briefing in place." % len(picks))
        return

    # Freshness second: if that is exactly what is already on the page, swap the
    # weakest slot for the best story not currently shown. The strongest item
    # stays put; the page still visibly moves. Forcing all three to rotate is
    # what dragged filler onto the homepage.
    if on_page and {p[2]["url"] for p in picks} == on_page:
        fresh = select(candidates, n=1, exclude=on_page)
        if fresh:
            picks[-1] = fresh[0]
            print("Top three unchanged - rotating the weakest slot for: %s" % fresh[0][2]["title"][:70])
        else:
            print("Nothing new cleared the bar; leaving the current briefing in place.")
            return

    data = {
        "updated": today,
        "eyebrow": "Latest briefing",
        "heading": "Technology & Trends",
        "items": [{
            "tag": tag,
            "headline": it["title"],
            "summary": trim_words(it["summary"]) or it["title"],
            "source": it["source"],
            "url": it["url"],
        } for _, tag, it in picks],
    }

    # Only claim a new date when the stories genuinely changed. Running more often
    # than the news moves would otherwise stamp "updated today" over last week's
    # cards, which is worse than showing an honest older date.
    if existing and [i.get("url") for i in existing.get("items", [])] == [i["url"] for i in data["items"]]:
        print("Same three stories as the current briefing - leaving it untouched (still dated %s)."
              % existing.get("updated"))
        return

    with open(OUT, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("\nWrote %s for %s" % (OUT, today))
    for s, tag, it in picks:
        print("  [%.1f] %-20s %s (%s)" % (s, tag, it["title"][:70], it["source"]))


if __name__ == "__main__":
    main()
