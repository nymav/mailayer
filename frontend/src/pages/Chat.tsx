import { useState } from 'react'
import type { FormEvent } from 'react'
import { Bot, Send } from 'lucide-react'
import { api } from '../api'
import { Header } from '../components'

type Turn={role:'user'|'assistant',text:string,sources?:any[]}
export default function Chat(){
 const [q,setQ]=useState('')
 const [busy,setBusy]=useState(false)
 const [turns,setTurns]=useState<Turn[]>([{role:'assistant',text:'Ask about senders, subscriptions, important messages, applications, receipts, or anything in your indexed mailbox.'}])
 const submit=async(e:FormEvent)=>{e.preventDefault();if(!q.trim()||busy)return;const text=q.trim();setQ('');setTurns(t=>[...t,{role:'user',text}]);setBusy(true);try{const r=await api.chat(text,90);setTurns(t=>[...t,{role:'assistant',text:r.answer,sources:r.sources}])}catch(err:any){setTurns(t=>[...t,{role:'assistant',text:`Error: ${err.message}`}])}finally{setBusy(false)}}
 return <section className="chat-page"><Header title="Mailbox AI" subtitle="Local LM Studio reasoning over retrieved evidence — not unrestricted mailbox access."/>
  <div className="card chat-box">{turns.map((t,i)=><div key={i} className={`turn ${t.role}`}><div className="avatar">{t.role==='assistant'?<Bot size={17}/>:'Y'}</div><div className="bubble"><div>{t.text}</div>{t.sources&&t.sources.length>0&&<div className="sources">{t.sources.slice(0,8).map(s=><span key={s.message_id}>{s.subject||'(no subject)'} · {s.sender_email}</span>)}</div>}</div></div>)}{busy&&<div className="turn assistant"><div className="avatar"><Bot size={17}/></div><div className="bubble">Thinking from local evidence…</div></div>}</div>
  <form className="chat-input" onSubmit={submit}><input value={q} onChange={e=>setQ(e.target.value)} placeholder="e.g. Which subscriptions are mostly noise?"/><button disabled={busy}><Send size={17}/></button></form>
 </section>
}
