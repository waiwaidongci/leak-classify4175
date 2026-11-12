from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers,admins
from src.controllers.export import export_inspections
from src.schemas.policy import PolicyInput,ApprovalInput
from src.services import policies
router=APIRouter()
@router.get('/policies')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return policies.list_policies(db)
@router.post('/policies',status_code=201)
def create(data:PolicyInput,db:Session=Depends(get_db),user=Depends(writers)):return policies.create_policy(db,data,user)
@router.patch('/policies/{id}/approval')
def approval(id:int,data:ApprovalInput,db:Session=Depends(get_db),user=Depends(admins)):return policies.approve_policy(db,id,data,user)
@router.get('/policies/{id}/predictions')
def predictions(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return policies.get_predictions(db,id)[1]
@router.get('/policies/{id}/export')
def export(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return export_inspections(db,id)
