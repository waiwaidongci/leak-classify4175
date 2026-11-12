from src.services.policies import get_predictions
from src.services.reviews import list_reviews
from src.utils.csv_export import csv_response
def export_inspections(db,id):
 policy,predictions=get_predictions(db,id,approved=True);reviews={x['window_id']:x for x in list_reviews(db) if x['policy_id']==id}
 return csv_response(f'inspection-policy-{id}.csv',[[x['reference'],x['probability'],policy.threshold,reviews.get(x['window_id'],{}).get('verdict','pending'),reviews.get(x['window_id'],{}).get('note','')] for x in predictions if x['predicted']==1],['匿名窗口','模型得分','验证集成本阈值','人工复核结论','说明'])
