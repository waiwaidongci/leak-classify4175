from sqlalchemy import select,update
from fastapi import HTTPException
from src.models import InspectionReview,ReviewRevision,User
from src.utils.serialize import row
from src.constants.enums import PolicyStatus
from .policies import get_predictions
from .audit import record
from src.utils.locking import lock_policy

def _candidate_map(db,policy_id):
 policy,predictions=get_predictions(db,policy_id,approved=True)
 candidates={x['window_id']:x for x in predictions if x['predicted']==1}
 return policy,predictions,candidates

def _user_map(db):
 return {u.id:u.email for u in db.scalars(select(User))}

def list_reviews(db):
 out=[]
 users=_user_map(db)
 for x in db.scalars(select(InspectionReview).order_by(InspectionReview.id.desc())):
  item=row(x);item['reviewer_email']=users.get(x.reviewer_id,'');out.append(item)
 return out

def list_revisions(db,policy_id=None,window_id=None):
 stmt=select(ReviewRevision).order_by(ReviewRevision.id.asc())
 if policy_id is not None:stmt=stmt.where(ReviewRevision.policy_id==policy_id)
 if window_id is not None:stmt=stmt.where(ReviewRevision.window_id==window_id)
 users=_user_map(db);out=[]
 for x in db.scalars(stmt):
  item=row(x);item['operator_email']=users.get(x.operator_id,'');out.append(item)
 return out

def save_review(db,data,user):
 # 先锁策略行再做候选与存在性检查：并发首次记录就同一策略串行，
 # 第二人在锁释放后读到已存在记录并收到 409，而不是撞唯一约束报 500。
 policy=lock_policy(db,data.policy_id)
 if not policy:raise HTTPException(404,'阈值策略不存在')
 _,predictions,candidates=_candidate_map(db,data.policy_id)
 if data.window_id not in candidates:raise HTTPException(422,'只允许复核本策略最终留出评估中的候选窗口')
 existing=db.scalar(select(InspectionReview).where(InspectionReview.policy_id==data.policy_id,InspectionReview.window_id==data.window_id))
 if existing:raise HTTPException(409,'该策略窗口已记录复核，请使用结论更正并填写原因')
 obj=InspectionReview(policy_id=data.policy_id,window_id=data.window_id,verdict=data.verdict,note=data.note,reviewer_id=user.id,version=1)
 db.add(obj);db.flush()
 db.add(ReviewRevision(review_id=obj.id,policy_id=obj.policy_id,window_id=obj.window_id,revision_no=1,verdict=obj.verdict,note=obj.note,reason='首次现场复核',operator_id=user.id,base_version=0))
 db.commit()
 record(db,user.email,'inspection.recorded',{'policy_id':data.policy_id,'window_id':data.window_id,'verdict':data.verdict,'version':1})
 item=row(obj);item['reviewer_email']=user.email;return item

def correct_review(db,data,user):
 policy=lock_policy(db,data.policy_id)
 if not policy:raise HTTPException(404,'阈值策略不存在')
 if policy.status!=PolicyStatus.APPROVED:
  db.rollback();raise HTTPException(403,'仅获批策略可更正复核结论')
 obj=db.scalar(select(InspectionReview).where(InspectionReview.policy_id==data.policy_id,InspectionReview.window_id==data.window_id))
 if not obj:raise HTTPException(404,'该策略窗口尚无复核记录，不能更正，请先记录复核')
 if obj.version!=data.expected_version:
  db.rollback()
  raise HTTPException(409,f'复核结论已被他人更新（当前第{obj.version}版），你持有的是第{data.expected_version}版，请刷新后基于最新结论再更正')
 next_no=db.scalar(select(ReviewRevision.revision_no).where(ReviewRevision.review_id==obj.id).order_by(ReviewRevision.revision_no.desc()).limit(1)) or 0
 base=obj.version
 # 条件更新把版本冲突检测下推到行级：PostgreSQL 与 SQLite 均保证
 # 两人基于同一旧版本更正时只有一人成功，另一人影响 0 行并收到冲突提示。
 result=db.execute(update(InspectionReview)
  .where(InspectionReview.id==obj.id,InspectionReview.version==data.expected_version)
  .values(verdict=data.verdict,note=data.note,reviewer_id=user.id,version=data.expected_version+1))
 if result.rowcount!=1:
  db.rollback()
  raise HTTPException(409,f'复核结论已被他人更新（你持有的是第{data.expected_version}版），请刷新后基于最新结论再更正')
 db.add(ReviewRevision(review_id=obj.id,policy_id=obj.policy_id,window_id=obj.window_id,revision_no=next_no+1,verdict=data.verdict,note=data.note,reason=data.reason,operator_id=user.id,base_version=base))
 db.commit()
 record(db,user.email,'inspection.corrected',{'policy_id':data.policy_id,'window_id':data.window_id,'from_version':base,'to_version':base+1,'verdict':data.verdict,'reason':data.reason})
 db.refresh(obj)
 item=row(obj);item['reviewer_email']=user.email;return item

def reviews_for_policy(db,policy_id):
 # 封存事务内调用：与策略行锁同事务，读取同一时点的当前结论。
 result={}
 for r in db.scalars(select(InspectionReview).where(InspectionReview.policy_id==policy_id)):
  result[r.window_id]={'verdict':r.verdict,'note':r.note,'version':r.version,'reviewer_id':r.reviewer_id}
 return result
