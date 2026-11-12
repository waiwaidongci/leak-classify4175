from pydantic import BaseModel,Field
from typing import Literal
VERDICTS=('pending','confirmed','false_alarm')
class ReviewInput(BaseModel):
 policy_id:int=Field(gt=0)
 window_id:int=Field(gt=0)
 verdict:Literal['pending','confirmed','false_alarm']
 note:str=Field(min_length=1,max_length=500)
class ReviewCorrection(BaseModel):
 policy_id:int=Field(gt=0)
 window_id:int=Field(gt=0)
 expected_version:int=Field(ge=1)
 verdict:Literal['pending','confirmed','false_alarm']
 note:str=Field(min_length=1,max_length=500)
 reason:str=Field(min_length=1,max_length=500)
