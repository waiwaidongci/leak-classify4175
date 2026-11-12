from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,ForeignKey,DateTime,UniqueConstraint,Integer
from src.config.database import Base
def now():return datetime.now(timezone.utc)
class InspectionReview(Base):
 __tablename__='inspection_reviews'
 __table_args__=(UniqueConstraint('policy_id','window_id'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 policy_id:Mapped[int]=mapped_column(ForeignKey('threshold_policies.id'))
 window_id:Mapped[int]=mapped_column(ForeignKey('sensor_windows.id'))
 verdict:Mapped[str]=mapped_column(String(30))
 note:Mapped[str]=mapped_column(String(500))
 reviewer_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 version:Mapped[int]=mapped_column(Integer,default=1)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
 updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,onupdate=now)
class ReviewRevision(Base):
 __tablename__='review_revisions'
 id:Mapped[int]=mapped_column(primary_key=True)
 review_id:Mapped[int]=mapped_column(ForeignKey('inspection_reviews.id'))
 policy_id:Mapped[int]=mapped_column(ForeignKey('threshold_policies.id'))
 window_id:Mapped[int]=mapped_column(ForeignKey('sensor_windows.id'))
 revision_no:Mapped[int]=mapped_column(Integer)
 verdict:Mapped[str]=mapped_column(String(30))
 note:Mapped[str]=mapped_column(String(500))
 reason:Mapped[str]=mapped_column(String(500),default='')
 operator_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 base_version:Mapped[int]=mapped_column(Integer)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
