import hashlib,json
from src.constants.features import FEATURES
def fingerprint(rows,config):
 canonical=[{'id':r['id'],'reference':r['reference'],'features':{k:float(r['features'][k]) for k in sorted(FEATURES)},'label':int(r['label'])} for r in sorted(rows,key=lambda r:r['reference'])]
 return hashlib.sha256(json.dumps({'rows':canonical,'config':config,'algorithm':'logistic-pipeline-v2-sentinel','split_seed':73},sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
