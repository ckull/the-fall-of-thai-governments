import json,urllib.request,time,sys
def gq(q,v=None):
    for i in range(5):
        r=urllib.request.Request("https://politigraph.wevis.info/graphql",json.dumps({"query":q,"variables":v or {}}).encode(),{"Content-Type":"application/json","apollographql-client-name":"analysis-probe","User-Agent":"curl/8.7.1"})
        try:
            d=json.load(urllib.request.urlopen(r,timeout=120))
        except Exception as e:
            print("retry",e,file=sys.stderr); time.sleep(3); continue
        if "errors" in d: raise Exception(json.dumps(d["errors"],ensure_ascii=False)[:800])
        return d["data"]
def paged(field,q,v=None,size=1000):
    out=[];off=0
    while True:
        d=gq(q,{**(v or {}),"limit":size,"offset":off})[field]
        out+=d
        if len(d)<size: return out
        off+=size; time.sleep(0.4)
