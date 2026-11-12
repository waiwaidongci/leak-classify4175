from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Float,ForeignKey,DateTime
from src.config.database import Base
class ThresholdPolicy(Base):
 __tablename__='threshold_policies'
 id:Mapped[int]=mapped_column(primary_key=True)
 run_id:Mapped[int]=mapped_column(ForeignKey('training_runs.id'))
 name:Mapped[str]=mapped_column(String(100))
 threshold:Mapped[float]=mapped_column(Float)
 status:Mapped[str]=mapped_column(String(20),default='draft')
 note:Mapped[str]=mapped_column(String(500),default='')
 creator_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
