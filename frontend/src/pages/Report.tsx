import { useCallback, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import { AlertTriangle, ArrowDownToLine, ArrowLeft, Check, ChevronRight, FileJson2, Printer, RefreshCw, Scale, ShieldCheck, Sparkles } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ClaimBadge, PlaceholderBadge, ReviewBadge } from '../components/Badge'
import { PageSkeleton } from '../components/Loading'
import { SystemStatusPanel } from '../components/SystemStatusPanel'
import { useToast } from '../context/ToastContext'
import type { AssessmentResults, AssessmentStatus, Claim, ClaimChartRow, CompetitorTarget, EvidenceItem, NegotiationBrief, ReportSection, ValuationResult } from '../types/api'

const sectionNav = [
  ['overview', 'Patent overview'],
  ['intelligence', 'Patent intelligence'],
  ['competitors', 'Competitor landscape'],
  ['claim-charts', 'Claim charts'],
  ['valuation', 'IP valuation'],
  ['strength', 'Patent strength'],
  ['licensing', 'Licensing strategy'],
  ['negotiation', 'Negotiation strategy'],
  ['recommendations', 'Recommendations'],
] as const

export function ReportPage() {
  const { id = '' } = useParams()
  const { notify } = useToast()
  const [results, setResults] = useState<AssessmentResults | null>(null)
  const [status, setStatus] = useState<AssessmentStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [loadError, setLoadError] = useState('')

  const reload = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true)
    else setRefreshing(true)
    try {
      const [nextResults, nextStatus] = await Promise.all([api.getResults(id), api.getStatus(id)])
      setResults(nextResults)
      setStatus(nextStatus)
      setLoadError('')
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not load this assessment report.'
      setLoadError(message)
      notify(message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [id, notify])

  useEffect(() => { void reload() }, [reload])

  const reviewedSteps = useMemo(() => new Set((results?.human_review_corrections || []).map((item) => String(item.step))), [results])

  function downloadJson() {
    if (!results) return
    try {
      const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `strategos-assessment-${id}.json`
      anchor.click()
      URL.revokeObjectURL(url)
      notify('Report JSON downloaded.', 'success')
    } catch {
      notify('Could not download the report JSON.')
    }
  }

  if (loading) return <div className="page-content"><PageSkeleton rows={3} /></div>
  if (!results?.report) return <div className="page-content"><div className="empty-state-card"><div className="empty-state-icon"><AlertTriangle size={22} /></div><h1>Report not available</h1><p>{loadError || 'Start this assessment to generate report sections.'}</p><Link to={`/assessments/${encodeURIComponent(id)}/progress`} className="button button-primary">View assessment progress <ChevronRight size={16} /></Link></div></div>

  return (
    <div className="page-content report-page">
      <div className="report-titlebar"><div><div className="breadcrumb-mini"><Link to="/">Workspace</Link><span>/</span><span>Assessment report</span></div><span className="section-eyebrow">FINAL IP VALUATION &amp; LICENSING REPORT</span><h1>{results.patent_profile?.title || results.report.patent_overview.summary.split(' (')[0] || 'Patent assessment'}</h1><p>Application {results.patent_profile?.application_number || '—'} <span className="meta-divider">·</span> Prepared {status?.updated_at ? new Date(status.updated_at).toLocaleDateString() : 'just now'}</p></div>
        <div className="report-actions"><button className="button button-secondary" onClick={downloadJson}><ArrowDownToLine size={16} /> Download JSON</button><button className="button button-secondary" onClick={() => { try { window.print() } catch { notify('Print is unavailable in this browser.') } }}><Printer size={16} /> Print / save PDF</button><button className="icon-button refresh-button" title="Refresh report" onClick={() => void reload(true)} disabled={refreshing}><RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /></button></div>
      </div>
      {loadError && <div className="report-error-banner"><AlertTriangle size={17} /> Some report data could not be refreshed. {loadError}<button onClick={() => void reload(true)}>Retry</button></div>}

      <div className="report-summary-strip"><div className="summary-symbol"><Scale size={19} /></div><div><strong>Decision support, with evidence gaps visible</strong><span>Valuation is calculated deterministically. Patent, competitor, and claim-chart outputs are placeholders.</span></div><div className="summary-status">{status?.human_review_pending ? <ReviewBadge /> : <span className="tag tag-reviewed"><Check size={12} /> Review recorded</span>}</div></div>

      <div className="report-layout">
        <aside className="report-anchor-nav"><div className="report-anchor-title">IN THIS REPORT</div>{sectionNav.map(([anchor, title], index) => <a href={`#${anchor}`} key={anchor}><span className="anchor-index">{String(index + 1).padStart(2, '0')}</span>{title}</a>)}<div className="report-anchor-rule" /><Link to={`/assessments/${encodeURIComponent(id)}/progress`} className="anchor-back"><ArrowLeft size={14} /> Pipeline status</Link></aside>

        <div className="report-sections">
          <ReportSectionCard id="overview" section={results.report.patent_overview} step="patent_intelligence" placeholder={false} reviewed={reviewedSteps.has('patent_intelligence')} assessmentId={id} onReviewed={() => void reload(true)}>
            <div className="overview-grid"><InfoCell label="Application number" value={results.patent_profile?.application_number} /><InfoCell label="Owner / company" value={results.patent_profile?.owner_name} /><InfoCell label="Technology domain" value={results.patent_profile?.technology_domain} /><InfoCell label="Filing date" value={results.patent_profile?.filing_date} /><InfoCell label="Jurisdiction" value={results.patent_profile?.jurisdiction} /><InfoCell label="Current status" value={results.patent_profile?.current_status} /></div>
          </ReportSectionCard>

          <ReportSectionCard id="intelligence" section={results.report.patent_intelligence} step="patent_intelligence" placeholder reviewed={reviewedSteps.has('patent_intelligence')} assessmentId={id} onReviewed={() => void reload(true)}>
            <div className="table-wrap"><table className="report-table"><thead><tr><th>Claim</th><th>Type</th><th>Claim text</th><th>Confidence</th><th>Review</th></tr></thead><tbody>{results.patent_profile?.claims?.length ? results.patent_profile.claims.map((claim) => <ClaimTableRow claim={claim} key={claim.claim_number} assessmentId={id} reviewed={reviewedSteps.has('patent_intelligence')} onReviewed={() => void reload(true)} />) : <tr><td colSpan={5}><EmptyInline title="No claim records returned" note="The patent extractor is a placeholder. The uploaded file has not been parsed." /></td></tr>}</tbody></table></div>
            <div className="data-note"><Sparkles size={14} /> Profile values and claim text are not extracted from the uploaded document in this demo.</div>
          </ReportSectionCard>

          <ReportSectionCard id="competitors" section={results.report.competitor_landscape} step="competitor_intelligence" placeholder reviewed={reviewedSteps.has('competitor_intelligence')} assessmentId={id} onReviewed={() => void reload(true)}>
            {results.competitors.length ? <div className="table-wrap"><table className="report-table"><thead><tr><th>Rank</th><th>Company</th><th>Similarity</th><th>Commercial evidence</th><th>Explanation</th><th>Review</th></tr></thead><tbody>{results.competitors.map((target, index) => <CompetitorRow key={`${target.company_name}-${index}`} target={target} rank={index + 1} assessmentId={id} reviewed={reviewedSteps.has('competitor_intelligence')} onReviewed={() => void reload(true)} />)}</tbody></table></div> : <EmptyPanel icon="spark" title="No target companies returned" note="Competitor discovery is a placeholder in this demo. Patent similarity alone will not be presented as a licensing target." />}
          </ReportSectionCard>

          <ReportSectionCard id="claim-charts" section={results.report.claim_charts} step="claim_chart" placeholder reviewed={reviewedSteps.has('claim_chart')} assessmentId={id} onReviewed={() => void reload(true)}>
            {results.claim_charts.length ? results.claim_charts.map((chart) => <div className="claim-chart-block" key={chart.claim_number}><div className="claim-chart-heading"><strong>Independent claim {chart.claim_number}</strong><span>{chart.rows.length} provisional row{chart.rows.length === 1 ? '' : 's'}</span></div><div className="table-wrap"><table className="report-table claim-table"><thead><tr><th>Limitation</th><th>Evidence</th><th>Assessment</th><th>Explanation</th><th>Review</th></tr></thead><tbody>{chart.rows.map((row, index) => <ClaimChartTableRow row={row} key={`${chart.claim_number}-${index}`} assessmentId={id} reviewed={reviewedSteps.has('claim_chart')} onReviewed={() => void reload(true)} />)}</tbody></table></div></div>) : <EmptyPanel icon="spark" title="Claim chart not available" note="The claim chart engine is a placeholder. No limitation-to-product evidence was retrieved." />}
          </ReportSectionCard>

          <ReportSectionCard id="valuation" section={results.report.ip_valuation} step="valuation" placeholder={false} reviewed={reviewedSteps.has('valuation')} assessmentId={id} onReviewed={() => void reload(true)}>
            {results.valuation ? <ValuationSection valuation={results.valuation} assessmentId={id} reviewed={reviewedSteps.has('valuation')} onReviewed={() => void reload(true)} /> : <EmptyPanel icon="chart" title="Valuation result unavailable" note="No valuation output was returned by the API." />}
          </ReportSectionCard>

          <ReportSectionCard id="strength" section={results.report.patent_strength} step="valuation" placeholder={false} reviewed={reviewedSteps.has('valuation')} assessmentId={id} onReviewed={() => void reload(true)}>
            {results.valuation && <StrengthSection valuation={results.valuation} />}
          </ReportSectionCard>

          <ReportSectionCard id="licensing" section={results.report.licensing_strategy} step="competitor_intelligence" placeholder reviewed={reviewedSteps.has('competitor_intelligence')} assessmentId={id} onReviewed={() => void reload(true)}>
            <div className="strategy-note"><ShieldCheck size={18} /><p>Use the licensing objective and any supplied commercial context to guide human review. The demo does not make an outreach recommendation from patent similarity alone.</p></div>
          </ReportSectionCard>

          <ReportSectionCard id="negotiation" section={results.report.negotiation_strategy} step="negotiation" placeholder={false} reviewed={reviewedSteps.has('negotiation')} assessmentId={id} onReviewed={() => void reload(true)}>
            {results.negotiation ? <NegotiationSection brief={results.negotiation} assessmentId={id} reviewed={reviewedSteps.has('negotiation')} onReviewed={() => void reload(true)} /> : <EmptyPanel icon="chart" title="Negotiation brief unavailable" note="The workflow did not return a negotiation result." />}
          </ReportSectionCard>

          <ReportSectionCard id="recommendations" section={results.report.recommendations} step="report_builder" placeholder={false} reviewed={reviewedSteps.has('report_builder')} assessmentId={id} onReviewed={() => void reload(true)}>
            <div className="recommendation-summary"><div className="recommendation-icon"><Sparkles size={17} /></div><div><strong>Risks, missing information, and next steps</strong><p>{results.report.recommendations.summary}</p></div></div>
            {results.errors.length > 0 && <div className="runtime-errors"><strong>Workflow errors</strong>{results.errors.map((error, index) => <p key={index}>{error}</p>)}</div>}
          </ReportSectionCard>

          <SystemStatusPanel />
          <div className="report-endnote"><span><ShieldCheck size={15} /> Human review is required before relying on these outputs.</span><button className="button button-primary" onClick={downloadJson}><FileJson2 size={16} /> Download report data</button></div>
        </div>
      </div>
    </div>
  )
}

function ReportSectionCard({ id, section, step, placeholder, reviewed, assessmentId, onReviewed, children }: { id: string; section: ReportSection; step: string; placeholder?: boolean; reviewed: boolean; assessmentId: string; onReviewed: () => void; children?: ReactNode }) {
  return <section className="report-card" id={id}>
    <div className="report-card-heading"><div className="report-section-heading"><span className="report-section-kicker">STRATEGOS REPORT</span><h2>{section.title}</h2></div><div className="report-card-badges">{placeholder && <PlaceholderBadge />}{section.needs_human_review && <ReviewBadge />}</div></div>
    <p className="report-section-summary">{section.summary}</p>
    {section.evidence?.length > 0 && <EvidenceList evidence={section.evidence} />}
    {children}
    {section.needs_human_review && <ReviewControl assessmentId={assessmentId} step={step} label={section.title} reviewed={reviewed} onReviewed={onReviewed} />}
  </section>
}

function ReviewControl({ assessmentId, step, label, reviewed, onReviewed, correctionSeed = {} }: { assessmentId: string; step: string; label: string; reviewed: boolean; onReviewed: () => void; correctionSeed?: Record<string, unknown> }) {
  const { notify } = useToast()
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const [correction, setCorrection] = useState(JSON.stringify(correctionSeed, null, 2))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(approveOnly = false) {
    let parsed: Record<string, unknown> = {}
    if (!approveOnly) {
      try {
        const value: unknown = JSON.parse(correction)
        if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('Enter a JSON object.')
        parsed = value as Record<string, unknown>
      } catch (parseError) {
        setError(parseError instanceof Error ? parseError.message : 'Correction must be a valid JSON object.')
        return
      }
    }
    setBusy(true)
    try {
      await api.submitReview(assessmentId, { step, correction: parsed, reviewer_note: note.trim() || (approveOnly ? `Approved ${label} in demo review.` : null) })
      notify(`${label}: review recorded.`, 'success')
      setOpen(false)
      onReviewed()
    } catch (submitError) {
      notify(submitError instanceof Error ? submitError.message : 'Could not submit the review.')
    } finally {
      setBusy(false)
    }
  }

  return <>
    <div className="review-control-row"><div><ReviewBadge /><span className="review-control-hint">{reviewed ? 'The API has recorded a review; the source output remains flagged for validation.' : 'This output is provisional and should be checked by a person.'}</span></div><button className={`button ${reviewed ? 'button-quiet' : 'button-review'} button-small`} onClick={() => setOpen(true)}>{reviewed ? 'Edit / approve again' : 'Edit / approve'}</button></div>
    {open && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false) }}><div className="review-modal" role="dialog" aria-modal="true" aria-labelledby={`review-title-${step}`}><div className="review-modal-head"><span className="review-modal-icon"><ShieldCheck size={19} /></span><div><h2 id={`review-title-${step}`}>Review {label}</h2><p>Record an approval or a correction for this report area.</p></div><button type="button" className="icon-button" aria-label="Close review" onClick={() => setOpen(false)}>×</button></div><form onSubmit={(event) => { event.preventDefault(); void submit(false) }}><label className="form-field"><span className="field-label">Correction data <span className="field-optional">Optional JSON object</span></span><textarea className="form-control review-json" value={correction} onChange={(event) => { setCorrection(event.target.value); setError('') }} spellCheck={false} /></label><label className="form-field mt-4"><span className="field-label">Reviewer note <span className="field-optional">Optional</span></span><textarea className="form-control form-textarea" value={note} onChange={(event) => setNote(event.target.value)} placeholder="What did you validate or change?" rows={3} /></label>{error && <div className="inline-validation mt-3">{error}</div>}<div className="review-modal-footer"><button type="button" className="button button-quiet" onClick={() => setOpen(false)}>Cancel</button><button type="button" className="button button-secondary" onClick={() => void submit(true)} disabled={busy}>{busy ? 'Saving…' : 'Approve as shown'}</button><button type="submit" className="button button-primary" disabled={busy}>Save correction</button></div></form></div></div>}
  </>
}

function ClaimTableRow({ claim, assessmentId, reviewed, onReviewed }: { claim: Claim; assessmentId: string; reviewed: boolean; onReviewed: () => void }) {
  return <tr><td><strong>Claim {claim.claim_number}</strong></td><td>{claim.independent ? 'Independent' : `Dependent${claim.depends_on.length ? ` on ${claim.depends_on.join(', ')}` : ''}`}</td><td className="claim-text-cell">{claim.text || 'No claim text returned.'}{claim.limitations.length > 0 && <span className="table-subtext">{claim.limitations.join(' · ')}</span>}</td><td>{formatPercent(claim.confidence)}</td><td>{claim.needs_human_review && <><ReviewBadge reviewed={reviewed} /><ReviewControl assessmentId={assessmentId} step="patent_intelligence" label={`Claim ${claim.claim_number}`} reviewed={reviewed} onReviewed={onReviewed} correctionSeed={{ claim_number: claim.claim_number }} /></>}</td></tr>
}

function CompetitorRow({ target, rank, assessmentId, reviewed, onReviewed }: { target: CompetitorTarget; rank: number; assessmentId: string; reviewed: boolean; onReviewed: () => void }) {
  return <tr><td><span className="rank-chip">{rank}</span></td><td><strong>{target.company_name}</strong>{target.eligible_for_outreach && <span className="eligible-tag">Evidence qualified</span>}</td><td><span className="similarity-value">{formatPercent(target.similarity_score)}</span></td><td><EvidenceList evidence={[...target.company_activity_evidence, ...target.commercial_relevance_evidence]} compact /></td><td>{target.explanation}</td><td>{target.needs_human_review && <><ReviewBadge reviewed={reviewed} /><ReviewControl assessmentId={assessmentId} step="competitor_intelligence" label={target.company_name} reviewed={reviewed} onReviewed={onReviewed} correctionSeed={{ company_name: target.company_name }} /></>}</td></tr>
}

function ClaimChartTableRow({ row, assessmentId, reviewed, onReviewed }: { row: ClaimChartRow; assessmentId: string; reviewed: boolean; onReviewed: () => void }) {
  return <tr><td>{row.limitation}</td><td><EvidenceList evidence={row.evidence} compact /></td><td><ClaimBadge assessment={row.assessment} /></td><td>{row.explanation}</td><td>{row.needs_human_review && <><ReviewBadge reviewed={reviewed} /><ReviewControl assessmentId={assessmentId} step="claim_chart" label={`Claim ${row.claim_number}: ${row.limitation}`} reviewed={reviewed} onReviewed={onReviewed} correctionSeed={{ claim_number: row.claim_number, limitation: row.limitation }} /></>}</td></tr>
}

function ValuationSection({ valuation, assessmentId, reviewed, onReviewed }: { valuation: ValuationResult; assessmentId: string; reviewed: boolean; onReviewed: () => void }) {
  const methodNames: Record<string, string> = { income_dcf: 'Income approach', relief_from_royalty: 'Relief-from-royalty', cost_approach: 'Cost approach' }
  const chartData = [
    { name: 'P10', value: valuation.percentiles.p10 },
    { name: 'P50', value: valuation.percentiles.p50 },
    { name: 'P90', value: valuation.percentiles.p90 },
  ].filter((item): item is { name: string; value: number } => item.value !== null && Number.isFinite(item.value))
  return <>
    <div className="valuation-method-grid">{valuation.methods.map((method) => <article className={`method-card ${method.available ? '' : 'method-unavailable'}`} key={method.method}><div className="method-topline"><span>{methodNames[method.method] || method.method}</span>{method.available ? <span className="method-live-indicator"><i /> Calculated</span> : <span className="method-missing-indicator">Inputs needed</span>}</div><strong>{method.available && method.value !== null ? formatMoney(method.value, method.currency) : '—'}</strong>{method.notes.map((note, index) => <p key={index}>{note}</p>)}</article>)}</div>
    <div className="valuation-summary-row"><div className="valuation-estimate"><span>Combined estimate</span><strong>{valuation.combined_estimate !== null ? formatMoney(valuation.combined_estimate, valuation.percentiles.currency) : 'Not available'}</strong></div><div className="valuation-confidence"><span>Confidence score</span><strong>{formatPercent(valuation.confidence)}</strong><small>Human review required</small></div><div className="valuation-estimate-note">The combined estimate is the simple mean of available method outputs in this scaffold. Review assumptions before relying on it.</div></div>
    <div className="chart-panel"><div className="chart-panel-title"><div><strong>Monte Carlo valuation range</strong><span>Seeded 10,000-draw simulation</span></div>{chartData.length > 0 && <span className="chart-currency">{valuation.percentiles.currency}</span>}</div>{chartData.length ? <div className="range-chart"><ResponsiveContainer width="100%" height={220}><BarChart data={chartData} margin={{ top: 12, right: 12, left: 16, bottom: 4 }}><CartesianGrid stroke="#edf1f0" vertical={false} /><XAxis dataKey="name" tickLine={false} axisLine={false} tick={{ fill: '#78898d', fontSize: 12 }} /><YAxis tickLine={false} axisLine={false} width={92} tickFormatter={(value: number) => formatCompactCurrency(value)} tick={{ fill: '#94a2a5', fontSize: 10 }} /><Tooltip formatter={(value) => formatMoney(Number(value), valuation.percentiles.currency)} contentStyle={{ borderRadius: 12, borderColor: '#e3eae8', boxShadow: '0 8px 24px rgba(25,50,58,.08)' }} /><Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={56}>{chartData.map((entry) => <Cell key={entry.name} fill={entry.name === 'P50' ? '#39796f' : '#a6c7bd'} />)}</Bar></BarChart></ResponsiveContainer></div> : <EmptyInline title="Range unavailable" note="At least one valuation method needs sufficient inputs before percentiles can be calculated." />}
      <div className="percentile-cards"><PercentileCard label="P10 · Conservative" value={valuation.percentiles.p10} currency={valuation.percentiles.currency} /><PercentileCard label="P50 · Median" value={valuation.percentiles.p50} currency={valuation.percentiles.currency} /><PercentileCard label="P90 · Upside" value={valuation.percentiles.p90} currency={valuation.percentiles.currency} /></div>
    </div>
    <div className="assumption-panel"><div className="assumption-heading"><span className="assumption-icon"><Scale size={16} /></span><strong>Assumptions &amp; method notes</strong></div>{valuation.assumptions.length ? <ul>{valuation.assumptions.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>No financial assumptions were supplied.</p>}{valuation.needs_human_review && <div className="review-control-inline"><ReviewBadge reviewed={reviewed} /><ReviewControl assessmentId={assessmentId} step="valuation" label="IP valuation" reviewed={reviewed} onReviewed={onReviewed} correctionSeed={{ assessment_id: valuation.assessment_id }} /></div>}</div>
  </>
}

function StrengthSection({ valuation }: { valuation: ValuationResult }) {
  const score = valuation.patent_strength_score
  return <div className="strength-layout"><div className="strength-score-card"><div className="strength-gauge" style={{ '--score': `${score ?? 0}%` } as CSSProperties}><div><strong>{score === null ? '—' : score.toFixed(0)}</strong><span>/ 100</span></div></div><div><strong>Patent strength score</strong><span>{score === null ? 'No rubric inputs supplied' : 'Weighted expert-input rubric'}</span></div></div><div className="strength-rubric"><div className="rubric-heading"><ShieldCheck size={17} /><strong>Score rubric</strong></div><p>{valuation.strength_score_rubric}</p><div className="rubric-caveat"><AlertTriangle size={15} />No dimension-level scores are returned by the API, so a component breakdown is not shown.</div></div></div>
}

function NegotiationSection({ brief, assessmentId, reviewed, onReviewed }: { brief: NegotiationBrief; assessmentId: string; reviewed: boolean; onReviewed: () => void }) {
  const low = brief.target_low_rate
  const high = brief.target_high_rate
  const opening = brief.opening_offer_rate
  const rangeMax = Math.max(high || 0, opening || 0, 0.01) * 1.18
  return <>
    <div className="negotiation-rate-grid"><RateCard label="Opening offer" value={opening} tone="offer" /><RateCard label="Target range · low" value={low} tone="low" /><RateCard label="Target range · high" value={high} tone="high" /></div>
    <div className="corridor-panel"><div className="corridor-heading"><div><strong>Royalty corridor</strong><span>Royalty base: {brief.royalty_base || 'Not provided'}</span></div><span className="corridor-unit">ANNUAL RATE</span></div>{low !== null && high !== null ? <div className="corridor-track-wrap"><div className="corridor-track"><span className="corridor-fill" style={{ left: `${Math.max(0, low / rangeMax * 100)}%`, width: `${Math.max(0, (high - low) / rangeMax * 100)}%` }} />{opening !== null && <span className="corridor-marker" style={{ left: `${Math.min(100, opening / rangeMax * 100)}%` }} title={`Opening ${formatPercent(opening)}`} />}</div><div className="corridor-endpoints"><span>0%</span><span>{formatPercent(rangeMax)}</span></div><div className="corridor-labels"><span><i className="corridor-legend-band" />Target range</span><span><i className="corridor-legend-marker" />Opening offer</span></div></div> : <EmptyInline title="Corridor not calculated" note={brief.missing_inputs.length ? `Add: ${brief.missing_inputs.join(', ')}.` : 'The required financial inputs are not available.'} />}</div>
    <div className="scenario-grid"><div className="scenario-card"><div className="scenario-card-title"><span className="scenario-icon"><Scale size={15} /></span><strong>Scenario analysis</strong></div>{brief.scenario_analysis.length ? <ul>{brief.scenario_analysis.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>No scenarios returned.</p>}</div><div className="scenario-card"><div className="scenario-card-title"><span className="scenario-icon scenario-icon-gold"><Sparkles size={15} /></span><strong>Negotiation points</strong></div>{brief.negotiation_points.length ? <ul>{brief.negotiation_points.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>No negotiation points returned.</p>}</div></div>
    {brief.needs_human_review && <div className="review-control-inline"><ReviewBadge reviewed={reviewed} /><ReviewControl assessmentId={assessmentId} step="negotiation" label="Negotiation strategy" reviewed={reviewed} onReviewed={onReviewed} correctionSeed={{ opening_offer_rate: opening, target_low_rate: low, target_high_rate: high }} /></div>}
  </>
}

function RateCard({ label, value, tone }: { label: string; value: number | null; tone: string }) {
  return <div className={`rate-card rate-${tone}`}><span>{label}</span><strong>{formatPercent(value)}</strong><small>{value === null ? 'Requires more input' : 'Per royalty base'}</small></div>
}

function PercentileCard({ label, value, currency }: { label: string; value: number | null; currency: string }) {
  return <div className="percentile-card"><span>{label}</span><strong>{value === null ? '—' : formatMoney(value, currency)}</strong></div>
}

function InfoCell({ label, value }: { label: string; value?: string | null }) {
  return <div className="overview-cell"><span>{label}</span><strong>{value || 'Not provided'}</strong></div>
}

function EvidenceList({ evidence, compact = false }: { evidence: EvidenceItem[] | string[]; compact?: boolean }) {
  if (!evidence.length) return <span className="no-evidence">No evidence attached</span>
  return <ul className={`evidence-list ${compact ? 'evidence-compact' : ''}`}>{evidence.map((item, index) => {
    const text = typeof item === 'string' ? item : [item.document_name || 'Source document', item.page ? `p. ${item.page}` : '', item.passage].filter(Boolean).join(' · ')
    return <li key={index} title={text}>{text}</li>
  })}</ul>
}

function EmptyInline({ title, note }: { title: string; note: string }) {
  return <div className="empty-inline"><span className="empty-inline-dot" /><div><strong>{title}</strong><p>{note}</p></div></div>
}

function EmptyPanel({ icon, title, note }: { icon: 'spark' | 'chart'; title: string; note: string }) {
  return <div className="report-empty-panel"><span className="empty-panel-icon">{icon === 'spark' ? <Sparkles size={18} /> : <Scale size={18} />}</span><div><strong>{title}</strong><p>{note}</p></div></div>
}

function formatMoney(value: number, currency = 'USD'): string {
  try { return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value) } catch { return `${currency} ${value.toLocaleString()}` }
}

function formatCompactCurrency(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`
  return `$${value.toFixed(0)}`
}

function formatPercent(value: number | null): string {
  return value === null || !Number.isFinite(value) ? '—' : `${(value * 100).toFixed(value * 100 < 10 ? 1 : 0)}%`
}
