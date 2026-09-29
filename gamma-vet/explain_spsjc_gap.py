# -*- coding: utf-8 -*-
import json
import re
from collections import Counter
from pathlib import Path

SRC = Path(r"c:\Users\GC1\Downloads\Clientes SPSJC.txt")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE_RE = re.compile(r"^(\d{8})\s+(.+)$")

text = SRC.read_bytes().decode("cp1252")
all_lines = text.splitlines()
nonempty = [ln for ln in all_lines if ln.strip()]

rows = []
blank = len(all_lines) - len(nonempty)
no_email = []
invalid_email = []
for i, raw in enumerate(nonempty, 1):
    parts = raw.split("\t")
    while len(parts) < 3:
        parts.append("")
    col0, email, phone = parts[0].strip(), parts[1].strip().lower(), parts[2].strip()
    m = CODE_RE.match(col0)
    name = m.group(2).strip() if m else col0
    digits = re.sub(r"\D", "", phone)
    rec = {"line": i, "name": name, "email": email, "phone": phone, "digits": digits}
    if not email:
        no_email.append(rec)
        continue
    if not EMAIL_RE.match(email):
        invalid_email.append(rec)
        continue
    rows.append(rec)

emails = [r["email"] for r in rows]
by_email = Counter(emails)
dup_emails = {e: n for e, n in by_email.items() if n > 1}
dup_extra = sum(n - 1 for n in dup_emails.values())

def norm_phone(digits):
    if not digits:
        return None
    if digits.startswith("55") and len(digits) in (12, 13):
        return "+" + digits
    if len(digits) in (10, 11):
        return "+55" + digits
    return None

with_phone = []
for r in rows:
    p = norm_phone(r["digits"])
    r["norm"] = p
    if p:
        with_phone.append(r)

# unique emails, keep phone if any
uniq = {}
for r in rows:
    prev = uniq.get(r["email"])
    if prev is None:
        uniq[r["email"]] = r
    elif r["norm"] and not prev["norm"]:
        uniq[r["email"]] = r

unique_list = list(uniq.values())
phone_map = {}
for r in unique_list:
    if not r["norm"]:
        continue
    phone_map.setdefault(r["norm"], []).append(r["email"])
phone_collisions = {p: ems for p, ems in phone_map.items() if len(ems) > 1}
merged_extra = sum(len(ems) - 1 for ems in phone_collisions.values())

print("file_lines", len(all_lines))
print("nonempty", len(nonempty))
print("blank", blank)
print("valid_email_rows", len(rows))
print("no_email", len(no_email), [(x["name"], x["email"]) for x in no_email])
print("invalid_email", len(invalid_email))
for x in invalid_email:
    print("  INV", x["name"], x["email"])
print("dup_email_addresses", len(dup_emails))
print("dup_extra_rows", dup_extra)
print("unique_emails", len(unique_list))
print("phone_collision_groups", len(phone_collisions))
print("phone_merged_extra", merged_extra)
print("expected_contacts_if_phone_merge", len(unique_list) - merged_extra)
print("ghl_tagged", 3410)
print("gap_unique_vs_ghl", len(unique_list) - 3410)

# extra invalid that passed regex but GHL rejected
print("passed_regex_but_ghl_422", "alyny_acg@hotmail.co9m" in uniq)
if "alyny_acg@hotmail.co9m" in uniq:
    print("  that one still in unique set")

# show a few phone collisions
print("--- phone collisions sample ---")
for i, (p, ems) in enumerate(list(phone_collisions.items())[:8]):
    print(p, ems)
