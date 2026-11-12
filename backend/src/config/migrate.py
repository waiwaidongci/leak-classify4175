from sqlalchemy import inspect,text
from src.config.database import engine,Base
import src.models  # noqa: F401  注册全部表到 metadata
def ensure_schema():
 # create_all 负责新表（review_revisions、policy_archives）；
 # 已存在的 inspection_reviews 需补齐更正功能列，metadata 不会自动 ALTER。
 Base.metadata.create_all(engine)
 inspector=inspect(engine)
 dialect=engine.dialect.name
 ts_type='TIMESTAMP' if dialect=='sqlite' else 'TIMESTAMP WITH TIME ZONE'
 existing={c['name'] for c in inspector.get_columns('inspection_reviews')}
 with engine.begin() as conn:
  if 'version' not in existing:
   conn.execute(text('ALTER TABLE inspection_reviews ADD COLUMN version INTEGER DEFAULT 1'))
   conn.execute(text('UPDATE inspection_reviews SET version=1'))
  if 'updated_at' not in existing:
   conn.execute(text(f'ALTER TABLE inspection_reviews ADD COLUMN updated_at {ts_type}'))
   conn.execute(text('UPDATE inspection_reviews SET updated_at=created_at WHERE updated_at IS NULL'))
  if inspector.has_table('review_revisions'):
   # 为升级前已存在的复核补登第1版历史，保证“历次结论”完整可溯。
   conn.execute(text('''INSERT INTO review_revisions
    (review_id,policy_id,window_id,revision_no,verdict,note,reason,operator_id,base_version,created_at)
    SELECT r.id,r.policy_id,r.window_id,1,r.verdict,r.note,'',r.reviewer_id,0,r.created_at
    FROM inspection_reviews r
    WHERE NOT EXISTS (SELECT 1 FROM review_revisions h WHERE h.review_id=r.id)'''))
