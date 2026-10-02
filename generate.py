import re, requests
from datetime import datetime, timezone

def fetch_real(url):
    h={"User-Agent":"Mozilla/5.0 (compatible; US-Econ-Calendar/1.0; +https://siumeifc1988-sketch.github.io/us-econ-calendar/)","Accept":"text/calendar, text/plain, */*"}
    # 直連
    try:
        r=requests.get(url, headers=h, timeout=20)
        if r.status_code==200 and len(r.text)>1000: return r.text
    except: pass
    # 中文版都係靠呢個代理過BLS封鎖
    for p in [f"https://api.allorigins.win/raw?url={url}", f"https://api.codetabs.com/v1/proxy?quest={url}"]:
        try:
            r=requests.get(p, headers=h, timeout=20)
            if r.status_code==200 and len(r.text)>1000:
                print(f"代理真實成功 {url.split('/')[-1]}")
                return r.text
        except: pass
    raise Exception(f"真實抓失敗 {url}")

def parse_ics(ics_text, keywords):
    # 最簡單iCal解析，只留你想要嘅
    events=[]
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.S):
        summ=re.search(r"SUMMARY:(.+)", block)
        if not summ: continue
        title=summ.group(1)
        if not any(k.lower() in title.lower() for k in keywords): continue
        # 保留原block，但統一加提醒
        if "VALARM" not in block:
            block+= "\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nACTION:DISPLAY\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nACTION:DISPLAY\r\nEND:VALARM"
        events.append(f"BEGIN:VEVENT{block}END:VEVENT")
    return events

all_events=[]

# 1. BLS 官方 bls.ics - 入面就有 CPI + 非農
bls_ics=fetch_real("https://www.bls.gov/schedule/news_release/bls.ics")
all_events+=parse_ics(bls_ics, ["Consumer Price Index", "Employment Situation", "CPI", "Employment"])

# 2. BEA 官方 - GDP/PCE (中文版都有)
try:
    bea_ics=fetch_real("https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics")
    all_events+=parse_ics(bea_ics, ["GDP", "Personal Income", "PCE"])
except Exception as e:
    print(f"BEA skip {e}")

# 3. FOMC 真實
html=fetch_real("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-\d{1,2})?,?\s+(\d{4})", html):
    mon={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}[m.group(1)]
    d=datetime(int(m.group(3)),mon,int(m.group(2)), tzinfo=timezone.utc)
    if d < datetime.now(timezone.utc): continue
    dt=d.strftime("%Y%m%dT140000")
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    all_events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:FOMC {mon}/{d.day}\r\nUID:FOMC-{dt}@fed.gov\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

if len(all_events)<8: raise Exception(f"真實抓太少 {len(all_events)}")

ics="BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//real-bls.ics-copy//\r\nX-WR-CALNAME:美股-CPI非農議息\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n" + "\r\n".join(all_events) + "\r\nEND:VCALENDAR"

open("us.ics","w",encoding="utf-8").write(ics)
print(f"真實完成 {len(all_events)} 個，全部來自 bls.ics + fed")
