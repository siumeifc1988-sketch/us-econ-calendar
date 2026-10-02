import re, requests
from datetime import datetime, timedelta

def fetch(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.bls.gov/"}, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"fetch fail {url}: {e}")
        return ""

events=[]
stamp=datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

# BLS 官方
for url,label in [
    ("https://www.bls.gov/schedule/news_release/empsit.htm","非農"),
    ("https://www.bls.gov/schedule/news_release/cpi.htm","CPI")
]:
    html=fetch(url)
    if not html: continue
    for m in re.finditer(r"\|\s*[A-Za-z]+\s+\d{4}\s*\|\s*([A-Za-z]{3,}\.?\s*\d{1,2},\s*\d{4})", html):
        try:
            d=datetime.strptime(m.group(1).replace(".",""), "%b %d, %Y")
            if d < datetime.now()-timedelta(days=1): continue
            dt=d.strftime("%Y%m%dT083000")
            events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:{label} {d.month}/{d.day}\r\nUID:{label}-{dt}@bls.gov\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nACTION:DISPLAY\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nACTION:DISPLAY\r\nEND:VALARM\r\nEND:VEVENT")
        except: pass

# Fed 官方
html=fetch("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-(\d{1,2}))?[^\d]{0,10}(\d{4})", html):
    try:
        mon={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}[m.group(1)]
        day=int(m.group(3) or m.group(2)); y=int(m.group(4))
        d=datetime(y,mon,day)
        if d < datetime.now(): continue
        dt=d.strftime("%Y%m%dT140000")
        events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:FOMC {mon}/{day}\r\nUID:FOMC-{dt}@fed.gov\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")
    except: pass

# 保底：一定有嘢，唔會再 502
if not events:
    print("全部官方連唔上，用公式保底")
    for k in range(6):
        d=datetime.now().replace(day=1)
        m = d.month-1+k
        y = d.year + m//12
        m = m%12+1
        d=datetime(y,m,1)
        while d.weekday()!=4: # 星期五=4
            d+=timedelta(days=1)
        if d < datetime.now(): continue
        dt=d.strftime("%Y%m%dT083000")
        events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:非農 {d.month}/{d.day}\r\nUID:calc-{dt}\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

ics="BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//GitHub-Actions-官方版//\r\nX-WR-CALNAME:美股-CPI非農議息\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR"
open("us.ics","w",encoding="utf-8").write(ics)
print(f"done {len(events)} events")
