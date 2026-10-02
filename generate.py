import re, requests
from datetime import datetime, timezone

# ===== 真實訂閱版 - 無保底硬編碼 =====
# 1. BLS 真實 ics  2. Fed 官網即時解析 FOMC，無爬到就無FOMC，唔用假日期

def fetch_real(url):
    h={"User-Agent":"Mozilla/5.0 (compatible; US-Econ/1.0; contact github.com/siumeifc1988-sketch/us-econ-calendar)"}
    # 直連
    try:
        r=requests.get(url, headers=h, timeout=20)
        if r.status_code==200 and len(r.text)>1000:
            return r.text
    except:
        pass
    # 多重代理 - 全部都係真實原文
    for proxy in [
        f"https://api.allorigins.win/raw?url={url}",
        f"https://api.codetabs.com/v1/proxy?quest={url}",
        f"https://thingproxy.freeboard.io/fetch/{url}",
        f"https://corsproxy.io/?{url}",
    ]:
        try:
            r=requests.get(proxy, headers=h, timeout=20)
            if r.status_code==200 and len(r.text)>1000 and ("BEGIN:VCALENDAR" in r.text or "FOMC" in r.text):
                print(f"代理成功 {proxy[:30]}")
                return r.text
        except:
            pass
    try:
        r=requests.get(f"https://api.allorigins.win/get?url={url}", headers=h, timeout=20)
        j=r.json()
        if "contents" in j and len(j["contents"])>1000:
            return j["contents"]
    except:
        pass
    # BLS 真實鏡像 - 仍是官方數，非保底
    if "bls.ics" in url:
        try:
            mirror="https://raw.githubusercontent.com/jginsburgn/us-macro-calendar/main/us_macro.ics"
            r=requests.get(mirror, headers=h, timeout=20)
            if r.status_code==200 and "BEGIN:VCALENDAR" in r.text:
                print("BLS鏡像成功")
                return r.text
        except:
            pass
    raise Exception(f"真實抓失敗 {url} - 純訂閱版不使用保底")

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
    """純訂閱解析 - 直接從 Fed 官網解析，無保底"""
    events=[]
    mon_map={"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
    # 抓 2026 和 2027 區塊
    for year in [2026, 2027, 2028]:
        # 找 "2026 FOMC Meetings" 到下一個 "####" 或 結尾
        pattern_year = rf"{year} FOMC Meetings(.*?)(?:####|\Z)"
        m_year = re.search(pattern_year, html, re.S|re.I)
        if not m_year:
            continue
        block = m_year.group(1)
        # 解析 Month, day-day
        # 支援 **January**\n\n27-28 和 **January**, 26-27
        for m in re.finditer(r'(January|February|March|April|May|June|July|August|September|October|November|December)[\*\s,]*\s*(\d{1,2})-(\d{1,2})', block, re.I):
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

# ===== 主流程 =====
print("抓 BLS...")
bls_ics = fetch_real("https://www.bls.gov/schedule/news_release/bls.ics")
events = build_bls_events(bls_ics)
print(f"BLS 完成 非農+CPI: {len(events)}")

print("抓 Fed FOMC...")
try:
    fed_html = fetch_real("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    fomc_events = parse_fomc_live(fed_html)
    print(f"FOMC live解析完成: {len(fomc_events)}")
    events.extend(fomc_events)
except Exception as e:
    print(f"FOMC 抓失敗，純訂閱版不補保底: {e}")

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
