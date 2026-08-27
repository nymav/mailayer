import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { api } from '../api'
import { Header, Metric } from '../components'

export default function Dashboard(){
  const [data,setData]=useState<any>(null)
  const [err,setErr]=useState('')
  const load=()=>api.dashboard(30).then(setData).catch(e=>setErr(e.message))
  useEffect(()=>{ load() },[])
  if(err) return <div className="error">{err}</div>
  if(!data) return <div className="loading">Loading dashboard…</div>
  const max=Math.max(1,...data.daily.map((x:any)=>x.count))
  return <section>
    <Header title="Dashboard" subtitle="A 30-day view of who is consuming your inbox and what deserves attention." actions={<button className="ghost" onClick={load}><RefreshCw size={16}/>Refresh</button>}/>
    <div className="metrics">
      <Metric label="Received" value={data.total}/><Metric label="Unread" value={data.unread}/><Metric label="Needs attention" value={data.actionable}/><Metric label="Useful" value={data.useful}/><Metric label="Low value" value={data.low_value}/>
    </div>
    <div className="grid two">
      <div className="card panel"><div className="panel-title">Email volume</div><div className="bars">{data.daily.map((d:any)=><div key={d.date} title={`${d.date}: ${d.count}`} className="bar" style={{height:`${Math.max(4,(d.count/max)*150)}px`}}/>)}</div></div>
      <div className="card panel"><div className="panel-title">Top senders</div>{data.top_senders.map((s:any)=><div className="rank" key={s.sender}><span>{s.sender}</span><strong>{s.count}</strong></div>)}</div>
    </div>
    <div className="grid two">
      <div className="card panel"><div className="panel-title">Categories</div>{Object.entries(data.categories).map(([k,v]:any)=><div className="rank" key={k}><span>{k}</span><strong>{v}</strong></div>)}</div>
      <div className="card panel"><div className="panel-title">Top domains</div>{data.top_domains.map((s:any)=><div className="rank" key={s.domain}><span>{s.domain}</span><strong>{s.count}</strong></div>)}</div>
    </div>
  </section>
}
