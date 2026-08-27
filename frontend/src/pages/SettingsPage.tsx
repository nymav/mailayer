import { useEffect, useState } from 'react'
import { CheckCircle2, CircleAlert, RefreshCw } from 'lucide-react'
import { api } from '../api'
import { Header } from '../components'
import type { Job } from '../types'

export default function SettingsPage(){
 const [status,setStatus]=useState<any>(null)
 const [days,setDays]=useState(90)
 const [job,setJob]=useState<Job|null>(null)
 const [err,setErr]=useState('')
 const load=()=>api.status().then(setStatus).catch(e=>setErr(e.message))
 useEffect(()=>{load()},[])
 useEffect(()=>{if(!job||!['queued','running'].includes(job.status))return;const t=setInterval(async()=>{const j=await api.job(job.id);setJob(j);if(['done','error'].includes(j.status)){clearInterval(t);load()}},1000);return()=>clearInterval(t)},[job?.id,job?.status])
 const run=async(fn:()=>Promise<any>)=>{try{setErr('');setJob(await fn())}catch(e:any){setErr(e.message)}}
 return <section><Header title="Settings & Local Services" subtitle="Connect Gmail, synchronize your local cache, and run optional local AI indexing." actions={<button className="ghost" onClick={load}><RefreshCw size={16}/>Refresh</button>}/>
  {err&&<div className="error">{err}</div>}
  <div className="grid two">
   <div className="card panel"><div className="panel-title">Gmail</div><Status ok={!!status?.credentials_file} text={status?.credentials_file?'credentials.json found':'credentials.json missing'}/><Status ok={!!status?.gmail_connected} text={status?.gmail_connected?`Connected ${status.account||''}`:'Not connected'}/><div className="button-row"><button onClick={()=>api.connect().then(load)}>Connect Gmail</button><button className="ghost" onClick={()=>api.disconnect().then(load)}>Disconnect</button></div></div>
   <div className="card panel"><div className="panel-title">LM Studio</div><Status ok={!!status?.lm_studio?.ok} text={status?.lm_studio?.ok?'Local API reachable':'Local API unavailable'}/><p className="muted">Chat: {status?.lm_studio?.chat_model||'not configured'}</p><p className="muted">Embeddings: {status?.lm_studio?.embedding_model||'disabled'}</p></div>
  </div>
  <div className="card panel"><div className="panel-title">Synchronization</div><div className="sync-controls"><label>History window<select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={30}>30 days</option><option value={90}>90 days</option><option value={365}>1 year</option><option value={0}>Everything</option></select></label><button onClick={()=>run(()=>api.fullSync(days))}>Full Sync</button><button className="ghost" onClick={()=>run(()=>api.incrementalSync())}>Incremental Sync</button></div><p className="muted">Last full: {status?.last_full_sync?new Date(status.last_full_sync).toLocaleString():'Never'} · Last incremental: {status?.last_incremental_sync?new Date(status.last_incremental_sync).toLocaleString():'Never'}</p></div>
  <div className="card panel"><div className="panel-title">Local AI jobs</div><div className="button-row"><button onClick={()=>run(()=>api.classify(100))}>AI classify 100</button><button className="ghost" onClick={()=>run(()=>api.embed(200))}>Index 200 embeddings</button></div></div>
  {job&&<div className="card job"><div><strong>{job.name}</strong><span>{job.status} · {job.message}</span></div><div className="progress"><div style={{width:`${Math.round(job.progress*100)}%`}}/></div>{job.status==='error'&&<pre>{job.error}</pre>}</div>}
 </section>
}
function Status({ok,text}:{ok:boolean,text:string}){return <div className={`status ${ok?'ok':'bad'}`}>{ok?<CheckCircle2 size={17}/>:<CircleAlert size={17}/>}<span>{text}</span></div>}
