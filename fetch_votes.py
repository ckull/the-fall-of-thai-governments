from gq import *
from concurrent.futures import ThreadPoolExecutor
ve=json.load(open("data/ve.json"))
Q="""query($id:ID!,$limit:Int,$offset:Int){voteEvents(where:{id:{eq:$id}}){votes(limit:$limit,offset:$offset){option voter_party voter_name_raw voters{id}}}}"""
def get(e):
    out=[];off=0
    while True:
        d=gq(Q,{"id":e["id"],"limit":1000,"offset":off})["voteEvents"][0]["votes"]
        out+=d
        if len(d)<1000:break
        off+=1000
    time.sleep(1.2)
    return e["id"],[(v["option"],v["voter_party"],v["voters"][0]["id"] if v["voters"] else v["voter_name_raw"]) for v in out]
with ThreadPoolExecutor(3) as ex: res=dict(ex.map(get,ve))
json.dump(res,open("data/votes.json","w"),ensure_ascii=False)
print(sum(len(v) for v in res.values()))
