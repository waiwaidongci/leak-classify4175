import threading
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError,IntegrityError
from fastapi import HTTPException
from src.config.database import SessionLocal
from src.models import InspectionReview,ReviewRevision,PolicyArchive,User
from src.schemas.review import ReviewInput,ReviewCorrection
from src.schemas.archive import ArchiveInput
from src.services import reviews,archives

def _users(db):
 return db.scalars(select(User).where(User.role=='analyst')).all()

def _one_review(pid,wid,user):
 db=SessionLocal()
 try:
  reviews.save_review(db,ReviewInput(policy_id=pid,window_id=wid,verdict='confirmed',note='初判'),user)
 finally:db.close()

def _with_lock_retry(fn,*args,**kw):
 # SQLite 无行级 FOR UPDATE，写竞争会报 database is locked，
 # 并发首记还可能直接撞唯一约束；失败后用全新事务重试，
 # 重试走完整检查，过期版本/已存在记录会正确收到 409。
 # PostgreSQL 生产路径由策略行锁串行化，不会进入这些分支。
 for attempt in range(30):
  try:return fn(*args,**kw)
  except OperationalError as e:
   if 'locked' not in str(e).lower():raise
  except IntegrityError:
   pass
  import time;time.sleep(0.1)
 raise RuntimeError('sqlite 写锁等待超时')

def test_concurrent_corrections_same_base_only_one_wins(client,tokens,approved_policy,candidate_window):
 pid,wid=approved_policy,candidate_window
 db=SessionLocal();u1,u2=_users(db)[:2];db.close()
 _one_review(pid,wid,u1)
 results=[]
 def worker(user,verdict):
  def call():
   s=SessionLocal()
   try:
    return reviews.correct_review(s,ReviewCorrection(policy_id=pid,window_id=wid,
     expected_version=1,verdict=verdict,note='并发更正',reason='现场证据更新'),user)
   finally:s.close()
  try:results.append(('ok',_with_lock_retry(call)))
  except HTTPException as e:results.append(('conflict',e.status_code))
 t1=threading.Thread(target=worker,args=(u1,'false_alarm'))
 t2=threading.Thread(target=worker,args=(u2,'confirmed'))
 t1.start();t2.start();t1.join();t2.join()
 statuses=sorted(r[0] for r in results)
 assert statuses==['conflict','ok'],results
 assert [r[1] for r in results if r[0]=='conflict'][0]==409
 # 最终版本只前进一格，历史只有 初判+一次更正，没有丢失更新
 db=SessionLocal()
 try:
  cur=db.scalar(select(InspectionReview).where(InspectionReview.policy_id==pid,InspectionReview.window_id==wid))
  assert cur.version==2
  revs=db.scalars(select(ReviewRevision).where(ReviewRevision.review_id==cur.id).order_by(ReviewRevision.revision_no)).all()
  assert [r.revision_no for r in revs]==[1,2]
  assert revs[1].verdict in ('false_alarm','confirmed')
 finally:db.close()

def test_seal_and_correction_converge_to_single_point(client,tokens,approved_policy,candidate_window):
 pid,wid=approved_policy,candidate_window
 db=SessionLocal();u1,u2=_users(db)[:2];db.close()
 _one_review(pid,wid,u1)
 before=db_count_archives(pid)
 barrier=threading.Barrier(2)
 seal_out,corr_out= {},{}
 def sealer():
  barrier.wait()
  s=SessionLocal()
  try:
   seal_out['archive']=_with_lock_retry(archives.create_archive,s,pid,ArchiveInput(note='并发封存'),u1)
  except Exception as e:seal_out['err']=repr(e)
  finally:s.close()
 def corrector():
  barrier.wait()
  def call():
   s=SessionLocal()
   try:
    return reviews.correct_review(s,ReviewCorrection(policy_id=pid,window_id=wid,
     expected_version=1,verdict='false_alarm',note='并发更正',reason='交叉时点测试'),u2)
   finally:s.close()
  try:corr_out['review']=_with_lock_retry(call)
  except HTTPException as e:corr_out['err']=e.status_code
 t1=threading.Thread(target=sealer);t2=threading.Thread(target=corrector)
 t1.start();t2.start();t1.join();t2.join()
 # 封存恰好新增一份，失败不留半份
 assert db_count_archives(pid)==before+1
 assert 'err' not in seal_out,seal_out
 a=seal_out['archive']
 entry=[c for c in a.content['candidates'] if c['window_id']==wid][0]
 # 名单内部自洽：该候选要么整体停留在 v1，要么整体是 v2，不会出现半新半旧
 assert entry['review_version'] in (1,2)
 if entry['review_version']==1:assert entry['verdict']=='confirmed'
 else:assert entry['verdict']=='false_alarm'
 # 名单快照哈希自洽（读取校验逻辑不会报错）
 s=SessionLocal()
 try:assert archives.get_archive(s,a.id).content_hash==a.content_hash
 finally:s.close()

def test_failed_seal_rolls_back_without_half_archive(client,tokens,approved_policy,candidate_window,monkeypatch):
 pid=approved_policy;wid=candidate_window
 db=SessionLocal();user=_users(db)[0];db.close()
 # 先保留一条复核，验证回滚不波及既有数据
 client.post('/reviews',headers=tokens['analyst'],json={'policy_id':pid,'window_id':wid,'verdict':'confirmed','note':'既有复核'})
 before=db_count_archives(pid)
 def boom(content):raise RuntimeError('模拟封存中途失败')
 monkeypatch.setattr(archives,'_hash',boom)
 s=SessionLocal()
 with pytest.raises(RuntimeError):
  archives.create_archive(s,pid,ArchiveInput(note='应回滚'),user)
 s.close()
 # 没有留下任何半份名单；既有复核不受影响
 assert db_count_archives(pid)==before
 db=SessionLocal()
 try:assert db.scalar(select(InspectionReview).where(InspectionReview.policy_id==pid)) is not None
 finally:db.close()

def db_count_archives(pid):
 db=SessionLocal()
 try:return db.query(PolicyArchive).filter(PolicyArchive.policy_id==pid).count()
 finally:db.close()

def test_concurrent_first_reviews_serialize_to_one(client,tokens,approved_policy,candidate_window):
 pid,wid=approved_policy,candidate_window
 db=SessionLocal();u1,u2=_users(db)[:2];db.close()
 outcomes=[]
 barrier=threading.Barrier(2)
 def worker(user):
  barrier.wait()
  def call():
   s=SessionLocal()
   try:
    reviews.save_review(s,ReviewInput(policy_id=pid,window_id=wid,verdict='confirmed',note='并发首记'),user)
    return 201
   except HTTPException as e:return e.status_code
   finally:s.close()
  outcomes.append(_with_lock_retry(call))
 t1=threading.Thread(target=worker,args=(u1,));t2=threading.Thread(target=worker,args=(u2,))
 t1.start();t2.start();t1.join();t2.join()
 assert sorted(outcomes)==[201,409],outcomes
 s=SessionLocal()
 try:
  cur=s.scalar(select(InspectionReview).where(InspectionReview.policy_id==pid,InspectionReview.window_id==wid))
  assert cur.version==1
  assert s.query(ReviewRevision).filter(ReviewRevision.review_id==cur.id).count()==1
 finally:s.close()
