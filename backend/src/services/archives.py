import hashlib,json
from sqlalchemy import select
from fastapi import HTTPException
from src.models import PolicyArchive,User
from src.utils.serialize import row
from src.constants.enums import PolicyStatus
from src.utils.locking import lock_policy
from .policies import get_predictions
from .reviews import reviews_for_policy
from .audit import record

def _hash(content):
 blob=json.dumps(content,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
 return hashlib.sha256(blob).hexdigest()

def _build_snapshot(db,policy,predictions,note):
 reviews=reviews_for_policy(db,policy.id)
 candidates=[]
 for p in predictions:
  if p['predicted']!=1:continue
  rev=reviews.get(p['window_id'])
  candidates.append({'window_id':p['window_id'],'reference':p['reference'],'probability':p['probability'],
   'verdict':rev['verdict'] if rev else 'pending',
   'review_note':rev['note'] if rev else '',
   'review_version':rev['version'] if rev else 0})
 candidates.sort(key=lambda x:x['window_id'])
 return {'archive_format':1,'policy_id':policy.id,'policy_name':policy.name,
  'threshold':policy.threshold,'sealed_note':note,
  'candidate_count':len(candidates),
  'reviewed_count':sum(1 for c in candidates if c['review_version']>0),
  'candidates':candidates}

def create_archive(db,id,data,user):
 # 与并发更正抢同一把策略行锁：封存期间结论冻结，快照保持同一时点。
 policy=lock_policy(db,id)
 if not policy:raise HTTPException(404,'阈值策略不存在')
 if policy.status!=PolicyStatus.APPROVED:
  db.rollback();raise HTTPException(403,'仅获批策略可封存巡检名单')
 _,predictions=get_predictions(db,id)
 content=_build_snapshot(db,policy,predictions,data.note)
 digest=_hash(content)
 seq=db.query(PolicyArchive).filter(PolicyArchive.policy_id==id).count()
 archive_no=f'CW-SEAL-{id:03d}-{seq+1:03d}'
 obj=PolicyArchive(archive_no=archive_no,policy_id=id,policy_name=policy.name,threshold=policy.threshold,
  content=content,content_hash=digest,candidate_count=content['candidate_count'],
  reviewed_count=content['reviewed_count'],creator_id=user.id)
 db.add(obj);db.flush()
 # 名单快照在单一事务内提交：任一步失败整体回滚，不留半份名单。
 db.commit()
 # 审计留痕在主事务提交后独立记录，避免留痕失败回滚已成功的封存。
 record(db,user.email,'archive.sealed',{'archive_id':obj.id,'archive_no':archive_no,'policy_id':id,
  'candidate_count':obj.candidate_count,'reviewed_count':obj.reviewed_count,'content_hash':digest})
 return _require(db,obj.id)

def list_archives(db):
 users={u.id:u.email for u in db.scalars(select(User))}
 out=[]
 for x in db.scalars(select(PolicyArchive).order_by(PolicyArchive.id.desc())):
  item=row(x);item.pop('content',None);item['creator_email']=users.get(x.creator_id,'');out.append(item)
 return out

def _require(db,archive_id):
 obj=db.get(PolicyArchive,archive_id)
 if not obj:raise HTTPException(404,'封存名单不存在')
 if _hash(obj.content)!=obj.content_hash:raise HTTPException(500,'封存内容校验未通过，名单可能已被篡改')
 return obj

def serialize(obj,db):
 item=row(obj)
 operator=db.get(User,obj.creator_id)
 item['creator_email']=operator.email if operator else ''
 return item

def get_archive(db,archive_id):
 return _require(db,archive_id)
