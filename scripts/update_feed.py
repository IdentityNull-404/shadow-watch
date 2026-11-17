#!/usr/bin/env python3
"""Collect recent headlines from public cyber security RSS sources."""
import datetime as dt
import email.utils
import html
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "feed.json"
FEEDS = [
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("CISA", "https://www.cisa.gov/cybersecurity-advisories/all.xml"),
]
TERMS = ("cyber","ransomware","breach","malware","exploit","vulnerability",
         "supply chain","outage","zero-day","critical infrastructure",
         "security","espionage","phishing","compromise","patch","attack")
ATOM = "{http://www.w3.org/2005/Atom}"

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def tag(node, names):
    for name in names:
        el = node.find(name)
        if el is not None and el.text:
            return el.text.strip()
    return ""

def when(s):
    try:
        return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc)
    except Exception:
        try:
            return dt.datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(dt.timezone.utc)
        except Exception:
            return None

def collect():
    now = dt.datetime.now(dt.timezone.utc)
    articles = {}
    successes = 0
    for publisher, endpoint in FEEDS:
        try:
            request = urllib.request.Request(endpoint, headers={"User-Agent":"ShadowWatchOSINT/1.0", "Accept":"application/rss+xml,application/atom+xml,application/xml"})
            with urllib.request.urlopen(request, timeout=20) as response:
                root = ET.fromstring(response.read(4_000_000))
            successes += 1
            nodes = root.findall(".//item") or root.findall(".//" + ATOM + "entry")
            for entry in nodes:
                title = clean(tag(entry, ["title",ATOM+"title"]))
                link = tag(entry, ["link"])
                if not link:
                    element = entry.find(ATOM+"link")
                    link = element.attrib.get("href","") if element is not None else ""
                summary = clean(tag(entry, ["description",ATOM+"summary"]))
                date = when(tag(entry, ["pubDate", ATOM+"updated", ATOM+"published"]))
                if not title or not link.startswith("https://") or not date:
                    continue
                if not any(word in (title+" "+summary).lower() for word in TERMS):
                    continue
                if not (-1 <= (now-date).total_seconds()/86400 <= 21):
                    continue
                articles[link] = {"title":title[:220],"url":link,"publisher":publisher,
                                  "date":date.isoformat(),"summary":summary[:240]}
        except Exception as exc:
            print(f"{publisher}: {exc}")
    return articles, successes

def main():
    previous = {"updated_at":None,"items":[]}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError,OSError):
            pass
    new, successes = collect()
    if not successes:
        print("No sources reachable; preserving previous successful snapshot")
        return
    now = dt.datetime.now(dt.timezone.utc)
    merged = {item["url"]:item for item in previous.get("items",[]) if item.get("url")}
    merged.update(new)
    valid = []
    for item in merged.values():
        date = when(item.get("date",""))
        if date and -1 <= (now-date).total_seconds()/86400 <= 21:
            valid.append(item)
    valid.sort(key=lambda x:x["date"], reverse=True)
    payload = {"updated_at":now.isoformat(),"items":valid[:60]}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {len(payload['items'])} headlines from {successes} reachable sources")

if __name__ == "__main__":
    main()
