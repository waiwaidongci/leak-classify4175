from pydantic import BaseModel,Field
class ArchiveInput(BaseModel):
 note:str=Field(max_length=500,default='')
