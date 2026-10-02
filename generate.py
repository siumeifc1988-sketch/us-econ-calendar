import re, requests, json
from datetime import datetime, timezone

def fetch_real(url):
    h={"User-Agent":"Mozilla/5.0 (compatible; US-Econ/1.0)"}
    try:
        r=requests.get(url, headers=h, timeout=20)
        if r.status_code==200 and len(r.text)>1000: return r.text
    except: pass
    for p in [
        f"https://api.allorigins.win/raw?url={url}",
        f"https://api.codetabs.com/v1/proxy?quest={url}",
        f"https://thingproxy.freeboard.io/fetch/{url}",
        f"https://corsproxy.io/?{url}",
    ]:
        try:
            r=requests.get(p, headers=h, timeout=20)
            if r.status_code==200 and len(r.text)>1000 and "BEGIN:VCALENDAR" in r.text:
                return r.text
        except: pass
    try:
        r=requests.get(f"https://api.allorigins.win/get?url={url}", headers=h, timeout=20)
        j=r.json()
        if "contents" in j and len(j["contents"])>1000: return j["contents"]
    except: pass
    # 真實鏡像，佢每日都係真 BLS
    if "bls.ics" in url:
        r=requests.get("https://raw.githubusercontent.com/jginsburgn/us-macro-calendar/main/us_macro.ics", headers=h, timeout=20)
        if r.status_code==200: return r.text
    raise Exception(url)

def parse_bls(ics_text):
    out=[]
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.S):
        summ=re.search(r"SUMMARY:(.+)", block)
        if not summ: continue
        t=summ.group(1)
        if "Employment Situation" in t: title="非農 Employment"
        elif "Consumer Price Index" in t: title="CPI"
        else: continue
        block=re.sub(r"SUMMARY:.+", f"SUMMARY:{title}", block)
        if "VALARM" not in block:
            block+="\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM"
        out.append(f"BEGIN:VEVENT{block}END:VEVENT")
    return out

events=parse_bls(fetch_real("https://www.bls.gov/schedule/news_release/bls.ics"))
html=fetch_real("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-\d{1,2})?,?\s+(\d{4})", html):
    mon={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}[m.group(1)]
    d=datetime(int(m.group(3)),mon,int(m.group(2)))
    if d < datetime.now(): continue
    dt=d.strftime("%Y%m%dT140000")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:FOMC\r\nUID:FOMC-{dt}@fed.gov\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

ics="BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//real-bls-filter//\r\nX-WR-CALNAME:美股-CPI非農議息\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n"+"\r\n".join(events)+"\r\nEND:VCALENDAR"
open("us.ics","w",encoding="utf-8").write(ics)
print(f"完成 非農:{len([e for e in events if '非農' in e])} CPI:{len([e for e in events if 'CPI' in e])} FOMC:{len([e for e in events if 'FOMC' in e])}")
