from sqlalchemy import select
from fastapi import HTTPException
from src.models import ThresholdPolicy,TrainingRun
from src.utils.serialize import row
from src.constants.enums import PolicyStatus,RunStatus
from .audit import record
def list_policies(db): return [row(x) for x in db.scalars(select(ThresholdPolicy).order_by(ThresholdPolicy.id.desc()))]
def create_policy(db,data,user):
 run=db.get(TrainingRun,data.run_id)
 if not run or run.status!=RunStatus.SUCCEEDED: raise HTTPException(422,'请选择完成的运行')
 obj=ThresholdPolicy(**data.model_dump(),threshold=run.result['recommendation']['threshold'],creator_id=user.id);db.add(obj);db.commit();record(db,user.email,'policy.created',{'policy_id':obj.id,'source':'validation_only'});return row(obj)
def approve_policy(db,id,data,user):
 obj=db.get(ThresholdPolicy,id)
 if not obj: raise HTTPException(404,'阈值策略不存在')
 if obj.status!=PolicyStatus.DRAFT: raise HTTPException(409,'只允许审核草稿')
 obj.status=data.status;obj.note=data.note;db.commit();record(db,user.email,'policy.reviewed',{'policy_id':id,'status':obj.status});return row(obj)
def get_predictions(db,id,approved=False):
 obj=db.get(ThresholdPolicy,id)
 if not obj: raise HTTPException(404,'阈值策略不存在')
 if approved and obj.status!=PolicyStatus.APPROVED: raise HTTPException(403,'仅获批策略可导出巡检参考')
 run=db.get(TrainingRun,obj.run_id)
 return obj,run.result['test_predictions']
