import { useEffect, useState } from 'react'
import { api } from '../api'
import { Badge, Header, Score } from '../components'

export default function Subscriptions(){
  const [rows,setRows]=useState<any[]>([])
  useEffect(()=>{api.subscriptions(90).then(setRows)},[])
  return <section><Header title="Subscription Intelligence" subtitle="Candidates worth keeping, reviewing, or eventually unsubscribing from — recommendations only."/>
    <div className="card table-wrap"><table><thead><tr><th>Sender</th><th>90d</th><th>/ month</th><th>Unread</th><th>Useful</th><th>Recommendation</th></tr></thead><tbody>
      {rows.map(r=><tr key={r.sender}><td><strong>{r.name||r.sender}</strong><small>{r.sender}</small></td><td>{r.count}</td><td>{r.estimated_monthly}</td><td>{Math.round(r.unread_ratio*100)}%</td><td><Score value={r.avg_usefulness}/></td><td><Badge tone={r.review_score>=.7?'warn':'neutral'}>{r.recommendation}</Badge></td></tr>)}
    </tbody></table></div></section>
}
