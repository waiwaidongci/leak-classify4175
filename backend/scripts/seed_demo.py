import json
import numpy as np
from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import *
from src.utils.security import hash_password
from src.constants.features import FEATURES
from src.services.datasets import get_windows
from src.services.training import train_model

def seed():
 Base.metadata.create_all(engine)
 with SessionLocal() as db:
  for role,name in [('admin','沈泊 · 水务负责人'),('analyst','周沅 · 工况分析师'),('viewer','林川 · 巡检观察员')]:
   email=role+'@chengwan.demo'
   if not db.scalar(select(User).where(User.email==email)):db.add(User(email=email,name=name,role=role,password_hash=hash_password('Chengwan2026!')))
  db.commit();dataset=db.scalar(select(WindowDataset).where(WindowDataset.name=='澄湾夜间工况 · 1500窗口'))
  if not dataset:
   dataset=WindowDataset(name='澄湾夜间工况 · 1500窗口',filename='cw-pressure-windows.csv',description='匿名管段独立夜间窗口，固定seed73；回顾性合成样本。');db.add(dataset);db.flush()
   rng=np.random.default_rng(73);Z=rng.normal(size=(1500,6));noise=rng.normal(0,.15,1500)
   logit=-1.9+1.0*Z[:,0]+1.1*Z[:,1]+.8*Z[:,2]+.3*Z[:,3]+.2*Z[:,4]+noise
   probability=1/(1+np.exp(-logit));y=(rng.random(1500)<probability).astype(int)
   X=np.c_[12+3*Z[:,0],5+1.8*Z[:,1],40+10*Z[:,2],.3+.08*Z[:,3],20+4*Z[:,4],18+5*Z[:,5]]
   db.add_all([SensorWindow(dataset_id=dataset.id,reference=f'CW-W{i+1:04d}',features={f:round(float(v),5) for f,v in zip(FEATURES,X[i])},label=int(y[i])) for i in range(1500)]);db.commit()
  if not db.scalar(select(TrainingRun).where(TrainingRun.name=='夜间漏损基准研究')):
   admin=db.scalar(select(User).where(User.role=='admin'));config={'feature_sets':[list(FEATURES)[:3],list(FEATURES)],'c_values':[.1,1.],'false_negative_cost':8.,'false_positive_cost':1.}
   result=train_model(get_windows(db,dataset.id),config);run=TrainingRun(name='夜间漏损基准研究',dataset_id=dataset.id,status='succeeded',config=config,result=result,creator_id=admin.id);db.add(run);db.flush();db.add(ThresholdPolicy(name='夜间先复核 · 基准草案',run_id=run.id,threshold=result['recommendation']['threshold'],note='候选仅供人工复核，未自动派工。',creator_id=admin.id));db.add(AuditLog(actor='seed',action='demo.created',detail={'seed':73,'windows':1500}));db.commit()
  counts={t.__tablename__:db.scalar(select(func.count()).select_from(t)) for t in [User,WindowDataset,SensorWindow,TrainingRun,ThresholdPolicy,InspectionReview]};print(json.dumps(counts));return counts
if __name__=='__main__':seed()
