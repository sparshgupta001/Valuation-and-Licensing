import { useCallback, useEffect, useState } from 'react'
import { Activity, CircleHelp, FilePlus2, LayoutDashboard, WifiOff } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { api } from '../api/client'
import { useToast } from '../context/ToastContext'

const navigation = [
  { label: 'Overview', to: '/', icon: LayoutDashboard, end: true },
  { label: 'New assessment', to: '/assessments/new', icon: FilePlus2, end: false },
]

export function AppShell() {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const { notify } = useToast()
  const location = useLocation()

  const checkHealth = useCallback(async () => {
    try {
      await api.health()
      setApiOnline(true)
    } catch {
      setApiOnline(false)
    }
  }, [])

  useEffect(() => {
    void checkHealth()
    const timer = window.setInterval(() => void checkHealth(), 15000)
    return () => window.clearInterval(timer)
  }, [checkHealth])

  const pageName = location.pathname === '/' ? 'Workspace' : location.pathname.includes('/report') ? 'Assessment report' : location.pathname.includes('/progress') ? 'Assessment progress' : location.pathname.includes('/commercial') ? 'Commercial inputs' : 'Create assessment'

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <NavLink to="/" className="brand-lockup">
          <span className="brand-mark"><span> S </span></span>
          <span><strong>Strategos</strong><small>IP intelligence</small></span>
        </NavLink>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigation.map(({ label, to, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`}>
              <Icon size={18} strokeWidth={1.8} /><span>{label}</span>
              {label === 'New assessment' && <span className="nav-plus">+</span>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-status-card">
          <div className="sidebar-status-top"><Activity size={15} /><span>API connection</span></div>
          <div className="sidebar-status-value"><span className={`health-dot ${apiOnline === null ? 'health-checking' : apiOnline ? 'health-online' : 'health-offline'}`} />{apiOnline === null ? 'Checking…' : apiOnline ? 'Connected' : 'Offline'}</div>
          {apiOnline === false && <button className="sidebar-retry" onClick={() => { void checkHealth(); notify('Checking the backend connection…', 'info') }}>Try again</button>}
        </div>
        <div className="sidebar-footer"><span className="avatar-small">S</span><span><strong>Demo workspace</strong><small>Mentor preview</small></span><CircleHelp size={16} className="ml-auto text-slate-500" /></div>
      </aside>

      <div className="main-frame">
        <header className="topbar">
          <div className="topbar-breadcrumb"><span>Strategos</span><span className="crumb-slash">/</span><strong>{pageName}</strong></div>
          <div className={`topbar-api ${apiOnline === false ? 'topbar-api-down' : ''}`}><span className={`health-dot ${apiOnline === null ? 'health-checking' : apiOnline ? 'health-online' : 'health-offline'}`} />{apiOnline === null ? 'Connecting to API' : apiOnline ? 'Backend connected' : 'Backend offline'}</div>
        </header>
        {apiOnline === false && <div className="offline-banner"><WifiOff size={17} /><span><strong>Backend unavailable.</strong> Start the FastAPI service at <code>127.0.0.1:8000</code> to continue. Your page is still safe to refresh.</span><button onClick={() => void checkHealth()}>Retry connection</button></div>}
        <main className="page-main"><Outlet context={{ apiOnline }} /></main>
        <footer className="app-footer"><span>Strategos · Patent valuation & licensing</span><span>Assessment outputs are decision support and require human review.</span></footer>
      </div>
    </div>
  )
}
