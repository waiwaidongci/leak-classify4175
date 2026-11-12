import os
DB_PATH='/tmp/gb_review_test.db'
if os.path.exists(DB_PATH):os.remove(DB_PATH)
os.environ['DATABASE_URL']='sqlite:///'+DB_PATH+'?timeout=30'
os.environ['JWT_SECRET']='gb-review-secret'
os.environ['SEED_DEMO']='false'
import pytest
from fastapi.testclient import TestClient
from src.config.migrate import ensure_schema
from src.config.database import SessionLocal
from src.models import (User,WindowDataset,SensorWindow,TrainingRun,ThresholdPolicy,
 InspectionReview,ReviewRevision,PolicyArchive,AuditLog)
from src.utils.security import hash_password

@pytest.fixture(scope='session')
def client():
 ensure_schema()
 db=SessionLocal()
 if not db.get(User,1):
  db.add_all([
   User(email='admin@chengwan.demo',name='负责人',role='admin',password_hash=hash_password('pw')),
   User(email='analyst@chengwan.demo',name='分析师甲',role='analyst',password_hash=hash_password('pw')),
   User(email='analyst2@chengwan.demo',name='分析师乙',role='analyst',password_hash=hash_password('pw')),
   User(email='viewer@chengwan.demo',name='观察员',role='viewer',password_hash=hash_password('pw'))])
  db.commit()
 from src.main import app
 with TestClient(app) as c:
  yield c
 db.close()

def login(client,email):
 r=client.post('/auth/login',json={'email':email,'password':'pw'})
 assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}

@pytest.fixture
def tokens(client):
 return {'admin':login(client,'admin@chengwan.demo'),
  'analyst':login(client,'analyst@chengwan.demo'),
  'analyst2':login(client,'analyst2@chengwan.demo'),
  'viewer':login(client,'viewer@chengwan.demo')}

@pytest.fixture(autouse=True)
def fresh_world():
 # 每个测试重建业务数据，保证策略状态、复核与封存完全隔离。
 db=SessionLocal()
 for m in (PolicyArchive,ReviewRevision,InspectionReview,ThresholdPolicy,TrainingRun,SensorWindow,WindowDataset,AuditLog):
  db.query(m).delete()
 db.commit()
 admin=db.scalar(__import__('sqlalchemy').select(User).where(User.role=='admin'))
 ds=WindowDataset(name='测试数据集',filename='demo.csv',description='测试');db.add(ds);db.flush()
 windows=[SensorWindow(dataset_id=ds.id,reference=f'CW-T{i+1:03d}',
   features={'night_flow':1.0+i,'pressure_drop':.2,'acoustic_energy':3.0,
    'flow_variation':.1,'pipe_age':10.0,'ambient_temp':18.0},label=i%2) for i in range(7)]
 db.add_all(windows);db.flush()
 predictions=[{'window_id':w.id,'reference':w.reference,'probability':0.5+0.05*i,'predicted':1 if i<5 else 0} for i,w in enumerate(windows)]
 run=TrainingRun(name='测试运行',dataset_id=ds.id,status='succeeded',
  config={'feature_sets':[['night_flow']],'c_values':[1.0],'false_negative_cost':8.0,'false_positive_cost':1.0},
  result={'recommendation':{'threshold':0.62},'test_predictions':predictions},creator_id=admin.id)
 db.add(run);db.flush()
 policy=ThresholdPolicy(name='测试策略',run_id=run.id,threshold=0.62,note='测试策略',creator_id=admin.id)
 db.add(policy);db.commit()
 yield
 db.close()

@pytest.fixture
def policy_id(client):
 return client.get('/policies',headers=login(client,'admin@chengwan.demo')).json()[0]['id']

@pytest.fixture
def approved_policy(client,tokens,policy_id):
 r=client.patch(f'/policies/{policy_id}/approval',headers=tokens['admin'],json={'status':'approved','note':'审批通过用于测试'})
 assert r.status_code==200,r.text
 return policy_id

@pytest.fixture
def candidate_window(client,tokens,approved_policy):
 preds=[p for p in client.get(f'/policies/{approved_policy}/predictions',headers=tokens['admin']).json() if p['predicted']==1]
 return preds[0]['window_id']
