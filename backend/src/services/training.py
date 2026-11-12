import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold,cross_val_score
from src.constants.features import FEATURES
from .splits import partition
from .metrics import evaluate
from .thresholds import choose_threshold
from .fingerprint import fingerprint

def train_model(rows,config):
 rows=sorted(rows,key=lambda r:r['reference'])
 if len({r['reference'] for r in rows})!=len(rows): raise ValueError('窗口自然键重复')
 if any(set(r['features'])!=set(FEATURES) or r['label'] not in (0,1) for r in rows): raise ValueError('特征/标签模式不合法')
 feature_sets=config['feature_sets'];cs=config['c_values']
 if not feature_sets or not cs or any(not s or len(set(s))!=len(s) or not set(s)<=set(FEATURES) for s in feature_sets): raise ValueError('非法特征候选，禁止标签入模')
 if any(not np.isfinite(c) or c<=0 or c>1000 for c in cs): raise ValueError('非法C值')
 if any(not np.isfinite(float(v)) for r in rows for v in r['features'].values()): raise ValueError('特征含非有限值')
 y=np.asarray([r['label'] for r in rows],dtype=int);train,validation,test=partition(y)
 cv=StratifiedKFold(n_splits=3,shuffle=True,random_state=73);comparisons=[]
 def pipeline(c):return Pipeline([('scale',StandardScaler()),('logistic',LogisticRegression(C=c,class_weight='balanced',max_iter=2000,solver='lbfgs',random_state=73))])
 for features in feature_sets:
  X=np.asarray([[r['features'][f] for f in features] for r in rows],dtype=float)
  if np.any(np.std(X[train],axis=0)==0): raise ValueError('训练特征有常量列，请移除后重试')
  for c in cs:
   scores=cross_val_score(pipeline(c),X[train],y[train],cv=cv,scoring='roc_auc',error_score='raise')
   comparisons.append({'features':features,'C':float(c),'fold_auc':scores.tolist(),'mean_auc':float(scores.mean()),'std_auc':float(scores.std())})
 comparisons.sort(key=lambda c:(-c['mean_auc'],len(c['features']),c['C'],','.join(c['features'])))
 winner=comparisons[0];features=winner['features'];X=np.asarray([[r['features'][f] for f in features] for r in rows],dtype=float)
 model=pipeline(winner['C']);model.fit(X[train],y[train])
 validation_p=model.predict_proba(X[validation])[:,1]
 recommendation=choose_threshold(y[validation],validation_p,config['false_negative_cost'],config['false_positive_cost'])
 # Test labels first enter computations only after all candidate and threshold selection is locked.
 test_p=model.predict_proba(X[test])[:,1];threshold=recommendation['threshold']
 final=evaluate(y[test],test_p,threshold,config['false_negative_cost'],config['false_positive_cost'])
 all_ids={name:[rows[int(i)]['id'] for i in ix] for name,ix in [('train',train),('validation',validation),('test',test)]}
 model_scale=model.named_steps['scale'];logit=model.named_steps['logistic']
 return {'fingerprint':fingerprint(rows,config),'split_ids':all_ids,'split_counts':{name:{'n':len(ix),'positive':int(y[ix].sum())} for name,ix in [('train',train),('validation',validation),('test',test)]},'comparisons':comparisons,'winner':winner,'recommendation':recommendation,'test':final,'standardization':{'mean':model_scale.mean_.tolist(),'scale':model_scale.scale_.tolist()},'coefficients':[{'feature':f,'coefficient':float(v)} for f,v in zip(features,logit.coef_[0])],'intercept':float(logit.intercept_[0]),'test_predictions':[{'window_id':rows[int(i)]['id'],'reference':rows[int(i)]['reference'],'probability':float(p),'predicted':int(p>=threshold)} for i,p in zip(test,test_p)],'method':'60/20/20 stratified seed73/74; 3fold train-only Pipeline CV; balanced logistic; validation-only cost threshold; sealed test evaluated once','assumption':'Retrospective synthetic windows are exchangeable; no calibration or future-field guarantee.'}
