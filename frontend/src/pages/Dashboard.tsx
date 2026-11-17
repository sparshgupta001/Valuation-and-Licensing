import { ArrowRight, ArrowUpRight, BadgeCheck, FileSearch, Scale, ShieldCheck, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { SystemStatusPanel } from '../components/SystemStatusPanel'

const workflowItems = [
  { number: '01', title: 'Add patent details', note: 'Upload a source document and set your licensing objective.' },
  { number: '02', title: 'Share context', note: 'Optional market and financial inputs improve the valuation.' },
  { number: '03', title: 'Review the report', note: 'See deterministic valuation with visible evidence gaps.' },
]

export function Dashboard() {
  return (
    <div className="page-content dashboard-page">
      <div className="dashboard-eyebrow"><span className="eyebrow-mark"><Sparkles size={14} /></span> IP portfolio intelligence <span className="eyebrow-divider" /> DEMO WORKSPACE</div>
      <section className="hero-panel">
        <div className="hero-copy">
          <div className="hero-kicker"><span className="kicker-dot" /> PATENT ASSESSMENT · LICENSING STRATEGY</div>
          <h1>Turn your patent into<br /><em>a commercial decision.</em></h1>
          <p>Bring the technical story and the business case together. Get a clear valuation view and a structured path to licensing.</p>
          <div className="hero-actions">
            <Link to="/assessments/new" className="button button-primary button-large">Start an assessment <ArrowRight size={17} /></Link>
            <span className="hero-time"><span className="hero-time-dot" /> About 5 minutes</span>
          </div>
          <div className="hero-trust"><ShieldCheck size={15} /><span>Private workspace</span><span className="trust-divider" /><span>Human review built in</span></div>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="visual-orbit orbit-one" /><div className="visual-orbit orbit-two" />
          <div className="visual-core"><span className="visual-core-icon"><FileSearch size={30} /></span><span className="core-caption">PATENT<br />ASSET</span></div>
          <div className="visual-node visual-node-top"><span className="visual-node-icon"><Scale size={16} /></span><span><strong>Value</strong><small>Evidence-led</small></span></div>
          <div className="visual-node visual-node-right"><span className="visual-node-icon visual-node-mint"><BadgeCheck size={16} /></span><span><strong>License</strong><small>Actionable path</small></span></div>
          <div className="visual-node visual-node-bottom"><span className="visual-node-icon visual-node-gold"><Sparkles size={16} /></span><span><strong>Review</strong><small>Human in control</small></span></div>
          <div className="visual-spark spark-a">✦</div><div className="visual-spark spark-b">✦</div>
        </div>
        <div className="hero-watermark">S</div>
      </section>

      <div className="section-heading-row"><div><span className="section-eyebrow">HOW IT WORKS</span><h2>A thoughtful path from IP to opportunity</h2></div><span className="workflow-caption">Three simple steps <ArrowUpRight size={15} /></span></div>
      <section className="workflow-grid">
        {workflowItems.map((item, index) => <article className="workflow-card" key={item.number}>
          <div className="workflow-card-top"><span className="workflow-number">{item.number}</span>{index < 2 && <span className="workflow-line" />}</div>
          <h3>{item.title}</h3><p>{item.note}</p>
        </article>)}
      </section>

      <section className="dashboard-bottom">
        <div className="value-note-card"><div className="value-note-icon"><Scale size={18} /></div><div><strong>Grounded valuation. Clear caveats.</strong><p>Valuation calculations are deterministic. Patent intelligence and evidence matching are placeholders in this demo and are labeled throughout.</p></div></div>
        <SystemStatusPanel />
      </section>
      <div className="dashboard-cta-strip"><span>Ready to assess an IP asset?</span><Link to="/assessments/new">Create your first assessment <ArrowRight size={15} /></Link></div>
    </div>
  )
}
