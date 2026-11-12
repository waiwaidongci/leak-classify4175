import numpy as np
from .metrics import confusion
def choose_threshold(y,p,fn_cost,fp_cost):
 if not np.isfinite(fn_cost) or not np.isfinite(fp_cost) or fn_cost<=0 or fp_cost<=0: raise ValueError('成本必须为有限正数')
 if not set(np.asarray(y).tolist())<={0,1}: raise ValueError('标签必须为0/1')
 p=np.asarray(p,dtype=float)
 if len(p)!=len(y) or not len(p) or not np.isfinite(p).all() or (p<0).any() or (p>1).any(): raise ValueError('概率必须有限、位于[0,1]且与标签等长')
 candidates=[]
 # Include a strict-above-maximum cut point: score==1 still needs an all-negative candidate.
 above_max=float(np.nextafter(np.max(p),np.inf))
 for t in np.unique(np.r_[0.,p,1.,above_max]):
  cm=confusion(y,p,float(t),fn_cost,fp_cost)
  candidates.append({'threshold':float(t),**cm})
 winner=min(candidates,key=lambda c:(c['total_cost'],-c['threshold']))
 return {'threshold':winner['threshold'],'validation_confusion':{k:v for k,v in winner.items() if k!='threshold'},'candidates':candidates,'selection_source':'validation_only','tie_break':'higher_threshold','validation_all_negative':winner['flagged']==0,'threshold_above_one':winner['threshold']>1.,'sentinel':'above_max_validation_score' if winner['threshold']==above_max else None}
