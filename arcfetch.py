import json, sys, urllib.request, urllib.parse, time
def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r: return json.load(r)
        except Exception as e:
            print('retry', e, file=sys.stderr); time.sleep(2*(i+1))
    raise SystemExit('failed '+url)
def esri2geom(g):
    if g is None: return None
    if 'x' in g: return {'type':'Point','coordinates':[g['x'],g['y']]}
    if 'rings' in g: return {'type':'Polygon','coordinates':g['rings']}  # fixed later via shapely
    if 'paths' in g: return {'type':'MultiLineString','coordinates':g['paths']}
def fetch(layer, where='1=1', fields='*', out=None, geom=True):
    meta=get(layer+'?f=json'); print(meta.get('name'), meta.get('geometryType'), file=sys.stderr)
    feats=[]; off=0; page=meta.get('maxRecordCount',1000) or 1000
    while True:
        qs=urllib.parse.urlencode(dict(where=where,outFields=fields,outSR=4326,f='json',resultOffset=off,resultRecordCount=page,returnGeometry=str(geom).lower()))
        d=get(layer+'/query?'+qs)
        if 'error' in d: raise SystemExit(d)
        fs=d.get('features',[])
        for f in fs: feats.append({'type':'Feature','properties':f['attributes'],'geometry':esri2geom(f.get('geometry'))})
        off+=len(fs)
        if not fs or not d.get('exceededTransferLimit'): break
    print(len(feats),'features', file=sys.stderr)
    json.dump({'type':'FeatureCollection','features':feats}, open(out,'w'))
    return meta
if __name__=='__main__':
    layer,out=sys.argv[1],sys.argv[2]; where=sys.argv[3] if len(sys.argv)>3 else '1=1'
    m=fetch(layer,where,out=out)
    print([f['name'] for f in m.get('fields',[])], file=sys.stderr)
