import numpy as np
from sklearn.model_selection import train_test_split
def partition(y):
 labels=np.asarray(y)
 if len(labels)<100 or set(labels.tolist())!={0,1} or min(np.bincount(labels))<20: raise ValueError('至少100窗口、两类各20条，才可分层分割和三折CV')
 index=np.arange(len(labels))
 train,remainder=train_test_split(index,test_size=.4,stratify=labels,random_state=73)
 validation,test=train_test_split(remainder,test_size=.5,stratify=labels[remainder],random_state=74)
 return train,validation,test
