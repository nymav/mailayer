import { useEffect, useState } from 'react'
import { api } from '../api'
import { Header } from '../components'

export default function ReviewLater(){
 const [rows,setRows]=useState<any[]>([])
 const load=()=>api.reviewLater().then(setRows)
 useEffect(()=>{ load() },[])
 return <section><Header title="Review Later" subtitle="A local attention queue. Nothing is changed in Gmail."/>
  <div className="card list">{rows.length===0?<div className="empty">Nothing queued.</div>:rows.map(r=><div className="review-row" key={r.review_id}><div><strong>{r.message.subject}</strong><span>{r.message.sender_email} · {new Date(r.message.received_at).toLocaleDateString()}</span></div><button className="ghost small" onClick={()=>api.removeReview(r.message.id).then(load)}>Done</button></div>)}</div>
 </section>
}
