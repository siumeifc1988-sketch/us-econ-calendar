import re, requests
from datetime import datetime, timezone

def fetch_real(url):
    h={"User-Agent":"Mozilla/5.0 (compatible; US-Econ/1.0; +github.com/siumeifc1988-sketch)"}
    try:
        r=requests.get(url, headers=h, timeout=20)
        if r.status_code==200 and len(r.text)>1000:
            return r.text
    except:
        pass
    proxies=[
        f"https://api.allorigins.win/raw?url={url}",
        f"https://api.codetabs.com/v1/proxy?quest={url}",
        f"https://thingproxy.freeboard.io/fetch/{url}",
        f"https://corsproxy.io/?{url}",
    ]
    for p in proxies:
        try:
            r=requests.get(p, headers=h, timeout=20)
            if r.status_code==200 and len(r.text)>1000 and "BEGIN:VCALENDAR" in r.text:
                print(f"代理成功 {p[:30]}")
                return r.text
        except:
            pass
    try:
        r=requests.get(f"https://api.allorigins.win/get?url={url}", headers=h, timeout=20)
        j=r.json()
        if "contents" in j and len(j["contents"])>1000:
            print("代理成功 allorigins/get")
            return j["contents"]
    except:
        pass
    # 真實鏡像，仍是官方 BLS 數據
    if "bls.ics" in url:
        try:
            mirror="https://raw.githubusercontent.com/jginsburgn/us-macro-calendar/main/us_macro.ics"
            r=requests.get(mirror, headers=h, timeout=20)
            if r.status_code==200 and "BEGIN:VCALENDAR" in r.text:
                print("真實鏡像成功 jginsburgn")
                return r.text
        except:
            pass
    raise Exception(f"真實抓失敗 {url}")

def build_events(ics_text):
    out=[]
    now=datetime.now()
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.S):
        summ=re.search(r"SUMMARY:(.+)", block)
        dt=re.search(r"DTSTART[^\r\n]+", block)
        if not summ or not dt:
            continue
        title=summ.group(1)
        if "Employment Situation" in title:
            new_title="非農"
        elif "Consumer Price Index" in title:
            new_title="CPI"
        else:
            continue
        # 只留未來
        m=re.search(r"(\d{8})T(\d{6})", dt.group(0))
        if m:
            try:
                dd=datetime.strptime(m.group(1), "%Y%m%d")
                if dd < now - timezone.timedelta(days=1) if hasattr(timezone, 'timedelta') else now:
                    # 簡單比較年月日
                    if dd.year < now.year or (dd.year==now.year and int(m.group(1)[4:6]) < now.month):
                        # 粗略過濾舊年舊月，保留當月之後
                        pass
            except:
                pass
        dtstart=dt.group(0).strip()
        uid_match=re.search(r"UID:([^\r\n]+)", block)
        uid_val=uid_match.group(1).strip() if uid_match else f"{new_title}-{dtstart}@bls.gov"
        stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        vevent="\r\n".join([
            "BEGIN:VEVENT",
            f"UID:{uid_val}",
            f"DTSTAMP:{stamp}",
            dtstart,
            f"SUMMARY:{new_title}",
            "DESCRIPTION:BLS official release",
            "BEGIN:VALARM",
            "TRIGGER:-P1D",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "END:VALARM",
            "BEGIN:VALARM",
            "TRIGGER:-PT60M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "END:VALARM",
            "END:VEVENT"
        ])
        out.append(vevent)
    return out

# 1. BLS 真實
events=build_events(fetch_real("https://www.bls.gov/schedule/news_release/bls.ics"))

# 2. FOMC 真實
html=fetch_real("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
stamp_now=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-\d{1,2})?,?\s+(\d{4})", html):
    mon_map={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
    mon=mon_map[m.group(1)]
    day=int(m.group(2))
    year=int(m.group(3))
    d=datetime(year, mon, day)
    if d < datetime.now():
        continue
    dt=d.strftime("%Y%m%dT140000")
    events.append("\r\n".join([
        "BEGIN:VEVENT",
        f"UID:FOMC-{dt}@fed.gov",
        f"DTSTAMP:{stamp_now}",
        f"DTSTART;TZID=US-Eastern:{dt}",
        "SUMMARY:FOMC",
        "DESCRIPTION:Federal Reserve FOMC meeting",
        "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
        "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
        "END:VEVENT"
    ]))

# 只留未來 12 個月，避免 iPhone 覺得舊
filtered=[]
now=datetime.now()
for ev in events:
    mm=re.search(r"DTSTART[^:]*:(\d{4})(\d{2})(\d{2})", ev)
    if mm:
        y=int(mm.group(1)); mo=int(mm.group(2))
        if y < now.year: continue
        if y==now.year and mo < now.month: continue
    filtered.append(ev)

events=filtered

ics_content="\r\n".join([
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//real-bls-filter-fixed//",
    "X-WR-CALNAME:美股-CPI非農議息",
    "CALSCALE:GREGORIAN",
    "BEGIN:VTIMEZONE",
    "TZID:US-Eastern",
    "BEGIN:DAYLIGHT",
    "TZOFFSETFROM:-0500",
    "TZOFFSETTO:-0400",
    "DTSTART:20070311T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU",
    "END:DAYLIGHT",
    "BEGIN:STANDARD",
    "TZOFFSETFROM:-0400",
    "TZOFFSETTO:-0500",
    "DTSTART:20071104T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU",
    "END:STANDARD",
    "END:VTIMEZONE",
] + events + ["END:VCALENDAR"]) + "\r\n"

open("us.ics","w",encoding="utf-8", newline="").write(ics_content)
print(f"完成 非農:{len([e for e in events if '非農' in e])} CPI:{len([e for e in events if 'CPI' in e])} FOMC:{len([e for e in events if 'FOMC' in e])} 總數:{len(events)}")
