import json
import urllib.error
import urllib.request

key = "pit-54be0041-b880-4912-b6e0-5fad3ec30d03"
agent = "3Fzfmx7ViwyD9v16h4DR"
action = "zeWiS2QJD0LcF6UOaejG"
base = "https://services.leadconnectorhq.com"


def req(method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


status, cur = req("GET", f"/conversation-ai/agents/{agent}/actions/{action}")
print("GET", status)
details = cur["data"]["details"]
print("current cals", [c["id"] for c in details["calendarIds"]])

blocked = {"e6FA0Add4dZVXt6qN40y", "dypic8EB1pS2Zh8hJw1c", "cNAnPs8MGpkjO1bSyba9"}
new_cals = [
    {"id": c["id"], "triggerCondition": c.get("triggerCondition") or ""}
    for c in details["calendarIds"]
    if c["id"] not in blocked
]

base_details = {
    "calendarIds": new_cals,
    "calendarActionType": details.get("calendarActionType", "multiple"),
    "aiDescription": (
        "Agendar SOMENTE clinico geral nos calendarios oficiais por unidade e dia. "
        "NUNCA usar Carlos Augusto nem Leonardo."
    ),
    "fallbackCalendar": bool(details.get("fallbackCalendar")),
    "fallbackCalendarId": details.get("fallbackCalendarId") or "",
    "onlySendLink": bool(details.get("onlySendLink")),
    "triggerWorkflow": False,
    "sleepAfterBooking": bool(details.get("sleepAfterBooking")),
    "transferBot": bool(details.get("transferBot")),
    "rescheduleEnabled": bool(details.get("rescheduleEnabled", True)),
    "cancelEnabled": bool(details.get("cancelEnabled", True)),
}

variants = [
    {"name": cur["data"]["name"], "type": cur["data"]["type"], "details": dict(base_details)},
    {
        "name": cur["data"]["name"],
        "type": cur["data"]["type"],
        "details": {**base_details, "calendarId": new_cals[0]["id"]},
    },
    {
        "name": cur["data"]["name"],
        "type": cur["data"]["type"],
        "details": {
            **base_details,
            "calendarIds": [c["id"] for c in new_cals],  # strings
        },
    },
]

for i, body in enumerate(variants):
    print(f"\n=== variant {i} ===")
    print(json.dumps(body)[:500])
    st, resp = req("PUT", f"/conversation-ai/agents/{agent}/actions/{action}", body)
    print("status", st)
    print(str(resp)[:700])

st, cur2 = req("GET", f"/conversation-ai/agents/{agent}/actions/{action}")
ids = [c["id"] for c in cur2["data"]["details"]["calendarIds"]]
print("\nVERIFY", ids)
print("blocked left", [i for i in ids if i in blocked])
