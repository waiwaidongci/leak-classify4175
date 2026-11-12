from sqlalchemy import select,func
from fastapi import HTTPException
from src.models import WindowDataset,SensorWindow
from src.utils.serialize import row
from .audit import record
from .fingerprint import fingerprint
def list_datasets(db):
 out=[]
 for d in db.scalars(select(WindowDataset).order_by(WindowDataset.id)):
  n=db.scalar(select(func.count()).select_from(SensorWindow).where(SensorWindow.dataset_id==d.id));positive=db.scalar(select(func.sum(SensorWindow.label)).where(SensorWindow.dataset_id==d.id)) or 0
  out.append(dict(row(d),count=n,positive=positive,prevalence=positive/n if n else 0))
 return out
def get_windows(db,id,limit=None):
 if not db.get(WindowDataset,id): raise HTTPException(404,'数据集不存在')
 q=select(SensorWindow).where(SensorWindow.dataset_id==id).order_by(SensorWindow.reference)
 if limit:q=q.limit(limit)
 return [row(x) for x in db.scalars(q)]
def create_dataset(db,data,user):
 if db.scalar(select(WindowDataset).where(WindowDataset.name==data.name)): raise HTTPException(409,'数据集名称已存在')
 refs=[x.reference for x in data.windows]
 if len(refs)!=len(set(refs)): raise HTTPException(422,'窗口reference重复')
 if min(sum(x.label==c for x in data.windows) for c in (0,1))<20: raise HTTPException(422,'每类至少20窗口')
 obj=WindowDataset(name=data.name,filename=data.filename,description=data.description);db.add(obj);db.flush()
 db.add_all([SensorWindow(dataset_id=obj.id,**x.model_dump()) for x in data.windows]);db.commit();record(db,user.email,'dataset.import',{'dataset_id':obj.id,'rows':len(refs)});return row(obj)
