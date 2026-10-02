from datetime import datetime, timedelta, timezone
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
events = []
for k in range(6):
    now = datetime.now()
    y = now.year + (now.month - 1 + k) // 12
    m = (now.month - 1 + k) % 12 + 1
    d = datetime(y, m, 1)
    while d.weekday() != 4:
        d += timedelta(days=1)
    if d < now:
        continue
    dt = d.strftime("%Y%m%dT083000")
    events.append(f"BEGIN:VEVENT\r\nDTSTART;TZID=US-Eastern:{dt}\r\nDTSTAMP:{stamp}\r\nSUMMARY:非農 {m}/{d.day}\r\nUID:{dt}\r\nBEGIN:VALARM\r\nTRIGGER:-P1D\r\nEND:VALARM\r\nBEGIN:VALARM\r\nTRIGGER:-PT60M\r\nEND:VALARM\r\nEND:VEVENT")

ics = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//offline//\r\nX-WR-CALNAME:美股\r\nBEGIN:VTIMEZONE\r\nTZID:US-Eastern\r\nBEGIN:DAYLIGHT\r\nTZOFFSETFROM:-0500\r\nTZOFFSETTO:-0400\r\nDTSTART:20070311T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\nTZOFFSETFROM:-0400\r\nTZOFFSETTO:-0500\r\nDTSTART:20071104T020000\r\nRRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n" + "\r\n".join(events) + "\r\nEND:VCALENDAR"
open("us.ics","w",encoding="utf-8").write(ics)
print(f"done {len(events)}")
