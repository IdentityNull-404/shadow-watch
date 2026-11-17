#!/usr/bin/env python3
"""Shadow Watch: news discovery with safe, deduplicated developing-event intake.
Automatically collected stories are leads, NOT verified breaches.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"data/feed.json"
LEDGER=ROOT/"data/incidents.json"
FEEDS=[
 ("BleepingComputer","https://www.bleepingcomputer.com/feed/"),
 ("The Hacker News","https://feeds.feedburner.com/TheHackersNews"),
 ("CISA","https://www.cisa.gov/cybersecurity-advisories/all.xml"),
 ("SecurityWeek","https://www.securityweek.com/feed/"),
]
ATOM="{http://www.w3.org/2005/Atom}"
TERMS=("ransomware","breach","cyberattack","cyber attack","outage","hacked","hackers",
       "malware","exploited","critical vulnerability","data theft","security incident",
       "supply chain","espionage","zero-day","phishing","compromised","ddos","extortion")
def clean(v):
 return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",str(v or "")))).strip()
def node_text(node,*names):
 for name in names:
  x=node.find(name)
  if x is not None and x.text:return x.text.strip()
 return ""
def parse_date(s):
 try:
  d=email.utils.parsedate_to_datetime(s)
 except (TypeError,ValueError):
  try:d=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
  except (TypeError,ValueError,AttributeError):return None
 if d.tzinfo is None:d=d.replace(tzinfo=dt.timezone.utc)
 return d.astimezone(dt.timezone.utc)
def canonical(link):
 try:
  u=urllib.parse.urlsplit(link)
  if u.scheme not in ("https","http") or not u.netloc:return ""
  query=urllib.parse.parse_qsl(u.query,keep_blank_values=True)
  query=[(k,v) for k,v in query if not k.lower().startswith(("utm_","fbclid","gclid"))]
  return urllib.parse.urlunsplit((u.scheme,u.netloc.lower(),u.path.rstrip("/") or "/",urllib.parse.urlencode(query),""))
 except (TypeError,ValueError):return ""
def fingerprint(title):
 s=re.sub(r"[^a-z0-9 ]"," ",title.lower())
 ignored={"the","a","an","of","and","in","on","to","for","as","with","after","new","report","reported"}
 terms=[x for x in s.split() if x not in ignored]
 return " ".join(sorted(set(terms))[:18])
def collect():
 now=dt.datetime.now(dt.timezone.utc)
 articles={}
 ok=0
 for publisher,endpoint in FEEDS:
  try:
   req=urllib.request.Request(endpoint,headers={"User-Agent":"Mozilla/5.0 (compatible; ShadowWatch/1.0; research)", "Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml"})
   with urllib.request.urlopen(req,timeout=18) as response:root=ET.fromstring(response.read(3000000))
   nodes=root.findall(".//item")
   if not nodes:nodes=root.findall(".//"+ATOM+"entry")
   ok+=1
   for item in nodes:
    title=clean(node_text(item,"title",ATOM+"title"))
    link=node_text(item,"link")
    if not link:
     anchor=item.find(ATOM+"link")
     link=anchor.attrib.get("href","") if anchor is not None else ""
    link=canonical(link)
    summary=clean(node_text(item,"description",ATOM+"summary",ATOM+"content"))
    published=parse_date(node_text(item,"pubDate",ATOM+"updated",ATOM+"published"))
    if not title or not link or not published:continue
    age=(now-published).total_seconds()/86400
    if age < -1 or age > 14:continue
    if not any(term in (title+" "+summary[:160]).lower() for term in TERMS):continue
    articles[link]={"id":"story-"+hashlib.sha256(link.encode()).hexdigest()[:16],"title":title[:200],
                    "url":link,"publisher":publisher,"date":published.isoformat(),
                    "summary":summary[:260],"status":"Developing / unverified lead"}
  except Exception as exc:print(f"{publisher} feed unavailable: {exc}")
 return articles,ok
def main():
 old={"updated_at":None,"items":[]}
 if FEED.exists():
  try:old=json.loads(FEED.read_text(encoding="utf-8"))
  except (ValueError,OSError):pass
 new,ok=collect()
 if ok==0:
  print("ERROR: all external feeds failed; preserving last successful feed")
  raise SystemExit(2)
 now=dt.datetime.now(dt.timezone.utc)
 ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
 known_urls={canonical(x.get("source","")) for x in ledger}
 for x in ledger:
  known_urls.update(canonical(s.get("url","")) for s in x.get("additionalSources",[]))
 known_titles={fingerprint(x.get("title","")) for x in ledger}
 combined={}
 for item in old.get("items",[]):
  link=canonical(item.get("url",""))
  if link:combined[link]=item
 combined.update(new)
 seen=set()
 output=[]
 for item in sorted(combined.values(),key=lambda x:x.get("date",""),reverse=True):
  date=parse_date(item.get("date",""))
  if not date or (now-date).total_seconds()/86400>14:continue
  normalized=fingerprint(item.get("title",""))
  if normalized in seen:continue
  seen.add(normalized)
  item["status"]="Developing / unverified lead"
  item["potential_duplicate"]=canonical(item["url"]) in known_urls or normalized in known_titles
  output.append(item)
 updated={"updated_at":now.isoformat(),"sources_available":ok,"sources_total":len(FEEDS),"items":output[:60]}
 FEED.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Collected {len(output[:60])} leads from {ok}/{len(FEEDS)} sources")
if __name__=="__main__":main()
