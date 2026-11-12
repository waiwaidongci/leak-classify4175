from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,JSON,Integer,ForeignKey,UniqueConstraint
from src.config.database import Base
class SensorWindow(Base):
 __tablename__='sensor_windows'
 __table_args__=(UniqueConstraint('dataset_id','reference'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 dataset_id:Mapped[int]=mapped_column(ForeignKey('window_datasets.id'))
 reference:Mapped[str]=mapped_column(String(80))
 features:Mapped[dict]=mapped_column(JSON)
 label:Mapped[int]=mapped_column(Integer)
