import re, requests
from datetime import datetime, timedelta

def fetch(url):
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.bls.gov/"}, timeout=20)
    r.raise_for_status()
    return r.text

events=[]
stamp=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

# 官方 BLS - 非農 / CPI
for url,label in [
    ("https://www.bls.gov/schedule/news_release/empsit.htm","非農"),
    ("https://www.bls.gov/schedule/news_release/cpi.htm","CPI")
]:
    html=fetch(url)
    for m in re.finditer(r"\|\s*[A-Za-z]+\s+\d{4}\s*\|\s*([A-Za-z]{3,}\.?\s*\d{1,2},\s*\d{4})", html):
        d=datetime.strptime(m.group(1).replace(".",""), "%b %d, %Y")
        if d < datetime.now()-timedelta(days=1): continue
        dt=d.strftime("%Y%m%dT083000")
        events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:{label} {d.month}/{d.day}\r\nUID:{label}-{dt}@bls.gov\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

# 官方 Fed - FOMC，唔寫死
html=fetch("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-(\d{1,2}))?[^\d]{0,10}(\d{4})", html):
    mon={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}[m.group(1)]
    day=int(m.group(3) or m.group(2)); y=int(m.group(4))
    d=datetime(y,mon,day)
    if d < datetime.now(): continue
    dt=d.strftime(f"%Y%m%dT140000")
    events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:FOMC {mon}/{day}\r\nUID:FOMC-{dt}@fed.gov\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

ics=f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//GitHub-Actions-官方版//\r\nX-WR-CALNAME:美股-CPI非農議息\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n{chr(13).join(events)}\r\nEND:VCALENDAR"
open("us.ics","w").write(ics)
