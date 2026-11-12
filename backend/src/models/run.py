from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,JSON,ForeignKey,DateTime
from src.config.database import Base
class TrainingRun(Base):
 __tablename__='training_runs'
 id:Mapped[int]=mapped_column(primary_key=True)
 dataset_id:Mapped[int]=mapped_column(ForeignKey('window_datasets.id'))
 name:Mapped[str]=mapped_column(String(100))
 status:Mapped[str]=mapped_column(String(20),default='queued')
 config:Mapped[dict]=mapped_column(JSON)
 result:Mapped[dict]=mapped_column(JSON,default=dict)
 error:Mapped[str|None]=mapped_column(String(1000),nullable=True)
 creator_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
