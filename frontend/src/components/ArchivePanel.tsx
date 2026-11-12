import {useState} from 'react';
import type {Archive,Policy} from '../types/domain';
import {policyApi} from '../api/policies';
import {Badge} from './common/Badge';
import {date,dec} from '../utils/format';

export function ArchivePanel({policy,archives,reload,canWrite}:{
 policy:Policy;archives:Archive[];reload:()=>Promise<any>;canWrite:boolean}){
 const [note,setNote]=useState('');
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [message,setMessage]=useState('');
 const [openId,setOpenId]=useState(0);
 const [detail,setDetail]=useState<Archive|null>(null);
 const mine=archives.filter(a=>a.policy_id===policy.id);
 async function seal(){
  setBusy(true);setError('');setMessage('');
  try{await policyApi.seal(policy.id,note);await reload();setMessage('已按当前时点封存编号名单')}
  catch(e:any){setError(e.message)}
  finally{setBusy(false)}
 }
 async function inspect(a:Archive){
  setOpenId(a.id);setDetail(null);
  try{setDetail(await policyApi.archive(a.id))}catch(e:any){setError(e.message)}
 }
 return <div className="archive-panel">
  <div className="section-title"><h2>编号封存名单</h2><small>封存当时全部候选与复核结论 · 并发更正保持同一时点</small></div>
  {error&&<div className="notice error">{error}</div>}
  {message&&<div className="notice success">{message}</div>}
  {policy.status==='approved'&&canWrite&&<div className="editor seal-form">
   <label>封存备注
    <input value={note} onChange={e=>setNote(e.target.value)} maxLength={500} placeholder="例如：2026-11 批次巡检参考封存"/>
   </label>
   <button className="primary" disabled={busy} onClick={seal}>封存为编号名单 →</button>
  </div>}
  {!mine.length&&<p className="fine">该策略尚无封存名单。封存后内容冻结，按编号下载永远返回同一时点内容；之后的更正只影响新封存，不改动训练标签。</p>}
  <div className="archive-list">
   {mine.map(a=><article key={a.id}>
    <div className="archive-heading">
     <div><b className="mono">{a.archive_no}</b><small>{date(a.created_at)} · {a.creator_email}</small></div>
     <Badge status="approved"/>
    </div>
    <div className="archive-meta">
     <span>候选 <b>{a.candidate_count}</b></span>
     <span>已复核 <b>{a.reviewed_count}</b></span>
     <span>阈值 <b>{a.threshold>1?'> 1':dec(a.threshold)}</b></span>
    </div>
    <div className="policy-actions">
     <button onClick={()=>inspect(a)}>查看封存内容 ↗</button>
     <button onClick={()=>policyApi.downloadArchive(a.id,a.archive_no)}>按编号下载 CSV</button>
    </div>
    {openId===a.id&&detail&&<div className="history-box">
     <h3>{detail.archive_no} 快照（{detail.content!.candidates.length} 条）· 校验 {detail.content_hash.slice(0,12)}…</h3>
     <table>
      <thead><tr><th>匿名窗口</th><th>模型得分</th><th>复核结论</th><th>结论版本</th><th>现场说明</th></tr></thead>
      <tbody>{detail.content!.candidates.map(c=><tr key={c.window_id}>
       <td>{c.reference}</td><td className="mono">{dec(c.probability)}</td>
       <td><Badge status={c.verdict}/></td><td className="mono">{c.review_version?`v${c.review_version}`:'未复核'}</td>
       <td>{c.review_note||'—'}</td>
      </tr>)}</tbody>
     </table>
    </div>}
   </article>)}
  </div>
 </div>;
}
