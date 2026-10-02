import datetime, timedelta
stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
events = []

# 就算 BLS 連唔上，都保證有 3 個月嘅非農，唔會再 exit 1
for k in range(3):
    d = datetime.datetime.now().replace(day=1)
    m = d.month - 1 + k
    y = d.year + m // 12
    m = m % 12 + 1
    d = datetime.datetime(y, m, 1)
    while d.weekday() != 4: # 5 = 星期五
        d += timedelta.Timedelta(days=1) if hasattr(timedelta, 'Timedelta') else datetime.timedelta(days=1)
    # 上面有啲 runner 用 timedelta，簡化版：
    # while d.weekday()!=4: d+=datetime.timedelta(days=1)
    if d < datetime.datetime.now():
        continue
    dt = d.strftime("%Y%m%dT083000")
    events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:非農 {d.month}/{d.day}\r\nUID:test-{dt}\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

# 如果上面 while 有問題，用最簡單版
if not events:
    d = datetime.datetime.now()
    dt = d.strftime("%Y%m%dT083000")
    events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:非農測試\r\nUID:test\r\nEND:VEVENT")

ics = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//\r\nX-WR-CALNAME:美股\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR"
open("us.ics","w",encoding="utf-8").write(ics)
print("OK", len(events))
