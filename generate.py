import re, requests
from datetime import datetime, timezone

def fetch_real(url):
    h={"User-Agent":"Mozilla/5.0 (compatible; US-Econ/1.0; contact github.com/siumeifc1988-sketch/us-econ-calendar)"}
    # 直連
    try:
        r=requests.get(url, headers=h, timeout=20)
        if r.status_code==200 and len(r.text)>1000:
            return r.text
    except:
        pass
    # 多重代理
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
            # allorigins/get 回傳 json
            if '"contents"' in txt[:200]:
                try:
                    j=r.json()
                    txt=j.get("contents","")
                except:
                    pass
            if len(txt)>1000 and ("FOMC" in txt or "BEGIN:VCALENDAR" in txt or "fomc" in txt.lower()):
                print(f"代理成功 {proxy[:40]}")
                return txt
        except Exception as e:
            continue
    # BLS 鏡像
    if "bls.ics" in url:
        try:
            mirror="https://raw.githubusercontent.com/jginsburgn/us-macro-calendar/main/us_macro.ics"
            r=requests.get(mirror, headers=h, timeout=20)
            if r.status_code==200 and "BEGIN:VCALENDAR" in r.text:
                print("BLS鏡像成功 jginsburgn")
                return r.text
        except:
            pass
    raise Exception(f"真實抓失敗 {url}")

def build_bls_events(ics_text):
    out=[]
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

def parse_fomc_live(html):
    """參考 compasseconomiccalendar 同 jginsburgn 做法：Month day-day，取第二日"""
    events=[]
    mon_map={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
    for year in [2026, 2027, 2028]:
        pattern_year = rf"{year} FOMC Meetings(.*?)(?:####|\Z)"
        m_year = re.search(pattern_year, html, re.S|re.I)
        if not m_year:
            continue
        block = m_year.group(1)
        for m in re.finditer(r'(January|February|March|April|May|June|July|August|September|October|November|December)[\*\s,]*\s*(\d{{1,2}})-(\d{{1,2}})', block, re.I):
            mon_name=m.group(1).capitalize()
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
                events.append("\r\n".join([
                    "BEGIN:VEVENT",
                    f"UID:FOMC-{dt}@fed.gov",
                    f"DTSTAMP:{stamp}",
                    f"DTSTART;TZID=US-Eastern:{dt}",
                    "SUMMARY:FOMC",
                    "DESCRIPTION:Federal Reserve FOMC meeting - live from federalreserve.gov",
                    "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "END:VEVENT"
                ]))
            except:
                continue
    return events

def parse_fomc_from_jginsburgn():
    """備用：從 jginsburgn/us-macro-calendar 嘅 FOMC 抽出嚟，佢本身已經係官方"""
    try:
        url="https://raw.githubusercontent.com/jginsburgn/us-macro-calendar/main/us_macro.ics"
        h={"User-Agent":"Mozilla/5.0"}
        r=requests.get(url, headers=h, timeout=20)
        if r.status_code!=200:
            return []
        ics=r.text
        out=[]
        for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S|re.I):
            if "FOMC" not in block and "Federal Reserve" not in block:
                continue
            dt=re.search(r"DTSTART[^:]*:(\d{8})T?(\d{6})?", block)
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
                out.append("\r\n".join([
                    "BEGIN:VEVENT",
                    f"UID:FOMC-{dt_str}@fed.gov",
                    f"DTSTAMP:{stamp}",
                    f"DTSTART;TZID=US-Eastern:{dt_str}",
                    "SUMMARY:FOMC",
                    "DESCRIPTION:FOMC from jginsburgn/us-macro-calendar (official Fed)",
                    "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
                    "END:VEVENT"
                ]))
            except:
                continue
        print(f"jginsburgn FOMC 備用成功: {len(out)}")
        return out
    except Exception as e:
        print(f"jginsburgn FOMC 失敗: {e}")
        return []

# ===== 主流程 =====
print("抓 BLS...")
bls_ics = fetch_real("https://www.bls.gov/schedule/news_release/bls.ics")
events = build_bls_events(bls_ics)
print(f"BLS 完成 非農+CPI: {len(events)}")

print("抓 Fed FOMC (live)...")
fomc_events=[]
try:
    fed_html = fetch_real("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    fomc_events = parse_fomc_live(fed_html)
    print(f"FOMC live解析完成: {len(fomc_events)}")
except Exception as e:
    print(f"FOMC live 失敗: {e}")

# 如果 live 少過 2 條，用 jginsburgn 備用 (佢係出名多人用嘅日曆)
if len(fomc_events) < 2:
    print("FOMC live 少於2條，改用 jginsburgn 備用")
    fomc_events = parse_fomc_from_jginsburgn()

# 最後保底：Fed 官方 2026-2027 公布表 (唔係假，係官方表)
if len(fomc_events) < 2:
    print("仍少於2條，用 Fed 官方公布表保底")
    official = [
        "20261027T140000","20261208T140000",
        "20270126T140000","20270316T140000","20270427T140000","20270615T140000",
        "20270727T140000","20270914T140000","20271026T140000","20271207T140000",
    ]
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for dt in official:
        y=int(dt[:4]); mo=int(dt[4:6]); da=int(dt[6:8])
        if datetime(y,mo,da) < datetime.now():
            continue
        fomc_events.append("\r\n".join([
            "BEGIN:VEVENT",
            f"UID:FOMC-{dt}@fed.gov",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID=US-Eastern:{dt}",
            "SUMMARY:FOMC",
            "DESCRIPTION:Federal Reserve FOMC official calendar",
            "BEGIN:VALARM","TRIGGER:-P1D","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
            "BEGIN:VALARM","TRIGGER:-PT60M","ACTION:DISPLAY","DESCRIPTION:Reminder","END:VALARM",
            "END:VEVENT"
        ]))

events.extend(fomc_events)

# 只留未來
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
print(f"最終完成 非農:{len([e for e in events if '非農' in e])} CPI:{len([e for e in events if 'CPI' in e])} FOMC:{len([e for e in events if 'FOMC' in e])} 總數:{len(events)}")
