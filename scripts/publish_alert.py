#!/usr/bin/env python3
"""Publish a reviewed Shadow Watch alert into the curated incident ledger.
The GitHub workflow requires an authenticated user to initiate it.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"data/incidents.json"
ALLOWED={"Developing report","Service outage","Ransomware claim","Confirmed cyberattack"}
def norm_url(link):
 u=urlsplit(link)
 if u.scheme!="https" or not u.hostname:raise ValueError("Source must be a public HTTPS URL")
 return urlunsplit((u.scheme,u.netloc.lower(),u.path.rstrip("/"),"",""))
def main():
 title=os.environ["INCIDENT_TITLE"].strip()
 org=os.environ["INCIDENT_ORG"].strip()
 date=os.environ["INCIDENT_DATE"].strip()
 source=norm_url(os.environ["INCIDENT_SOURCE"].strip())
 classification=os.environ.get("INCIDENT_TYPE","Developing report").strip()
 summary=os.environ["INCIDENT_SUMMARY"].strip()
 if not all((title,org,summary)) or len(title)>220 or len(summary)>1200:raise ValueError("Invalid fields")
 if classification not in ALLOWED:raise ValueError("Unsupported incident classification")
 event_date=dt.date.fromisoformat(date)
 if event_date > dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=1):raise ValueError("Future event date")
 if event_date < dt.date(2026,11,1):raise ValueError("This ledger begins November 2026")
 incidents=json.loads(FILE.read_text(encoding="utf-8"))
 match=next((x for x in incidents if x.get("source")==source or any(s.get("url")==source for s in x.get("additionalSources",[]))),None)
 if not match:
  match=next((x for x in incidents if x.get("organization","").lower()==org.lower() and x.get("date")==date and title.lower()==x.get("title","").lower()),None)
 if match:
  # Don't downgrade verified evidence or overwrite authored analysis with unreviewed findings.
  links=match.setdefault("additionalSources",[])
  if source!=match.get("source") and not any(x.get("url")==source for x in links):
   links.append({"name":"Follow-up source","url":source})
  print("Updated source links for existing incident:",match["id"])
 else:
  uid=hashlib.sha256((org.lower()+"|"+date+"|"+title.lower()).encode()).hexdigest()[:12]
  match={"id":"reviewed-"+uid,"date":date,"title":title,"organization":org,
   "sector":"Other","type":classification,"severity":"medium","summary":summary,
   "source":source,"sourceName":urlsplit(source).hostname,"confidence":
    "Editorial review required" if classification=="Developing report" else
    "Status selected by publisher; verify against original source",
   "connection":"No technical connection established without supporting evidence."}
  incidents.append(match)
  print("Added incident:",match["id"])
 incidents.sort(key=lambda x:x.get("date",""),reverse=True)
 FILE.write_text(json.dumps(incidents,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
if __name__=="__main__":main()
