from pydantic import BaseModel,Field
from typing import Literal
class ReviewInput(BaseModel):
 policy_id:int=Field(gt=0)
 window_id:int=Field(gt=0)
 verdict:Literal['pending','confirmed','false_alarm']
 note:str=Field(min_length=1,max_length=500)
