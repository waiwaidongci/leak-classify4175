from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.services import datasets
from src.schemas.dataset import DatasetInput
from src.constants.features import FEATURES
router=APIRouter()
@router.get('/features')
def features(user=Depends(current_user)):return FEATURES
@router.get('/datasets')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return datasets.list_datasets(db)
@router.post('/datasets',status_code=201)
def create(data:DatasetInput,db:Session=Depends(get_db),user=Depends(writers)):return datasets.create_dataset(db,data,user)
@router.get('/datasets/{id}/windows')
def windows(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return datasets.get_windows(db,id,100)
