def test_review_correction_history_and_conflict(client,tokens,approved_policy,candidate_window):
 admin,analyst,a2,viewer=tokens['admin'],tokens['analyst'],tokens['analyst2'],tokens['viewer']
 pid,wid=approved_policy,candidate_window
 # viewer 只读，写入被拒
 r=client.post('/reviews',headers=viewer,json={'policy_id':pid,'window_id':wid,'verdict':'confirmed','note':'观察员尝试'})
 assert r.status_code==403
 # 非候选窗口不可复核
 r=client.post('/reviews',headers=analyst,json={'policy_id':pid,'window_id':999999,'verdict':'confirmed','note':'x'})
 assert r.status_code==422
 # 首次复核
 r=client.post('/reviews',headers=analyst,json={'policy_id':pid,'window_id':wid,'verdict':'confirmed','note':'初判确认漏点'})
 assert r.status_code==201,r.text
 first=r.json();assert first['version']==1
 # 重复直接记录被拒，引导走更正
 r=client.post('/reviews',headers=analyst,json={'policy_id':pid,'window_id':wid,'verdict':'false_alarm','note':'再记一次'})
 assert r.status_code==409
 # 更正必须带原因
 r=client.post('/reviews/corrections',headers=analyst,json={'policy_id':pid,'window_id':wid,'expected_version':1,'verdict':'false_alarm','note':'现场开挖未见漏损','reason':''})
 assert r.status_code==422
 # 基于 v1 更正到 v2
 r=client.post('/reviews/corrections',headers=a2,json={'policy_id':pid,'window_id':wid,'expected_version':1,'verdict':'false_alarm','note':'开挖未见漏损','reason':'压力复测正常，初判受相邻施工干扰'})
 assert r.status_code==201,r.text
 v2=r.json();assert v2['version']==2 and v2['verdict']=='false_alarm' and v2['reviewer_id']!=first['reviewer_id']
 # 另一人仍基于旧 v1 更正 → 冲突，不覆盖
 r=client.post('/reviews/corrections',headers=analyst,json={'policy_id':pid,'window_id':wid,'expected_version':1,'verdict':'confirmed','note':'坚持确认','reason':'另一组现场证据'})
 assert r.status_code==409
 assert '冲突' in r.json()['detail'] or '更新' in r.json()['detail']
 # 再基于 v2 更正到 v3
 r=client.post('/reviews/corrections',headers=analyst,json={'policy_id':pid,'window_id':wid,'expected_version':2,'verdict':'confirmed','note':'二次开挖确认接口渗漏','reason':'扩大开挖后发现接口渗漏'})
 assert r.status_code==201
 assert r.json()['version']==3
 # 历次结论、操作者、原因、时间全部保留
 hist=client.get(f'/reviews/history?policy_id={pid}&window_id={wid}',headers=admin).json()
 assert len(hist)==3
 assert [h['revision_no'] for h in hist]==[1,2,3]
 assert [h['verdict'] for h in hist]==['confirmed','false_alarm','confirmed']
 assert hist[0]['reason']=='首次现场复核'
 assert hist[1]['reason'].startswith('压力复测')
 assert hist[2]['base_version']==2
 assert all(h['operator_email'] for h in hist)
 assert all(h['created_at'] for h in hist)
 # 当前列表反映最新结论且带操作者邮箱
 cur=[x for x in client.get('/reviews',headers=admin).json() if x['policy_id']==pid and x['window_id']==wid][0]
 assert cur['version']==3 and cur['verdict']=='confirmed' and cur['reviewer_email']
 # 更正留痕
 audit=client.get('/audit',headers=admin).json()
 assert any(a['action']=='inspection.corrected' and a['detail'].get('from_version')==2 for a in audit)
 assert any(a['action']=='inspection.recorded' for a in audit)

def test_correction_requires_existing_review_and_approved(client,tokens,policy_id):
 analyst=tokens['analyst']
 preds=client.get(f'/policies/{policy_id}/predictions',headers=analyst).json()
 wid=[p['window_id'] for p in preds if p['predicted']==1][0]
 # 草稿策略不可更正
 r=client.post('/reviews/corrections',headers=analyst,json={'policy_id':policy_id,'window_id':wid,'expected_version':1,'verdict':'confirmed','note':'n','reason':'r'})
 assert r.status_code==403
