import type { ReactNode } from 'react'
import type { Message } from './types'

export function Header({title, subtitle, actions}:{title:string, subtitle:string, actions?:ReactNode}) {
  return <div className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div><div className="header-actions">{actions}</div></div>
}

export function Metric({label, value, sub}:{label:string,value:string|number,sub?:string}) {
  return <div className="metric card"><span>{label}</span><strong>{value}</strong>{sub && <small>{sub}</small>}</div>
}

export function Score({value}:{value:number}) {
  const pct = Math.round(value * 100)
  return <div className="score"><div className="score-track"><div className="score-fill" style={{width:`${pct}%`}}/></div><span>{pct}</span></div>
}

export function Badge({children, tone='neutral'}:{children:ReactNode,tone?:string}) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function EmailRow({m, onOpen, onLater}:{m:Message,onOpen:()=>void,onLater:()=>void}) {
  return <div className={`email-row ${m.is_read ? '' : 'unread'}`}>
    <button className="email-main" onClick={onOpen}>
      <div className="email-sender">{m.sender_name || m.sender_email}</div>
      <div className="email-content"><div className="email-subject">{m.subject || '(no subject)'}</div><div className="email-snippet">{m.summary || m.snippet}</div></div>
      <div className="email-meta"><Badge>{m.category}</Badge><span>{new Date(m.received_at).toLocaleDateString()}</span></div>
    </button>
    <button className="ghost small" onClick={onLater}>Later</button>
  </div>
}
