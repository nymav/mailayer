import { useEffect, useState } from 'react'
import { api } from '../api'
import { Header, Score } from '../components'

export default function Senders(){
  const [rows,setRows]=useState<any[]>([])
  useEffect(()=>{api.senders(90).then(setRows)},[])
  return <section><Header title="Senders" subtitle="90-day behavioral overview of who sends you the most mail."/>
    <div className="card table-wrap"><table><thead><tr><th>Sender</th><th>Emails</th><th>Unread</th><th>Usefulness</th><th>Noise</th><th>Last seen</th></tr></thead><tbody>
      {rows.map(r=><tr key={r.sender}><td><strong>{r.name||r.sender}</strong><small>{r.name?r.sender:r.domain}</small></td><td>{r.count}</td><td>{Math.round(r.unread_ratio*100)}%</td><td><Score value={r.avg_usefulness}/></td><td>{Math.round(r.noise_ratio*100)}%</td><td>{new Date(r.last_seen).toLocaleDateString()}</td></tr>)}
    </tbody></table></div></section>
}
