from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,DateTime
from src.config.database import Base
class WindowDataset(Base):
 __tablename__='window_datasets'
 id:Mapped[int]=mapped_column(primary_key=True)
 name:Mapped[str]=mapped_column(String(100),unique=True)
 filename:Mapped[str]=mapped_column(String(160))
 description:Mapped[str]=mapped_column(String(500),default='')
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
