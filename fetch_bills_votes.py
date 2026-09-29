from gq import *
import re
# a few titles are withheld from the published data; counts and statuses are kept
WITHHELD = re.compile("\u0e1e\u0e23\u0e30\u0e21\u0e2b\u0e32\u0e01\u0e29\u0e31\u0e15\u0e23\u0e34\u0e22\u0e4c|112")
def withhold(rows):
    for x in rows:
        if WITHHELD.search(x.get("title") or ""): x["title"] = ""
    return rows
bills=paged("bills","""query($limit:Int,$offset:Int){bills(limit:$limit,offset:$offset){id title status creator_type classification proposal_date categories people_signature_count
 organizations{id} events{__typename ... on BillEnactEvent{start_date} ... on BillRejectEvent{start_date} ... on BillRoyalAssentEvent{start_date} ... on BillVoteEvent{classification start_date}}}}""")
json.dump(withhold(bills),open("data/bills.json","w"),ensure_ascii=False)
ve=paged("voteEvents","""query($limit:Int,$offset:Int){voteEvents(limit:$limit,offset:$offset){id title nickname classification start_date result agree_count disagree_count abstain_count novote_count organizations{id classification} bills{id}}}""")
json.dump(withhold(ve),open("data/ve.json","w"),ensure_ascii=False)
orgs=gq("""{organizations(where:{classification:{in:[CABINET,HOUSE_OF_REPRESENTATIVE,HOUSE_OF_SENATE]}}){id name classification term founding_date dissolution_date}}""")["organizations"]
json.dump(orgs,open("data/orgs.json","w"),ensure_ascii=False)
print(len(bills),len(ve),len(orgs))
P=gq("""{organizations(where:{classification:{eq:POLITICAL_PARTY}}){id name founding_date dissolution_date}}""")["organizations"]
json.dump(P,open("data/parties.json","w"),ensure_ascii=False)
people=paged("people","""query($limit:Int,$offset:Int){people(limit:$limit,offset:$offset){id name
 memberships{start_date end_date posts{role organizations{id classification}}}}}""")
json.dump(people,open("data/people.json","w"),ensure_ascii=False)
print(len(P),"parties",len(people),"people")
