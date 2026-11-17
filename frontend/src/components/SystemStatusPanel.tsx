import { useState } from 'react'
import { CheckCircle2, ChevronDown, CircleDashed, Info, Sparkles } from 'lucide-react'

const modules = [
  { name: 'Valuation engine', state: 'Live', live: true, note: 'Deterministic Python calculations: DCF, relief-from-royalty, cost approach, and Monte Carlo.' },
  { name: 'Negotiation corridor', state: 'Partial', live: false, note: 'Royalty corridor math is deterministic when inputs are available; narrative remains a placeholder.' },
  { name: 'Patent intelligence', state: 'Placeholder', live: false, note: 'Document upload is stored. Patent extraction and claim parsing are not connected yet.' },
  { name: 'Competitor intelligence', state: 'Placeholder', live: false, note: 'No company data sources or semantic target ranking are configured.' },
  { name: 'Claim charts', state: 'Placeholder', live: false, note: 'Rows are provisional and are not evidence-backed claim mappings.' },
]

export function SystemStatusPanel() {
  const [open, setOpen] = useState(false)
  return (
    <section className={`system-panel ${open ? 'system-panel-open' : ''}`}>
      <button className="system-panel-trigger" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className="system-panel-symbol"><Info size={17} /></span>
        <span className="system-panel-copy"><strong>System status</strong><small>What is live in this demo</small></span>
        <span className="system-panel-count"><span className="live-dot" /> 1 live · 1 partial · 3 placeholder</span>
        <ChevronDown size={17} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="system-panel-list">
        {modules.map((module) => (
          <div className="system-module" key={module.name}>
            <span className={`system-module-icon ${module.live ? 'is-live' : 'is-stub'}`}>
              {module.live ? <CheckCircle2 size={16} /> : <Sparkles size={15} />}
            </span>
            <div className="min-w-0 flex-1"><div className="system-module-title">{module.name}<span className={`module-state ${module.live ? 'module-live' : 'module-placeholder'}`}>{module.state}</span></div><p>{module.note}</p></div>
            {!module.live && <CircleDashed size={15} className="shrink-0 text-slate-300" />}
          </div>
        ))}
        <p className="system-honesty-note">Placeholder results are labeled throughout the report. A human should review every AI-assisted or provisional item.</p>
      </div>}
    </section>
  )
}
