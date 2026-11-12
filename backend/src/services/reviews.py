from sqlalchemy import select
from fastapi import HTTPException
from src.models import InspectionReview
from src.utils.serialize import row
from .policies import get_predictions
from .audit import record
def list_reviews(db):return [row(x) for x in db.scalars(select(InspectionReview).order_by(InspectionReview.id.desc()))]
def save_review(db,data,user):
 policy,predictions=get_predictions(db,data.policy_id,approved=True)
 candidates={x['window_id']:x for x in predictions if x['predicted']==1}
 if data.window_id not in candidates: raise HTTPException(422,'只允许复核本策略最终留出评估中的候选窗口')
 if db.scalar(select(InspectionReview).where(InspectionReview.policy_id==data.policy_id,InspectionReview.window_id==data.window_id)): raise HTTPException(409,'该策略窗口已记录复核')
 obj=InspectionReview(**data.model_dump(),reviewer_id=user.id);db.add(obj);db.commit();record(db,user.email,'inspection.recorded',{'policy_id':data.policy_id,'window_id':data.window_id,'verdict':data.verdict});return row(obj)
