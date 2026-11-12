import {useState} from 'react';
import type {Review,ReviewRevision,Prediction} from '../types/domain';
import {policyApi} from '../api/policies';
import {Badge} from './common/Badge';
import {VERDICTS} from '../constants/enums';
import {date} from '../utils/format';

export function CorrectionDialog({policyId,windowId,current,reference,reload,onClose}:{
 policyId:number;windowId:number;current:Review|undefined;reference:string;reload:()=>Promise<any>;onClose:()=>void}){
 const [verdict,setVerdict]=useState(current?.verdict||'pending');
 const [note,setNote]=useState(current?.note||'');
 const [reason,setReason]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [history,setHistory]=useState<ReviewRevision[]|null>(null);
 async function openHistory(){
  setBusy(true);setError('');
  try{setHistory(await policyApi.history(policyId,windowId))}
  catch(e:any){setError(e.message)}
  finally{setBusy(false)}
 }
 async function submit(e:React.FormEvent){
  e.preventDefault();
  if(!current){setError('该窗口尚未记录复核，无法更正，请先保存首次复核');return}
  setBusy(true);setError('');
  try{
   await policyApi.correct({policy_id:policyId,window_id:windowId,expected_version:current.version,verdict,note,reason});
   await reload();onClose();
  }catch(e:any){setError(e.message);setBusy(false)}
 }
 return <div className="modal-backdrop" onClick={onClose}>
  <div className="modal" onClick={e=>e.stopPropagation()}>
   <div className="modal-head"><h2>更正现场复核结论</h2><button className="text-button" onClick={onClose}>关闭 ✕</button></div>
   <p className="fine">窗口 {reference} · 当前第 <b>{current?.version??0}</b> 版
    {current&&<> · 记录人 {current.reviewer_email}</>}。更正不会覆盖历史，系统将追加新版本并记录原因、操作者与时间。</p>
   {error&&<div className="notice error">{error}</div>}
   <form className="editor" onSubmit={submit}>
    <div className="form-grid">
     <label>更正后结论
      <select value={verdict} onChange={e=>setVerdict(e.target.value)}>
       {Object.entries(VERDICTS).map(([k,v])=><option value={k} key={k}>{v}</option>)}
      </select>
     </label>
     <label>基于版本
      <input value={`第 ${current?.version??'-'} 版（乐观锁）`} disabled/>
     </label>
    </div>
    <label>现场说明
     <input value={note} onChange={e=>setNote(e.target.value)} required maxLength={500}/>
    </label>
    <label>更正原因（必填）
     <textarea rows={3} value={reason} onChange={e=>setReason(e.target.value)} required maxLength={500} placeholder="例如：复测压力正常，初判受相邻施工干扰"/>
    </label>
    <div className="policy-actions">
     <button type="button" onClick={openHistory} disabled={busy}>查看历次结论 ↻</button>
     <button className="primary" disabled={busy||!current}>提交更正 →</button>
    </div>
   </form>
   {history&&<div className="history-box">
    <h3>历次结论（{history.length} 版）</h3>
    <table>
     <thead><tr><th>版本</th><th>结论</th><th>说明 / 原因</th><th>操作者</th><th>时间</th></tr></thead>
     <tbody>{history.map(h=><tr key={h.id}>
      <td className="mono">v{h.revision_no}{h.base_version>0&&<small>基于 v{h.base_version}</small>}</td>
      <td><Badge status={h.verdict}/></td>
      <td><strong>{h.note}</strong>{h.reason&&<small>原因：{h.reason}</small>}</td>
      <td>{h.operator_email}</td>
      <td className="mono">{date(h.created_at)}</td>
     </tr>)}</tbody>
    </table>
   </div>}
  </div>
 </div>;
}

export function currentReviewFor(reviews:Review[],policyId:number,windowId:number){
 return reviews.find(r=>r.policy_id===policyId&&r.window_id===windowId);
}

export function predictionReference(predictions:Prediction[],windowId:number){
 return predictions.find(p=>p.window_id===windowId)?.reference||String(windowId);
}
