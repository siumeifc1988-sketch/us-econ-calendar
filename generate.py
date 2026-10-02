
import re, requests
from datetime import datetime, timezone

def fetch_real(url):
    h={"User-Agent":"Mozilla/5.0 (compatible; US-Econ/1.0; contact github.com/siumeifc1988-sketch/us-econ-calendar)"}
    try:
        r=requests.get(url, headers=h, timeout=20)
        if r.status_code==200 and len(r.text)>1000:
            return r.text
    except:
        pass
    for proxy in [
        f"https://api.allorigins.win/raw?url={url}",
        f"https://api.codetabs.com/v1/proxy?quest={url}",
        f"https://thingproxy.freeboard.io/fetch/{url}",
        f"https://corsproxy.io/?{url}",
        f"https://api.allorigins.win/get?url={url}",
    ]:
        try:
            r=requests.get(proxy, headers=h, timeout=25)
            txt = r.text
            if '"contents"' in txt[:200]:
                try:
                    j=r.json()
                    txt=j.get("contents","")
                except:
                    pass
            if len(txt)>1000 and ("FOMC" in txt or "BEGIN:VCALENDAR" in txt or "fomc" in txt.lower()):
                return txt
        except:
            continue
    if "bls.ics" in url:
        try:
            mirror="https://raw.githubusercontent.com/jginsburgn/us-macro-calendar/main/us_macro.ics"
            r=requests.get(mirror, headers=h, timeout=20)
            if r.status_code==200 and "BEGIN:VCALENDAR" in r.text:
                return r.text
        except:
            pass
    raise Exception(f"fetch fail {url}")

def build_bls_events(ics_text):
    out=[]
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.S):
        summ=re.search(r"SUMMARY:(.+)", block)
        dt=re.search(r"DTSTART[^\r\n]+", block)
        desc=re.search(r"DESCRIPTION:(.+)", block)
        if not summ or not dt:
            continue
        title=summ.group(1)
        orig_desc = desc.group(1).strip() if desc else ""
        orig_desc = orig_desc.replace("\\n", " | ").replace("\\,", ",")[:200]
        if "Employment Situation" in title:
            new_title="非農"
            detail = f"【美股重磅】非農就業數據 (Employment Situation)\\n公布: 美東08:30 香港20:30/21:30\\n來源: BLS官方 https://www.bls.gov/schedule/news_release/bls.ics\\n原標: {title}\\n{orig_desc}\\n影響: 高 - 影響Fed利率預期 美股美元黃金波動\\n備註: 每月第一個星期五"
        elif "Consumer Price Index" in title:
            new_title="CPI"
            detail = f"【美股重磅】CPI消費者物價指數\\n公布: 美東08:30 香港20:30/21:30\\n來源: BLS官方 https://www.bls.gov/schedule/news_release/bls.ics\\n原標: {title}\\n{orig_desc}\\n影響: 高 - 通脹核心指標\\n備註: 每月中旬 Core CPI更重要"
        else:
            continue
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
            f"DESCRIPTION:{detail}",
            "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
            "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
            "END:VEVENT"
        ])
        out.append(vevent)
    return out

def parse_fomc_live(html):
    events=[]
    mon_map={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
    for year in [2026, 2027, 2028]:
        m_year = re.search(rf"{year} FOMC Meetings(.*?)(?:####|\Z)", html, re.S|re.I)
        if not m_year:
            continue
        block = m_year.group(1)
        for m in re.finditer(r'(January|February|March|April|May|June|July|August|September|October|November|December)[\*\s,]*\s*(\d{1,2})-(\d{1,2})', block, re.I):
            mon_name=m.group(1).capitalize()
            start_day=int(m.group(2))
            end_day=int(m.group(3))
            mon_num=mon_map.get(mon_name)
            if not mon_num:
                continue
            try:
                d=datetime(year, mon_num, end_day)
                if d < datetime.now():
                    continue
                dt=d.strftime("%Y%m%dT140000")
                stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                detail = f"【美股重磅】FOMC議息決定日\\n會議: {mon_name} {start_day}-{end_day}, {year} 決定日{end_day}\\n時間: 美東14:00 香港次日02:00 記者會14:30\\n來源: Fed官方 https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm\\n影響: 最高 - 利率決定引爆美股\\n備註: 每年8次 *有點陣圖"
                events.append("\r\n".join([
                    "BEGIN:VEVENT",
                    f"UID:FOMC-{dt}@fed.gov",
                    f"DTSTAMP:{stamp}",
                    f"DTSTART;TZID=US-Eastern:{dt}",
                    "SUMMARY:FOMC",
                    f"DESCRIPTION:{detail}",
                    "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "END:VEVENT"
                ]))
            except:
                continue
    return events

def parse_fomc_from_jginsburgn():
    try:
        url="https://raw.githubusercontent.com/jginsburgn/us-macro-calendar/main/us_macro.ics"
        r=requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        if r.status_code!=200:
            return []
        ics=r.text
        out=[]
        for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S|re.I):
            if "FOMC" not in block and "Federal Reserve" not in block:
                continue
            dt=re.search(r"DTSTART[^:]*:(\d{8})", block)
            if not dt:
                continue
            ymd=dt.group(1)
            y=int(ymd[:4]); mo=int(ymd[4:6]); da=int(ymd[6:8])
            try:
                d=datetime(y,mo,da)
                if d < datetime.now():
                    continue
                dt_str=d.strftime("%Y%m%dT140000")
                stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                detail = f"【美股重磅】FOMC議息\\n時間: 美東14:00 香港次日02:00\\n來源: jginsburgn同步Fed官方\\n影響: 最高"
                out.append("\r\n".join([
                    "BEGIN:VEVENT",
                    f"UID:FOMC-{dt_str}@fed.gov",
                    f"DTSTAMP:{stamp}",
                    f"DTSTART;TZID=US-Eastern:{dt_str}",
                    "SUMMARY:FOMC",
                    f"DESCRIPTION:{detail}",
                    "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "END:VEVENT"
                ]))
            except:
                continue
        return out
    except:
        return []

print("抓 BLS...")
bls_ics = fetch_real("https://www.bls.gov/schedule/news_release/bls.ics")
events = build_bls_events(bls_ics)
print(f"BLS: {len(events)}")

print("抓 FOMC...")
fomc_events=[]
try:
    fed_html = fetch_real("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    fomc_events = parse_fomc_live(fed_html)
    print(f"FOMC live: {len(fomc_events)}")
except Exception as e:
    print(f"FOMC fail {e}")

if len(fomc_events) < 2:
    fomc_events = parse_fomc_from_jginsburgn()
    print(f"FOMC backup: {len(fomc_events)}")

if len(fomc_events) < 2:
    official = [
        ("20261027T140000","October 27-28, 2026"),
        ("20261208T140000","December 8-9, 2026"),
        ("20270126T140000","January 26-27, 2027"),
        ("20270316T140000","March 16-17, 2027"),
        ("20270427T140000","April 27-28, 2027"),
        ("20270615T140000","June 15-16, 2027"),
        ("20270727T140000","July 27-28, 2027"),
        ("20270914T140000","September 14-15, 2027"),
        ("20271026T140000","October 26-27, 2027"),
        ("20271207T140000","December 7-8, 2027"),
    ]
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for dt, meet in official:
        y=int(dt[:4]); mo=int(dt[4:6]); da=int(dt[6:8])
        if datetime(y,mo,da) < datetime.now():
            continue
        detail = f"【美股重磅】FOMC議息決定日\\n會議: {meet}\\n時間: 美東14:00 香港次日02:00 記者會14:30\\n來源: Fed官方表\\n影響: 最高"
        fomc_events.append("\r\n".join([
            "BEGIN:VEVENT",
            f"UID:FOMC-{dt}@fed.gov",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=US-Eastern:{dt}",
            "SUMMARY:FOMC",
            f"DESCRIPTION:{detail}",
            "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
            "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
            "END:VEVENT"
        ]))

events.extend(fomc_events)
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
    "PRODID:-//real-bls-live-subscription//",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:美股-CPI非農議息",
    "X-PUBLISHED-TTL:PT12H",
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
print(f"完成 非農:{len([e for e in events if '非農' in e])} CPI:{len([e for e in events if 'CPI' in e])} FOMC:{len([e for e in events if 'FOMC' in e])} 總數:{len(events)} 全部有詳情")
