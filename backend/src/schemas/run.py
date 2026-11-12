from pydantic import BaseModel,Field,model_validator
from src.constants.features import FEATURES
class TrainingInput(BaseModel):
 dataset_id:int=Field(gt=0)
 name:str=Field(min_length=1,max_length=100)
 feature_sets:list[list[str]]=Field(min_length=1,max_length=3)
 c_values:list[float]=Field(min_length=1,max_length=5)
 false_negative_cost:float=Field(gt=0,le=1000,allow_inf_nan=False)
 false_positive_cost:float=Field(gt=0,le=1000,allow_inf_nan=False)
 @model_validator(mode='after')
 def validate_candidates(self):
  if any(not s or len(s)!=len(set(s)) or not set(s)<=set(FEATURES) for s in self.feature_sets): raise ValueError('只能选择非空、不重复的六个允许特征，标签不可入模')
  if any(not 0<c<=1000 for c in self.c_values): raise ValueError('C必须在(0,1000]')
  if len(set(self.c_values))!=len(self.c_values): raise ValueError('C候选不得重复')
  return self
