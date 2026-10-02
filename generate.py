import re, requests
from datetime import datetime, timedelta, timezone

def fetch(url):
    headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.bls.gov/"}
    try:
        r=requests.get(url, headers=headers, timeout=20)
        if r.status_code==200 and len(r.text)>500:
            print(f"直連成功")
            return r.text
        print(f"直連失敗 {r.status_code}")
    except Exception as e:
        print(f"直連error {e}")
    try:
        proxy=f"https://api.allorigins.win/raw?url={url}"
        r=requests.get(proxy, headers=headers, timeout=20)
        if r.status_code==200 and len(r.text)>500:
            print(f"代理成功")
            return r.text
    except Exception as e:
        print(f"代理error {e}")
    return ""

events=[]
stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

for url,label in [("https://www.bls.gov/schedule/news_release/empsit.htm","非農"),("https://www.bls.gov/schedule/news_release/cpi.htm","CPI")]:
    html=fetch(url)
    if not html: continue
    for m in re.finditer(r"\|\s*[A-Za-z]+\s+\d{4}\s*\|\s*([A-Za-z]{3,}\.?\s*\d{1,2},\s*\d{4})", html):
        try:
            d=datetime.strptime(m.group(1).replace(".",""), "%b %d, %Y")
            if d.replace(tzinfo=None) < datetime.now()-timedelta(days=1): continue
            dt=d.strftime("%Y%m%dT083000")
            events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:{label} {d.month}/{d.day}\r\nUID:{label}-{dt}@bls.gov\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")
        except: pass

# 保底，保證一定出到 us.ics，唔會再 exit 1
if not events:
    print("全部抓唔到，用公式保底")
    for k in range(3):
        now=datetime.now()
        y=now.year+(now.month-1+k)//12
        m=(now.month-1+k)%12+1
        d=datetime(y,m,1)
        while d.weekday()!=4: d+=timedelta(days=1)
        if d<now: continue
        dt=d.strftime("%Y%m%dT083000")
        events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:非農 {d.month}/{d.day}\r\nUID:calc-{dt}\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

ics="BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//fix-403//\r\nX-WR-CALNAME:美股\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n"+"\r\n".join(events)+"\r\nEND:VCALENDAR"
open("us.ics","w",encoding="utf-8").write(ics)
print(f"done {len(events)}")
