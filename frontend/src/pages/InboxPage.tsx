import { useEffect, useState } from 'react'
import { Search, X } from 'lucide-react'
import { api } from '../api'
import { Badge, EmailRow, Header, Score } from '../components'
import type { Message } from '../types'

export default function InboxPage(){
  const [items,setItems]=useState<Message[]>([])
  const [search,setSearch]=useState('')
  const [selected,setSelected]=useState<Message|null>(null)
  const [err,setErr]=useState('')
  const load=()=>api.messages(90,search).then(setItems).catch(e=>setErr(e.message))
  useEffect(()=>{const t=setTimeout(load,250);return()=>clearTimeout(t)},[search])
  return <section>
    <Header title="Inbox Intelligence" subtitle="Your local analyzed view; Gmail remains unchanged."/>
    <div className="search"><Search size={17}/><input placeholder="Search sender, subject, or body…" value={search} onChange={e=>setSearch(e.target.value)}/></div>
    {err&&<div className="error">{err}</div>}
    <div className="card list">{items.map(m=><EmailRow key={m.id} m={m} onOpen={()=>setSelected(m)} onLater={()=>api.addReview(m.id)}/>)}</div>
    {selected&&<div className="drawer-backdrop" onClick={()=>setSelected(null)}><aside className="drawer" onClick={e=>e.stopPropagation()}>
      <button className="drawer-close" onClick={()=>setSelected(null)}><X/></button>
      <div className="drawer-from">{selected.sender_name || selected.sender_email}<span>{selected.sender_email}</span></div>
      <h2>{selected.subject}</h2><div className="drawer-tags"><Badge>{selected.category}</Badge>{selected.action_required&&<Badge tone="warn">ACTION</Badge>}<span>{new Date(selected.received_at).toLocaleString()}</span></div>
      <div className="drawer-scores"><div>Usefulness<Score value={selected.usefulness}/></div><div>Importance<Score value={selected.importance}/></div></div>
      <div className="reason"><strong>Why</strong><p>{selected.reason}</p></div>
      <pre className="mail-body">{selected.body_text || selected.snippet}</pre>
      <div className="drawer-actions"><button onClick={()=>api.feedback(selected.id,true)}>Useful</button><button className="ghost" onClick={()=>api.feedback(selected.id,false)}>Not useful</button><button className="ghost" onClick={()=>api.addReview(selected.id)}>Review later</button></div>
    </aside></div>}
  </section>
}
