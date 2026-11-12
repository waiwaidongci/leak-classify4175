from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Float,ForeignKey,DateTime,JSON,Integer
from src.config.database import Base
def now():return datetime.now(timezone.utc)
class PolicyArchive(Base):
 __tablename__='policy_archives'
 id:Mapped[int]=mapped_column(primary_key=True)
 archive_no:Mapped[str]=mapped_column(String(40),unique=True)
 policy_id:Mapped[int]=mapped_column(ForeignKey('threshold_policies.id'))
 policy_name:Mapped[str]=mapped_column(String(100))
 threshold:Mapped[float]=mapped_column(Float)
 content:Mapped[dict]=mapped_column(JSON)
 content_hash:Mapped[str]=mapped_column(String(64))
 candidate_count:Mapped[int]=mapped_column(Integer)
 reviewed_count:Mapped[int]=mapped_column(Integer)
 creator_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
