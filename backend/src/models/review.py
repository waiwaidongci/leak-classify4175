from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,ForeignKey,DateTime,UniqueConstraint
from src.config.database import Base
class InspectionReview(Base):
 __tablename__='inspection_reviews'
 __table_args__=(UniqueConstraint('policy_id','window_id'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 policy_id:Mapped[int]=mapped_column(ForeignKey('threshold_policies.id'))
 window_id:Mapped[int]=mapped_column(ForeignKey('sensor_windows.id'))
 verdict:Mapped[str]=mapped_column(String(30))
 note:Mapped[str]=mapped_column(String(500))
 reviewer_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
