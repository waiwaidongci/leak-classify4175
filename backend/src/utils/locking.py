from sqlalchemy import select
from src.models import ThresholdPolicy
def lock_policy(db,policy_id):
 # 行级串行化：PostgreSQL 以 SELECT ... FOR UPDATE 锁定策略行，
 # 使并发更正/封存就同一策略排队，保证同一时点快照。
 # SQLite 不支持 FOR UPDATE，靠单写者事务与版本号保证一致。
 query=select(ThresholdPolicy).where(ThresholdPolicy.id==policy_id)
 if db.bind.dialect.name!='sqlite':query=query.with_for_update()
 return db.scalars(query).first()
