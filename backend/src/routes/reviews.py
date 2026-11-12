from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.services import reviews
from src.schemas.review import ReviewInput
router=APIRouter()
@router.get('/reviews')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return reviews.list_reviews(db)
@router.post('/reviews',status_code=201)
def create(data:ReviewInput,db:Session=Depends(get_db),user=Depends(writers)):return reviews.save_review(db,data,user)
