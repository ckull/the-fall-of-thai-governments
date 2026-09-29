"""Compile data/*.json into the compact dataset embedded in the story page."""
import json, collections as C, statistics as S
from datetime import date
L = lambda f: json.load(open(f"data/{f}.json"))
bills, ve, votes, people, orgs = L("bills"), {e["id"]: e for e in L("ve")}, L("votes"), L("people"), L("orgs")
parties = {p["id"]: p["name"] for p in L("parties")}
PRESENT = {"เห็นด้วย", "ไม่เห็นด้วย", "งดออกเสียง", "ไม่ลงคะแนนเสียง"}
chamber = lambda e: e["organizations"][0]["id"] if len(e["organizations"]) == 1 else "joint"
out = {}
# every bill as a dot: [proposer, status, year, title, isDecree]
# a few bill titles are left out of the hover boxes; the bill still counts as a dot
import re as _re
SENSITIVE = _re.compile("\u0e1e\u0e23\u0e30\u0e21\u0e2b\u0e32\u0e01\u0e29\u0e31\u0e15\u0e23\u0e34\u0e22\u0e4c|112")
out["bills"] = [[b["creator_type"], b["status"], (b["proposal_date"] or "")[:4], "" if SENSITIVE.search(b["title"]) else b["title"], b["classification"] == "EMERGENCY_DECREE"] for b in bills]
mp = [b for b in bills if b["creator_type"] == "POLITICIAN"]
out["mpNeverVoted"] = sum(not any(e.get("classification") == "MP_1" for e in b["events"] if e["__typename"] == "BillVoteEvent") for b in mp)
days = C.defaultdict(list)
for b in bills:
    en = [e["start_date"] for e in b["events"] if e["__typename"] == "BillEnactEvent" and e.get("start_date")]
    if en and b["proposal_date"]:
        days[b["creator_type"]].append((date.fromisoformat(en[0]) - date.fromisoformat(b["proposal_date"])).days)
out["medianDays"] = {k: S.median(v) for k, v in days.items()}
out["cabinets"] = [[c["term"], c["founding_date"], c["dissolution_date"]] for c in sorted((o for o in orgs if o["classification"] == "CABINET"), key=lambda o: o["term"])]
out["houses"] = [[c["term"], c["founding_date"], c["dissolution_date"]] for c in sorted((o for o in orgs if o["classification"] == "HOUSE_OF_REPRESENTATIVE"), key=lambda o: o["term"])]
holders = C.defaultdict(set)
for p in people:
    for m in p["memberships"]:
        for po in m["posts"]:
            if po["role"].startswith("รัฐมนตรีว่าการ") and any(o["classification"] == "CABINET" for o in po["organizations"]):
                holders[po["role"].replace("รัฐมนตรีว่าการกระทรวง", "")].add(p["id"])
out["ministers"] = sorted(((k, len(v)) for k, v in holders.items()), key=lambda x: -x[1])
flows, np_ = C.Counter(), C.Counter()
for p in people:
    ms = sorted((m["start_date"], o["id"]) for m in p["memberships"] for po in m["posts"] for o in po["organizations"] if o["classification"] == "POLITICAL_PARTY")
    seq = []
    for _, o in ms:
        if not seq or seq[-1] != o: seq.append(o)
    if seq: np_[len(seq)] += 1
    flows.update((parties.get(a, a), parties.get(b, b)) for a, b in zip(seq, seq[1:]))
out["flows"] = [[a, b, n] for (a, b), n in flows.most_common(14)]
out["partyCounts"] = dict(np_)
out["bjtInflow"] = sum(n for (a, b), n in flows.items() if b == "ภูมิใจไทย")
share = C.defaultdict(list); per = C.defaultdict(lambda: [0, 0])
for i, vs in votes.items():
    ch = chamber(ve[i]); p = [o for o, _, _ in vs if o in PRESENT]
    if p: share[ch].append(round(C.Counter(p).most_common(1)[0][1] / len(p), 4))
    for o, _, pid in vs:
        a = per[(pid, ch)]; a[0] += o == "ลา / ขาดลงมติ"; a[1] += 1
out["unanimity"] = {k: v for k, v in share.items() if k != "joint"}
out["senatePassed"] = [sum(ve[i]["result"] == "ผ่าน" for i in votes if chamber(ve[i]) == "วุฒิสภา-13"), sum(chamber(ve[i]) == "วุฒิสภา-13" for i in votes)]
ab = {}
for ch in ["สภาผู้แทนราษฎร-25", "สภาผู้แทนราษฎร-26", "สภาผู้แทนราษฎร-27"]:
    r = [a / n for (pid, c), (a, n) in per.items() if c == ch and n >= 20]
    h = [0] * 10
    for x in r: h[min(int(x * 10), 9)] += 1
    ab[ch] = {"n": len(r), "median": round(S.median(r), 3), "over50": sum(x > .5 for x in r), "hist": h, "votes": sum(chamber(ve[i]) == ch for i in votes)}
out["absence"] = ab
# prime minister and minister attendance (House votes only)
ANUTIN = "4cc8dfaf-e5ce-41f4-94d3-53bf858308b4"
mint = C.defaultdict(list)
for p in people:
    for m in p["memberships"]:
        for po in m["posts"]:
            if any(o["classification"] == "CABINET" for o in po["organizations"]):
                mint[p["id"]].append((m["start_date"], m["end_date"] or "9999"))
pmr = {}
for ch in ["สภาผู้แทนราษฎร-25", "สภาผู้แทนราษฎร-26", "สภาผู้แทนราษฎร-27"]:
    rates = sorted(((a / n, pid) for (pid, c), (a, n) in per.items() if c == ch and n >= 20), reverse=True)
    mn = [0, 0]
    for i, vs in votes.items():
        if chamber(ve[i]) != ch: continue
        dt = ve[i]["start_date"]
        for o, _, pid in vs:
            if any(s <= dt <= e for s, e in mint.get(pid, [])):
                mn[0] += o == "ลา / ขาดลงมติ"; mn[1] += 1
    a, n = per[(ANUTIN, ch)]
    pmr[ch] = {"missed": a, "votes": n, "rank": [pid for _, pid in rates].index(ANUTIN) + 1, "of": len(rates), "ministerRate": round(mn[0] / mn[1], 3)}
asPm = [0, 0]
for i, vs in votes.items():
    if ve[i]["start_date"] >= "2025-09-19":
        for o, _, pid in vs:
            if pid == ANUTIN: asPm[0] += o == "ลา / ขาดลงมติ"; asPm[1] += 1
out["anutin"] = {"terms": pmr, "asPm": asPm}
# party-switching network: who moved where, per period, and which side the destination was on
cab = json.load(open("data/cabinet_sides.json"))
side_at = []  # (start, end, party, side)
for c in cab:
    for po in c["posts"]:
        if po["role"].startswith("พรรคฝ่าย"):
            sd = "gov" if po["role"] == "พรรคฝ่ายรัฐบาล" else "opp"
            for m in po["memberships"]:
                for o in m["members"]:
                    side_at.append((m["start_date"], m["end_date"] or "9999", o["name"], sd))
# Anutin cabinets (from 2025-09-05) are not yet recorded in Politigraph; only the PM's own party and the main opposition are set here from public record
ANUTIN_ERA = "2025-08-30"
def side(party, dt):
    if dt >= ANUTIN_ERA:
        return {"ภูมิใจไทย": "gov", "ประชาชน": "opp"}.get(party, "unknown")
    s = {sd for a, b, p, sd in side_at if p == party and a <= dt <= b}
    if not s:  # between cabinets: use the next cabinet formed
        nxt = sorted((a, p, sd) for a, b, p, sd in side_at if a > dt)
        if nxt:
            first = nxt[0][0]
            s = {sd for a, p, sd in nxt if a == first and p == party}
    return s.pop() if len(s) == 1 else ("unknown" if not s else "both")
FORCED = {("ก้าวไกล", "ประชาชน"), ("อนาคตใหม่", "ก้าวไกล")}
PERIODS = [["prayut", "Prayut, 2019–23", "0000", "2023-09-01"], ["pheuthai", "Srettha and Paetongtarn, 2023–25", "2023-09-01", ANUTIN_ERA], ["anutin", "Anutin, 2025–26", ANUTIN_ERA, "9999"]]
edges = C.defaultdict(lambda: {"n": 0, "names": []})
members = C.Counter()
for p in people:
    ms = sorted((m["start_date"], o["id"]) for m in p["memberships"] for po in m["posts"] for o in po["organizations"] if o["classification"] == "POLITICAL_PARTY")
    for pid in {o for _, o in ms}: members[parties.get(pid, pid)] += 1
    seq = []
    for d, o in ms:
        if not seq or seq[-1][1] != o: seq.append((d, o))
    for (_, a), (d, b) in zip(seq, seq[1:]):
        A, B = parties.get(a, a), parties.get(b, b)
        per_ = next(k for k, _, s0, s1 in PERIODS if s0 <= d < s1)
        kind = "forced" if (A, B) in FORCED else side(B, d)
        e = edges[(per_, A, B, kind)]; e["n"] += 1; e["names"].append(p["name"])
out["network"] = {
    "periods": [[k, l] for k, l, _, _ in PERIODS],
    "edges": [[k, a, b, kind, v["n"], sorted(v["names"])] for (k, a, b, kind), v in edges.items()],
    "members": dict(members),
    # each party's side in the last cabinet of each period (Anutin era: only the PM's party and the main opposition are known)
    "sides": {
        "prayut": {p: sd for a0, b0, p, sd in side_at if a0 == "2019-07-10"},
        "pheuthai": {p: sd for a0, b0, p, sd in side_at if a0 == "2024-09-04"},
        "anutin": {"ภูมิใจไทย": "gov", "ประชาชน": "opp"},
    },
}
# the two votes that made Anutin prime minister: each MP's choice, grouped by party
import re
known = sorted(set(parties.values()), key=len, reverse=True)
def party_of(raw):
    c = re.sub(r"[^\u0E00-\u0E7F]", "", raw or "")
    c = c[4:] if c.startswith("พรรค") else c
    return c if c in known else next((k for k in known if c.startswith(k)), "other")
pmv = []
for e in sorted((e for e in ve.values() if e["classification"] == "PM_VOTE"), key=lambda e: e["start_date"]):
    byp = C.defaultdict(C.Counter)
    for o, p, _ in votes[e["id"]]:
        byp[party_of(p)][o] += 1
    pmv.append({"date": e["start_date"], "parties": {k: dict(v) for k, v in byp.items()}})
out["pmVotes"] = pmv
# party logos (from Politigraph, resized to 72px by the download step) embedded as data URIs
import base64, os
out["logos"] = {f[:-4]: "data:image/png;base64," + base64.b64encode(open("data/logos/" + f, "rb").read()).decode()
                for f in sorted(os.listdir("data/logos")) if f.endswith(".png")}
open("data/story.json", "w").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print({k: (v if k not in ("bills", "unanimity") else len(v)) for k, v in out.items()})
# embed into the story page
tpl = open("story_template.html").read()
open("fall-of-thai-governments.html", "w").write(tpl.replace("/*DATA*/null", json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))

# hosted build: a full HTML document for Cloudflare Pages (the artifact viewer adds this wrapper itself)
import os
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")  # e.g. https://your-project.pages.dev, for absolute share-image links
os.makedirs("dist", exist_ok=True)
page = open("fall-of-thai-governments.html").read()
desc_en = "Why Thai governments keep falling: five cabinets in seven years, who writes the laws, party switching and the 2026 referendum. A bilingual data story built on WeVis's Politigraph."
desc_th = "ทำไมรัฐบาลไทยล้มแล้วล้มอีก: ห้าคณะรัฐมนตรีในเจ็ดปี ใครเขียนกฎหมาย การย้ายพรรค และประชามติ 2569"
og_img = f"{SITE_URL}/og.png" if SITE_URL else "og.png"
favicon = "data:image/svg+xml," + "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23161a22'/%3E%3Crect x='7' y='9' width='18' height='4' rx='2' fill='%23fbfcfd'/%3E%3Crect x='7' y='16' width='9' height='4' rx='2' fill='%23fbfcfd'/%3E%3Crect x='7' y='23' width='4' height='4' rx='2' fill='%23e0572a'/%3E%3C/svg%3E"
head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{desc_en}">
<meta property="og:type" content="article">
<meta property="og:title" content="The Fall of Thai Governments · รัฐบาลที่ล้มแล้วล้มอีก">
<meta property="og:description" content="{desc_en} {desc_th}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
{f'<meta property="og:url" content="{SITE_URL}/">' if SITE_URL else ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#fbfcfd">
<link rel="icon" href="{favicon}">
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
"""
# the page starts with its own <title>, links and <style>; they stay in <head>, the rest goes in <body>
split = page.index("</style>") + len("</style>")
html_out = head + page[:split] + "\n</head>\n<body>\n" + page[split:] + "\n</body>\n</html>\n"
open("dist/index.html", "w").write(html_out)
import shutil
shutil.copyfile("assets/og.png", "dist/og.png")  # made once from og_card.html with Chrome
open("dist/_headers", "w").write("/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n/og.png\n  Cache-Control: public, max-age=86400\n")
print("dist written:", len(html_out), "bytes")
