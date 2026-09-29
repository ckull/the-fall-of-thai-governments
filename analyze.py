"""Reproduce the Politigraph findings from data/*.json (run fetch_*.py first to refresh).
Data: Politigraph by WeVis, CC BY-NC 4.0 — https://politigraph.wevis.info"""
import json, collections as C, statistics as S
from datetime import date

L = lambda f: json.load(open(f"data/{f}.json"))
bills, ve, votes, people, orgs = L("bills"), {e["id"]: e for e in L("ve")}, L("votes"), L("people"), L("orgs")
parties = {p["id"]: p["name"] for p in L("parties")}
PRESENT = {"เห็นด้วย", "ไม่เห็นด้วย", "งดออกเสียง", "ไม่ลงคะแนนเสียง"}
ABSENT = "ลา / ขาดลงมติ"
chamber = lambda e: e["organizations"][0]["id"] if len(e["organizations"]) == 1 else "joint"


def bill_funnel():
    print("\n## 1. Bill pass rate by proposer")
    t = C.Counter((b["creator_type"], b["status"]) for b in bills)
    for k in ["ASSEMBLY", "POLITICIAN", "PEOPLE", "UNKNOWN"]:
        n = sum(v for (c, _), v in t.items() if c == k)
        print(f"{k:11} total {n:4}  enacted {t[(k,'ENACTED')]:3} ({t[(k,'ENACTED')]/n:.1%})  "
              f"rejected {t[(k,'REJECTED')]:3}  merged {t[(k,'MERGED')]:3}  in progress {t[(k,'IN_PROGRESS')]:3}")
    ed = [b for b in bills if b["classification"] == "EMERGENCY_DECREE"]
    print("emergency decrees:", C.Counter(b["status"] for b in ed))
    mp = [b for b in bills if b["creator_type"] == "POLITICIAN"]
    voted = sum(any(e.get("classification") == "MP_1" for e in b["events"] if e["__typename"] == "BillVoteEvent") for b in mp)
    print(f"MP bills never reaching a first-reading vote: {len(mp)-voted} of {len(mp)}")
    days = C.defaultdict(list)
    for b in bills:
        en = [e["start_date"] for e in b["events"] if e["__typename"] == "BillEnactEvent" and e.get("start_date")]
        if en and b["proposal_date"]:
            days[b["creator_type"]].append((date.fromisoformat(en[0]) - date.fromisoformat(b["proposal_date"])).days)
    for k, v in days.items():
        print(f"{k}: median {S.median(v)} days to enact (n={len(v)})")


def cabinet_churn():
    print("\n## 2. Cabinet lifespans and minister turnover")
    for c in sorted((o for o in orgs if o["classification"] == "CABINET"), key=lambda o: o["term"]):
        end = date.fromisoformat(c["dissolution_date"]) if c["dissolution_date"] else date.today()
        print(f"cabinet {c['term']}: {c['founding_date']} → {c['dissolution_date'] or 'now'}  "
              f"{(end-date.fromisoformat(c['founding_date'])).days} days")
    holders = C.defaultdict(set)
    for p in people:
        for m in p["memberships"]:
            for po in m["posts"]:
                if po["role"].startswith("รัฐมนตรีว่าการ") and any(o["classification"] == "CABINET" for o in po["organizations"]):
                    holders[po["role"]].add(p["id"])
    for n, r in sorted(((len(v), k) for k, v in holders.items()), reverse=True)[:6]:
        print(f"{n} people: {r}")


def party_switching():
    # Uses membership records, not Vote.voter_party (that field is raw OCR and noisy).
    print("\n## 3. Party switching")
    flows, n_parties = C.Counter(), C.Counter()
    for p in people:
        ms = sorted((m["start_date"], o["id"]) for m in p["memberships"] for po in m["posts"]
                    for o in po["organizations"] if o["classification"] == "POLITICAL_PARTY")
        seq = []
        for _, o in ms:
            if not seq or seq[-1] != o:
                seq.append(o)
        if seq:
            n_parties[len(seq)] += 1
        flows.update((parties.get(a, a), parties.get(b, b)) for a, b in zip(seq, seq[1:]))
    print("people by number of parties:", sorted(n_parties.items()))
    for (a, b), n in flows.most_common(15):
        print(f"{n:4}  {a} → {b}")
    print("inflows to ภูมิใจไทย:", sum(n for (a, b), n in flows.items() if b == "ภูมิใจไทย"))


def unanimity_and_absence():
    print("\n## 4–5. How one-sided votes are, and absence")
    for ch in ["สภาผู้แทนราษฎร-25", "สภาผู้แทนราษฎร-26", "สภาผู้แทนราษฎร-27", "วุฒิสภา-13", "joint"]:
        share, absent = [], []
        for i, vs in votes.items():
            if chamber(ve[i]) != ch or not vs:
                continue
            p = [o for o, _, _ in vs if o in PRESENT]
            if p:
                share.append(C.Counter(p).most_common(1)[0][1] / len(p))
                absent.append(1 - len(p) / len(vs))
        print(f"{ch}: {len(share)} votes, median top-option share {S.median(share):.1%}, "
              f"≥95% one-sided {sum(s >= .95 for s in share)}, mean absent {S.mean(absent):.1%}")
    per = C.defaultdict(lambda: [0, 0])
    for i, vs in votes.items():
        for o, _, pid in vs:
            a = per[(pid, chamber(ve[i]))]
            a[0] += o == ABSENT
            a[1] += 1
    for ch in ["สภาผู้แทนราษฎร-25", "สภาผู้แทนราษฎร-26", "สภาผู้แทนราษฎร-27"]:
        r = [a / n for (pid, c), (a, n) in per.items() if c == ch and n >= 20]
        print(f"{ch}: {len(r)} MPs, median absent {S.median(r):.0%}, MPs absent >50%: {sum(x > .5 for x in r)}")


if __name__ == "__main__":
    bill_funnel()
    cabinet_churn()
    party_switching()
    unanimity_and_absence()
