import { useState } from 'react'
import { BarChart3, Bot, Clock3, Inbox, Mail, Settings, Users, Waves } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import InboxPage from './pages/InboxPage'
import Senders from './pages/Senders'
import Subscriptions from './pages/Subscriptions'
import ReviewLater from './pages/ReviewLater'
import Chat from './pages/Chat'
import SettingsPage from './pages/SettingsPage'

type Page = 'dashboard' | 'inbox' | 'senders' | 'subscriptions' | 'later' | 'chat' | 'settings'

const nav = [
  ['dashboard', 'Dashboard', BarChart3],
  ['inbox', 'Inbox', Inbox],
  ['senders', 'Senders', Users],
  ['subscriptions', 'Subscriptions', Waves],
  ['later', 'Review Later', Clock3],
  ['chat', 'AI Chat', Bot],
  ['settings', 'Settings', Settings],
] as const

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-icon"><Mail size={19}/></div><div><strong>MAIL</strong><span>INTELLIGENCE</span></div></div>
        <nav>
          {nav.map(([id, label, Icon]) => (
            <button key={id} className={page === id ? 'nav-item active' : 'nav-item'} onClick={() => setPage(id as Page)}>
              <Icon size={18}/><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-note">Local-first<br/>Gmail stays source of truth.</div>
      </aside>
      <main className="main">
        {page === 'dashboard' && <Dashboard/>}
        {page === 'inbox' && <InboxPage/>}
        {page === 'senders' && <Senders/>}
        {page === 'subscriptions' && <Subscriptions/>}
        {page === 'later' && <ReviewLater/>}
        {page === 'chat' && <Chat/>}
        {page === 'settings' && <SettingsPage/>}
      </main>
    </div>
  )
}
