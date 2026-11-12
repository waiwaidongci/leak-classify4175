import json
from pathlib import Path
from celery import Celery
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.config.database import SessionLocal
from src.models import TrainingRun
from src.services.datasets import get_windows
from src.services.training import train_model
from src.services.audit import record
from src.constants.enums import RunStatus
app=Celery('leak_classify',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
@app.task(name='leak.train',soft_time_limit=180,time_limit=210)
def train_run(id):
 with SessionLocal() as db:
  run=db.get(TrainingRun,id)
  if not run or run.status==RunStatus.SUCCEEDED:return
  run.status=RunStatus.RUNNING;db.commit()
  try:
   result=train_model(get_windows(db,run.dataset_id),run.config)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'training-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False))
   run.result=result;run.status=RunStatus.SUCCEEDED;run.error=None;db.commit();record(db,'worker','training.succeeded',{'run_id':id,'test_auc':result['test']['auc']})
  except Exception as e:
   db.rollback();run=db.get(TrainingRun,id);run.status=RunStatus.FAILED;run.error=str(e)[:1000];db.commit();record(db,'worker','training.failed',{'run_id':id,'error':run.error})
