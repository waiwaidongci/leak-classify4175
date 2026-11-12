import {useState,useEffect,useCallback} from 'react';
import type {Policy,Review,Prediction,User,Archive} from '../types/domain';
import {policyApi} from '../api/policies';
import {PageTitle} from '../components/common/PageTitle';
import {Badge} from '../components/common/Badge';
import {Notice} from '../components/common/Notice';
import {Table} from '../components/common/Table';
import {Empty} from '../components/common/Empty';
import {CorrectionDialog,currentReviewFor,predictionReference} from '../components/CorrectionDialog';
import {ArchivePanel} from '../components/ArchivePanel';
import {useAsync} from '../hooks/useAsync';
import {dec,date} from '../utils/format';
import {VERDICTS} from '../constants/enums';

export function PoliciesPage({policies,reviews,user,reload}:{policies:Policy[];reviews:Review[];user:User;reload:()=>Promise<any>}){
 const [note,setNote]=useState('按模型线索安排人工复核；不自动派工，记录现场证据后再判断。');
 const [active,setActive]=useState<Policy|null>(null);
 const [predictions,setPredictions]=useState<Prediction[]>([]);
 const [windowId,setWindowId]=useState(0);
 const [verdict,setVerdict]=useState('pending');
 const [reviewNote,setReviewNote]=useState('等待现场压力与声学复核。');
 const [archives,setArchives]=useState<Archive[]>([]);
 const [correctTarget,setCorrectTarget]=useState<{windowId:number}|null>(null);
 const {busy,error,message,act}=useAsync();
 const canWrite=user.role!=='viewer';
 const loadArchives=useCallback(async()=>{try{setArchives(await policyApi.archives())}catch{/* 留痕页可稍后重试 */}},[]);
 useEffect(()=>{loadArchives()},[loadArchives]);
 const refreshAll=useCallback(async()=>{await Promise.all([reload(),loadArchives()])},[reload,loadArchives]);
 async function inspect(p:Policy){
  await act(async()=>{
   setPredictions((await policyApi.predictions(p.id)).filter(x=>x.predicted));
   setActive(p);setWindowId(0);
  },'');
 }
 return <>
  <PageTitle index="05 / HUMAN REVIEW" title="先复核，再形成现场判断。" description="负责人审核固定阈值策略；分析师记录候选窗口复核，记错可带原因更正并保留历次结论。获批策略可封存编号名单，按编号下载内容不变。"/>
  <Notice error={error} message={message}/>
  {user.role==='admin'&&<label className="approval-note">本次策略审核备注<input value={note} onChange={e=>setNote(e.target.value)} maxLength={500}/></label>}
  {!policies.length&&<Empty title="没有阈值策略" help="在封存结果中建立策略，系统复制验证集选定阈值。"/>}
  <div className="policy-list">
   {policies.map(p=><article key={p.id}>
    <div className="policy-heading"><small>POLICY / {String(p.id).padStart(3,'0')} · RUN {p.run_id}</small><Badge status={p.status}/></div>
    <div className="policy-body">
     <div><h2>{p.name}</h2><p>{p.note}</p></div>
     <div className="threshold-number"><small>LOCKED THRESHOLD</small><b>{p.threshold>1?'> 1':dec(p.threshold)}</b>{p.threshold>1&&<small>无人标记哨兵 / 非概率</small>}</div>
    </div>
    <div className="policy-actions">
     <button onClick={()=>inspect(p)}>查看复核候选 ↗</button>
     <button disabled={p.status!=='approved'} onClick={()=>act(()=>policyApi.export(p.id),'获批巡检参考已导出（当前结论）')}>导出当前名单 CSV</button>
     {user.role==='admin'&&p.status==='draft'&&<>
      <button disabled={busy} onClick={()=>act(async()=>{await policyApi.approve(p.id,'rejected',note);await reload()},'策略已退回')}>退回</button>
      <button className="primary" disabled={busy} onClick={()=>act(async()=>{await policyApi.approve(p.id,'approved',note);await reload()},'策略已获批')}>审核通过 →</button>
     </>}
    </div>
   </article>)}
  </div>
  {active&&<section className="review-section">
   <div className="section-title"><h2>{active.name} / 候选窗口</h2><small>候选 {predictions.length} · 回顾性留出窗口 · 结论可更正，历史不覆盖</small></div>
   <Table headers={['匿名窗口','模型得分','当前复核','版本','操作']}>
    {predictions.slice(0,20).map(p=>{
      const cur=currentReviewFor(reviews,active.id,p.window_id);
      return <tr key={p.window_id}>
       <td>{p.reference}</td><td>{dec(p.probability)}</td>
       <td>{cur?<Badge status={cur.verdict}/>:'尚未记录'}</td>
       <td className="mono">{cur?`v${cur.version}`:'—'}</td>
       <td>{cur&&canWrite&&active.status==='approved'&&<button className="text-button" onClick={()=>setCorrectTarget({windowId:p.window_id})}>更正结论 ↗</button>}</td>
      </tr>;
    })}
   </Table>
   {canWrite&&active.status==='approved'&&<form className="editor review-form" onSubmit={e=>{e.preventDefault();act(async()=>{
     await policyApi.review({policy_id:active.id,window_id:windowId||predictions[0]?.window_id,verdict,note:reviewNote});
     await refreshAll();
    },'人工复核记录已保存')}}>
    <h2>记录一次人工复核</h2>
    <div className="form-grid">
     <label>候选窗口<select value={windowId||predictions[0]?.window_id||''} onChange={e=>setWindowId(+e.target.value)}>
      {predictions.map(p=><option key={p.window_id} value={p.window_id}>{p.reference} / 得分{dec(p.probability)}</option>)}
     </select></label>
     <label>人工结论<select value={verdict} onChange={e=>setVerdict(e.target.value)}>
      {Object.entries(VERDICTS).map(([k,v])=><option value={k} key={k}>{v}</option>)}
     </select></label>
    </div>
    <label>现场记录说明<input value={reviewNote} onChange={e=>setReviewNote(e.target.value)} required maxLength={500}/></label>
    <p className="fine">每个候选仅可首次记录一次；记错请用“更正结论”，填写原因后系统保留历次结论、操作者与时间。两人基于同一旧版本更正时，后者会收到冲突提示而不会覆盖。</p>
    <button className="primary" disabled={busy||!predictions.length}>保存人工复核 →</button>
   </form>}
   {correctTarget&&<CorrectionDialog policyId={active.id} windowId={correctTarget.windowId}
    reference={predictionReference(predictions,correctTarget.windowId)}
    current={currentReviewFor(reviews,active.id,correctTarget.windowId)}
    reload={refreshAll} onClose={()=>setCorrectTarget(null)}/>}
   <ArchivePanel policy={active} archives={archives} reload={refreshAll} canWrite={canWrite}/>
  </section>}
  <div className="section-title"><h2>人工复核留档（当前结论）</h2><small>历次结论在更正弹窗中查看 · 不从训练标签自动生成</small></div>
  <Table headers={['策略 / 窗口ID','当前结论','版本','说明','记录人','最近更新']}>
   {reviews.map(r=><tr key={r.id}>
    <td>#{r.policy_id} / {r.window_id}</td><td><Badge status={r.verdict}/></td><td className="mono">v{r.version}</td>
    <td>{r.note}</td><td>{r.reviewer_email}</td><td>{date(r.updated_at||r.created_at)}</td>
   </tr>)}
  </Table>
 </>;
}
