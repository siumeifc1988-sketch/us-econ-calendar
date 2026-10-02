import re, requests
from datetime import datetime, timedelta, timezone
try:
    from bs4 import BeautifulSoup
    HAS_BS=True
except:
    HAS_BS=False

def fetch(url):
    headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.bls.gov/"}
    try:
        r=requests.get(url, headers=headers, timeout=20)
        if r.status_code==200 and len(r.text)>1000:
            return r.text
    except: pass
    for tmpl in ["https://api.allorigins.win/raw?url={url}","https://api.codetabs.com/v1/proxy?quest={url}"]:
        try:
            r=requests.get(tmpl.format(url=url), headers=headers, timeout=20)
            if r.status_code==200 and len(r.text)>1000:
                print(f"代理成功 {url[-15:]}")
                return r.text
        except: pass
    return ""

def parse_bls(html, label):
    out=[]
    if not html: return out
    # 抓所有 Oct. 12, 2025 呢類日期
    for m in re.finditer(r"([A-Z][a-z]{2,}\.?\s+\d{1,2},\s+\d{4})", html):
        try:
            d=datetime.strptime(m.group(1).replace(".",""), "%b %d, %Y")
        except:
            try: d=datetime.strptime(m.group(1).replace(".",""), "%B %d, %Y")
            except: continue
        if d.replace(tzinfo=None) < datetime.now()-timedelta(days=1): continue
        # 淨係要未來一年
        if d.year > datetime.now().year+1: continue
        out.append((d,label))
    return out

events=[]
stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
all_dates=[]

for url,label in [("https://www.bls.gov/schedule/news_release/empsit.htm","非農"),("https://www.bls.gov/schedule/news_release/cpi.htm","CPI")]:
    all_dates+=parse_bls(fetch(url), label)

# FOMC
html=fetch("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
if html:
    for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-(\d{1,2}))?\s*,?\s*(\d{4})", html):
        try:
            mon={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}[m.group(1)]
            day=int(m.group(3) or m.group(2)); y=int(m.group(4))
            d=datetime(y,mon,day)
            if d.replace(tzinfo=None) < datetime.now(): continue
            all_dates.append((d,"FOMC"))
        except: pass

# 轉做 VEVENT
for d,label in all_dates:
    if label=="FOMC": dt=d.strftime("%Y%m%dT140000")
    else: dt=d.strftime("%Y%m%dT083000")
    events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:{label} {d.month}/{d.day}\r\nUID:{label}-{dt}\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

# 保底：咩都抓唔到都三樣齊
if len([e for e in events if "CPI" in e])<3:
    for k in range(6):
        now=datetime.now()
        y=now.year+(now.month-1+k)//12; m=(now.month-1+k)%12+1
        d=datetime(y,m,12) # CPI 固定12號前後
        if d<now: continue
        dt=d.strftime("%Y%m%dT083000")
        events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:CPI {m}/{d.day} (保底)\r\nUID:CPI-{dt}\r\nEND:VEVENT")

if len([e for e in events if "FOMC" in e])<3:
    fomc_fallback=[(2026,1,28),(2026,3,18),(2026,4,29),(2026,6,17),(2026,7,29),(2026,9,16),(2026,10,28),(2026,12,9)]
    for y,m,d in fomc_fallback:
        dd=datetime(y,m,d)
        if dd<datetime.now(): continue
        dt=dd.strftime("%Y%m%dT140000")
        events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:FOMC {m}/{d} (保底)\r\nUID:FOMC-{dt}\r\nEND:VEVENT")

ics="BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//full-auto//\r\nX-WR-CALNAME:美股-CPI非農議息\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n"+"\r\n".join(events)+"\r\nEND:VCALENDAR"
open("us.ics","w",encoding="utf-8").write(ics)
print(f"done 非農:{len([e for e in events if '非農' in e])} CPI:{len([e for e in events if 'CPI' in e])} FOMC:{len([e for e in events if 'FOMC' in e])}")
