import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score,roc_curve,precision_recall_curve,confusion_matrix

def confusion(y,p,threshold,fn_cost,fp_cost):
 pred=np.asarray(p)>=threshold;tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
 return {'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp),'precision':float(tp/(tp+fp)) if tp+fp else 0.,'recall':float(tp/(tp+fn)) if tp+fn else 0.,'accuracy':float((tp+tn)/len(y)),'total_cost':float(fn*fn_cost+fp*fp_cost),'flagged':int(tp+fp)}
def evaluate(y,p,threshold,fn_cost,fp_cost):
 fpr,tpr,thresholds=roc_curve(y,p);precision,recall,pr_thresholds=precision_recall_curve(y,p)
 return {'auc':float(roc_auc_score(y,p)),'average_precision':float(average_precision_score(y,p)),'prevalence':float(np.mean(y)),'confusion':confusion(y,p,threshold,fn_cost,fp_cost),'roc':[{'x':float(x),'y':float(z),'threshold':float(t) if np.isfinite(t) else None} for x,z,t in zip(fpr,tpr,thresholds)],'pr':[{'x':float(x),'y':float(z)} for x,z in zip(recall,precision)]}
