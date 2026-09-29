# -*- coding: utf-8 -*-
import json, sys, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]
BASE = "https://services.leadconnectorhq.com"
USERS = {
    "xHPu5HbnVNPF6QuPnf73": "unidade sp-sjc@",
    "f7YzBTlfq3LJXu4KIVg7": "gerencia SJC",
    "Q5pfBwf4jPWZnxOZlmjZ": "unidade eba@ (nao mexer)",
    "XgTUAYGWRzOVbADjopey": "gerencia EBA (nao mexer)",
}

def search(field, uid):
    body = json.dumps({"locationId": LOC, "page": 1, "pageLimit": 1, "filters": [{"field": field, "operator": "eq", "value": uid}]}).encode()
    r = urllib.request.Request(BASE + "/contacts/search", data=body, method="POST", headers={"Authorization": "Bearer " + KEY, "Version": "2021-07-28", "Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode()).get("total")

for uid, label in USERS.items():
    print(label, "owner", search("assignedTo", uid), "follower", search("followers", uid))
