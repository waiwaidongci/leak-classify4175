from pydantic import BaseModel,Field,model_validator
from src.constants.features import FEATURES
class WindowInput(BaseModel):
 reference:str=Field(min_length=1,max_length=80)
 features:dict[str,float]
 label:int=Field(ge=0,le=1)
 @model_validator(mode='after')
 def validate_features(self):
  import math
  if set(self.features)!=set(FEATURES): raise ValueError('每个窗口必须恰有六个允许特征，禁止label作为特征')
  if not all(math.isfinite(x) for x in self.features.values()): raise ValueError('特征必须为有限数值')
  return self
class DatasetInput(BaseModel):
 name:str=Field(min_length=1,max_length=100)
 filename:str=Field(min_length=1,max_length=160)
 description:str=Field(default='',max_length=500)
 windows:list[WindowInput]=Field(min_length=100,max_length=5000)
