import {request,post,download} from './client';
import type {Policy,Prediction,Review,ReviewRevision,Archive} from '../types/domain';
export const policyApi={
 all:()=>request<Policy[]>('/policies'),
 create:(data:any)=>post('/policies',data),
 approve:(id:number,status:string,note:string)=>request('/policies/'+id+'/approval',{method:'PATCH',body:JSON.stringify({status,note})}),
 predictions:(id:number)=>request<Prediction[]>('/policies/'+id+'/predictions'),
 reviews:()=>request<Review[]>('/reviews'),
 review:(data:any)=>post('/reviews',data),
 correct:(data:{policy_id:number;window_id:number;expected_version:number;verdict:string;note:string;reason:string})=>post('/reviews/corrections',data),
 history:(policy_id:number,window_id:number)=>request<ReviewRevision[]>(`/reviews/history?policy_id=${policy_id}&window_id=${window_id}`),
 archives:()=>request<Archive[]>('/archives'),
 archive:(id:number)=>request<Archive>('/archives/'+id),
 seal:(id:number,note:string)=>post('/policies/'+id+'/seal',{note}),
 downloadArchive:(id:number,no:string)=>download('/archives/'+id+'/download',no+'.csv'),
 export:(id:number)=>download('/policies/'+id+'/export','inspection-policy-'+id+'.csv')
};
