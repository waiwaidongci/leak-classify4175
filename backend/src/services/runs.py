from sqlalchemy import select
from fastapi import HTTPException
from src.models import TrainingRun,WindowDataset
from src.utils.serialize import row
from src.constants.enums import RunStatus
from .audit import record
def list_runs(db): return [row(x) for x in db.scalars(select(TrainingRun).order_by(TrainingRun.id.desc()))]
def get_run(db,id):
 obj=db.get(TrainingRun,id)
 if not obj: raise HTTPException(404,'训练运行不存在')
 return obj
def create_run(db,data,user):
 if not db.get(WindowDataset,data.dataset_id): raise HTTPException(404,'数据集不存在')
 config=data.model_dump(exclude={'name','dataset_id'})
 obj=TrainingRun(dataset_id=data.dataset_id,name=data.name,config=config,creator_id=user.id);db.add(obj);db.commit()
 from src.worker import train_run
 try:train_run.delay(obj.id)
 except Exception:
  obj.status=RunStatus.FAILED;obj.error='队列不可用，请重试';db.commit();raise HTTPException(503,obj.error)
 record(db,user.email,'training.queued',{'run_id':obj.id});return row(obj)
