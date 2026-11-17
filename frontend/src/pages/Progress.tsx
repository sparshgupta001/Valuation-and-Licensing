import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, ArrowRight, Check, Circle, Clock3, LoaderCircle, RotateCw } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { InlineSpinner } from '../components/Loading'
import { useToast } from '../context/ToastContext'
import type { AssessmentState, AssessmentStatus, StepStatus } from '../types/api'

const stepTitles: Record<string, string> = {
  patent_intelligence: 'Patent intelligence',
  competitor_intelligence: 'Competitor landscape',
  claim_chart: 'Claim chart analysis',
  valuation: 'IP valuation',
  negotiation: 'Negotiation strategy',
  report_builder: 'Report generation',
  human_review_checkpoint: 'Human review checkpoint',
}
const terminalStates = new Set<AssessmentState>(['review_required', 'completed', 'partial', 'failed'])

export function ProgressPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [status, setStatus] = useState<AssessmentStatus | null>(null)
  const [pollError, setPollError] = useState('')
  const [isStarting, setIsStarting] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const pollLock = useRef(false)
  const startedByThisPage = useRef(false)

  const refresh = useCallback(async () => {
    if (pollLock.current) return
    pollLock.current = true
    try {
      let next = await api.getStatus(id)
      if (next.state === 'created' && !startedByThisPage.current) {
        startedByThisPage.current = true
        setIsStarting(true)
        try {
          next = await api.startAssessment(id)
        } catch (error) {
          startedByThisPage.current = false
          throw error
        }
        setIsStarting(false)
      }
      setStatus(next)
      setLastUpdated(new Date())
      setPollError('')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load assessment progress.'
      setPollError(message)
      if (!pollError) notify(message)
    } finally {
      setIsStarting(false)
      pollLock.current = false
    }
  }, [id, notify, pollError])

  useEffect(() => {
    let active = true
    const runRefresh = async () => { if (active) await refresh() }
    void runRefresh()
    const interval = window.setInterval(() => { void runRefresh() }, 2000)
    return () => { active = false; window.clearInterval(interval) }
  }, [refresh])

  const done = Boolean(status && terminalStates.has(status.state))
  const steps = status?.steps || []
  const stepMap = useMemo(() => new Map(steps.map((step) => [step.name, step])), [steps])
  const failed = status?.state === 'failed' || steps.some((step) => step.state === 'failed')

  function stateFor(name: string): StepStatus['state'] {
    const step = stepMap.get(name)?.state
    if (step) return step
    if (status?.state === 'running' && name === 'patent_intelligence') return 'running'
    return 'pending'
  }

  const coreDone = done && !failed
  return (
    <div className="page-content progress-page">
      <div className="page-intro-row"><div><div className="breadcrumb-mini"><Link to="/">Workspace</Link><span>/</span><Link to={`/assessments/${encodeURIComponent(id)}/commercial`}>Assessment</Link><span>/</span><span>Progress</span></div><span className="section-eyebrow">ASSESSMENT PIPELINE</span><h1>{failed ? 'Assessment needs attention' : coreDone ? 'Your assessment is ready' : 'Building your assessment'}</h1><p>{failed ? 'A workflow step failed. Review the details below and retry or continue with available results.' : coreDone ? 'The workflow finished. Placeholder outputs remain clearly marked for review.' : 'The analysis steps are running in dependency order. This page refreshes status every 2 seconds.'}</p></div>
        <div className={`pipeline-state-chip ${failed ? 'pipeline-chip-failed' : coreDone ? 'pipeline-chip-done' : 'pipeline-chip-running'}`}><span className="pipeline-chip-dot" />{failed ? 'Needs attention' : coreDone ? status?.state === 'review_required' || status?.human_review_pending ? 'Review required' : 'Completed' : <><span className="spinner spinner-small" /> In progress</>}</div>
      </div>

      <section className="pipeline-card">
        <div className="pipeline-card-head"><div><h2>Assessment workflow</h2><p>Three workstreams branch from the patent profile, then rejoin before the report.</p></div><div className="pipeline-updated"><Clock3 size={14} />{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}` : 'Waiting for backend'}</div></div>
        {!status && !pollError && <div className="pipeline-loading"><span className="spinner" /> Connecting to assessment…</div>}
        {pollError && <div className="pipeline-error"><AlertTriangle size={18} /><div><strong>Could not refresh status</strong><p>{pollError}</p></div><button className="button button-secondary button-small" onClick={() => void refresh()}><RotateCw size={14} /> Retry</button></div>}
        <div className="pipeline-flow">
          <div className="flow-node-wrap flow-patent"><StepNode name="patent_intelligence" title={stepTitles.patent_intelligence} subtitle="Profile and technical features" state={stateFor('patent_intelligence')} error={stepMap.get('patent_intelligence')?.error} /></div>
          <div className="branch-label"><span /> PARALLEL WORKSTREAMS <span /></div>
          <div className="flow-branches">
            <StepNode name="competitor_intelligence" title={stepTitles.competitor_intelligence} subtitle="Commercially relevant targets" state={stateFor('competitor_intelligence')} error={stepMap.get('competitor_intelligence')?.error} stub />
            <StepNode name="claim_chart" title={stepTitles.claim_chart} subtitle="Limitations and evidence" state={stateFor('claim_chart')} error={stepMap.get('claim_chart')?.error} stub />
            <StepNode name="valuation" title={stepTitles.valuation} subtitle="Deterministic Python methods" state={stateFor('valuation')} error={stepMap.get('valuation')?.error} live />
          </div>
          <div className="flow-join" />
          <div className="flow-node-wrap flow-negotiation"><StepNode name="negotiation" title={stepTitles.negotiation} subtitle="Waits for valuation + competitors" state={stateFor('negotiation')} error={stepMap.get('negotiation')?.error} /></div>
          <div className="flow-node-wrap flow-report"><StepNode name="report_builder" title={stepTitles.report_builder} subtitle="Assembles nine report sections" state={stateFor('report_builder')} error={stepMap.get('report_builder')?.error} /></div>
          <div className="flow-node-wrap flow-review"><StepNode name="human_review_checkpoint" title={stepTitles.human_review_checkpoint} subtitle="Human confirmation is part of the process" state={stateFor('human_review_checkpoint')} error={stepMap.get('human_review_checkpoint')?.error} review /></div>
        </div>
        <div className="pipeline-legend"><span><i className="legend-done" />Completed</span><span><i className="legend-running" />Running</span><span><i className="legend-pending" />Pending</span><span><i className="legend-stub" />Placeholder module</span></div>
      </section>

      <div className="pipeline-bottom"><div className="pipeline-honesty"><span className="info-dot">i</span><span>Patent extraction, competitor discovery, and claim mapping are placeholders. Valuation math is live and deterministic; missing inputs are shown in the report.</span></div>{done && <button className="button button-primary" onClick={() => navigate(`/assessments/${encodeURIComponent(id)}/report`)}>{failed ? 'View available results' : 'Open report'} <ArrowRight size={16} /></button>}{!done && isStarting && <span className="pipeline-wait"><InlineSpinner label="Starting workflow" /></span>}</div>
      {steps.some((step) => step.error) && <section className="pipeline-error-list"><h3>Step details</h3>{steps.filter((step) => step.error).map((step) => <p key={step.name}><strong>{stepTitles[step.name] || step.name}:</strong> {step.error}</p>)}</section>}
    </div>
  )
}

function StepNode({ name, title, subtitle, state, error, stub, live, review }: { name: string; title: string; subtitle: string; state: StepStatus['state']; error?: string | null; stub?: boolean; live?: boolean; review?: boolean }) {
  const icon = state === 'completed' ? <Check size={16} /> : state === 'running' ? <LoaderCircle size={16} className="animate-spin" /> : state === 'failed' ? <AlertTriangle size={16} /> : state === 'skipped' ? <Circle size={14} /> : <span>{name === 'human_review_checkpoint' ? 'R' : name === 'report_builder' ? '4' : name === 'negotiation' ? '3' : name === 'patent_intelligence' ? '1' : name === 'valuation' ? 'V' : name === 'claim_chart' ? 'C' : '2'}</span>
  return <article className={`step-node step-${state} ${stub ? 'step-node-stub' : ''} ${live ? 'step-node-live' : ''} ${review ? 'step-node-review' : ''}`} title={error || (stub ? 'Placeholder output — not a completed analysis.' : undefined)}>
    <span className="step-icon">{icon}</span><div className="step-node-copy"><div className="step-node-title">{title}{live && <span className="live-tag">LIVE</span>}{stub && <span className="stub-tag">PLACEHOLDER</span>}</div><p>{error ? 'Step failed' : subtitle}</p></div><span className="step-state-text">{state === 'completed' ? review ? 'Review' : 'Done' : state === 'running' ? 'Running' : state === 'failed' ? 'Failed' : state === 'skipped' ? 'Skipped' : 'Queued'}</span>
  </article>
}
