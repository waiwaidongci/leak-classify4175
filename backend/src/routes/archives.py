from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.controllers.export import export_archive
from src.services import archives
from src.schemas.archive import ArchiveInput
router=APIRouter()
@router.get('/archives')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return archives.list_archives(db)
@router.post('/policies/{id}/seal',status_code=201)
def seal(id:int,data:ArchiveInput,db:Session=Depends(get_db),user=Depends(writers)):return archives.serialize(archives.create_archive(db,id,data,user),db)
@router.get('/archives/{archive_id}')
def detail(archive_id:int,db:Session=Depends(get_db),user=Depends(current_user)):return archives.serialize(archives.get_archive(db,archive_id),db)
@router.get('/archives/{archive_id}/download')
def download(archive_id:int,db:Session=Depends(get_db),user=Depends(current_user)):return export_archive(db,archive_id)
