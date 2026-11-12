import io,csv,hashlib,json
from src.config.database import SessionLocal
from src.models import SensorWindow

def test_archive_snapshot_immutable_and_reflects_corrections(client,tokens,approved_policy,candidate_window):
 admin,analyst=tokens['admin'],tokens['analyst']
 pid=approved_policy
 wid=candidate_window
 # 首次复核后封存第一版名单
 client.post('/reviews',headers=analyst,json={'policy_id':pid,'window_id':wid,'verdict':'confirmed','note':'初判'})
 r=client.post(f'/policies/{pid}/seal',headers=analyst,json={'note':'第一次封存'})
 assert r.status_code==201,r.text
 a1=r.json()
 assert a1['archive_no'].startswith(f'CW-SEAL-{pid:03d}-')
 assert a1['candidate_count']==5 and a1['reviewed_count']==1
 # 详情含完整快照
 d1=client.get(f"/archives/{a1['id']}",headers=admin).json()
 assert d1['archive_no']==a1['archive_no']
 snap1={c['window_id']:c for c in d1['content']['candidates']}
 assert snap1[wid]['verdict']=='confirmed' and snap1[wid]['review_version']==1
 # 下载第一版 CSV 内容
 dl1=client.get(f"/archives/{a1['id']}/download",headers=admin)
 assert dl1.status_code==200
 rows1=list(csv.reader(io.StringIO(dl1.text.lstrip('﻿'))))
 assert rows1[0][3]=='人工复核结论'
 assert len(rows1)==6
 # 更正结论后再次封存：新名单反映更正
 r=client.post('/reviews/corrections',headers=analyst,json={'policy_id':pid,'window_id':wid,'expected_version':1,'verdict':'false_alarm','note':'开挖未见','reason':'复测正常'})
 assert r.status_code==201
 r=client.post(f'/policies/{pid}/seal',headers=analyst,json={'note':'第二次封存'})
 assert r.status_code==201
 a2=r.json();assert a2['id']!=a1['id']
 snap2={c['window_id']:c for c in client.get(f"/archives/{a2['id']}",headers=admin).json()['content']['candidates']}
 assert snap2[wid]['verdict']=='false_alarm' and snap2[wid]['review_version']==2
 # 按编号重新下载第一版：内容不变（候选与结论都保持旧时点）
 dl1_again=client.get(f"/archives/{a1['id']}/download",headers=admin).text
 assert dl1_again==dl1.text
 d1_again=client.get(f"/archives/{a1['id']}",headers=admin).json()
 assert d1_again['content']==d1['content']
 # 第二版下载包含新结论且行数一致
 rows2=list(csv.reader(io.StringIO(client.get(f"/archives/{a2['id']}/download",headers=admin).text.lstrip('﻿'))))
 assert len(rows2)==6
 assert any(r_[0]==snap1[wid]['reference'] and r_[3]=='false_alarm' for r_ in rows2[1:])
 assert any(r_[0]==snap1[wid]['reference'] and r_[3]=='confirmed' for r_ in rows1[1:])
 # 名单列表不含大块 content，但含哈希与编号
 listing=client.get('/archives',headers=admin).json()
 ids={x['id'] for x in listing}
 assert {a1['id'],a2['id']}<=ids
 assert all('content' not in x for x in listing)
 assert all(len(x['content_hash'])==64 for x in listing)
 # 审计含封存动作
 audit=client.get('/audit',headers=admin).json()
 seals=[a for a in audit if a['action']=='archive.sealed']
 assert {s['detail']['archive_no'] for s in seals}>={a1['archive_no'],a2['archive_no']}

def test_archive_permissions_and_seal_rules(client,tokens,policy_id):
 viewer,admin=tokens['viewer'],tokens['admin']
 # 草稿策略不可封存
 r=client.post(f'/policies/{policy_id}/seal',headers=tokens['analyst'],json={'note':''})
 assert r.status_code==403
 # viewer 不可封存
 r=client.post(f'/policies/{policy_id}/seal',headers=viewer,json={'note':''})
 assert r.status_code==403
 # viewer 可读取列表与详情
 assert client.get('/archives',headers=viewer).status_code==200
 assert client.get('/policies',headers=viewer).status_code==200

def test_tamper_detection_and_hash(client,tokens,approved_policy):
 analyst=tokens['analyst']
 r=client.post(f'/policies/{approved_policy}/seal',headers=analyst,json={'note':'防篡改封存'})
 assert r.status_code==201
 aid=r.json()['id']
 from src.config.database import SessionLocal
 from src.models import PolicyArchive
 db=SessionLocal()
 obj=db.get(PolicyArchive,aid)
 original=obj.content
 tampered=json.loads(json.dumps(original))
 tampered['candidates'][0]['verdict']='confirmed'
 obj.content=tampered;db.commit();db.close()
 # 哈希校验失败 → 500（中间件统一错误），绝不静默返回篡改内容
 r=client.get(f'/archives/{aid}',headers=tokens['admin'])
 assert r.status_code==500
 r=client.get(f'/archives/{aid}/download',headers=tokens['admin'])
 assert r.status_code==500
 # 恢复后可正常读取，且哈希算法与服务一致
 db=SessionLocal();obj=db.get(PolicyArchive,aid);obj.content=original;db.commit();db.close()
 r=client.get(f'/archives/{aid}',headers=tokens['admin']);assert r.status_code==200
 blob=json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
 assert hashlib.sha256(blob).hexdigest()==r.json()['content_hash']

def test_live_export_still_reflects_current_verdict(client,tokens,approved_policy,candidate_window):
 analyst=tokens['analyst'];pid=approved_policy;wid=candidate_window
 client.post('/reviews',headers=analyst,json={'policy_id':pid,'window_id':wid,'verdict':'pending','note':'待判'})
 client.post('/reviews/corrections',headers=analyst,json={'policy_id':pid,'window_id':wid,'expected_version':1,'verdict':'confirmed','note':'再更正','reason':'终判确认'})
 r=client.get(f'/policies/{pid}/export',headers=analyst)
 assert r.status_code==200
 rows=list(csv.reader(io.StringIO(r.text.lstrip('﻿'))))
 ref=[p for p in client.get(f'/policies/{pid}/predictions',headers=analyst).json() if p['window_id']==wid][0]['reference']
 assert any(x[0]==ref and x[3]=='confirmed' for x in rows[1:])

def test_training_labels_unaffected(client,tokens,approved_policy,candidate_window):
 from src.config.database import SessionLocal
 from src.models import SensorWindow
 before={w.id:w.label for w in db_all_windows()}
 client.post('/reviews',headers=tokens['analyst'],json={'policy_id':approved_policy,'window_id':candidate_window,'verdict':'confirmed','note':'初判'})
 client.post('/reviews/corrections',headers=tokens['analyst'],json={'policy_id':approved_policy,'window_id':candidate_window,'expected_version':1,'verdict':'false_alarm','note':'n','reason':'r'})
 after={w.id:w.label for w in db_all_windows()}
 assert before==after

def db_all_windows():
 from src.config.database import SessionLocal
 db=SessionLocal()
 try:return db.query(SensorWindow).all()
 finally:db.close()
