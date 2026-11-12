import {useEffect,useState} from 'react';
import {authApi} from '../api/auth';
import type {User} from '../types/domain';
export function useSession(){
 const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true);
 useEffect(()=>{if(localStorage.getItem('chengwan-token'))authApi.me().then(setUser).catch(()=>localStorage.removeItem('chengwan-token')).finally(()=>setLoading(false));else setLoading(false);const expired=()=>setUser(null);window.addEventListener('session-expired',expired);return()=>window.removeEventListener('session-expired',expired);},[]);
 async function login(email:string,password:string){const r=await authApi.login(email,password);localStorage.setItem('chengwan-token',r.token);setUser(r.user);}
 function logout(){localStorage.removeItem('chengwan-token');setUser(null);}
 return {user,loading,login,logout};
}
