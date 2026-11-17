import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowRight, Check, CircleHelp, Save, SkipForward } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { InlineSpinner } from '../components/Loading'
import { SourceBadge } from '../components/Badge'
import { useToast } from '../context/ToastContext'
import type { CommercialInfo as CommercialPayload, InputValue } from '../types/api'

type FieldKey = keyof CommercialPayload
type InputKind = 'text' | 'textarea' | 'number' | 'percent' | 'list'
interface FieldConfig { key: FieldKey; label: string; placeholder: string; helper?: string; kind?: InputKind; group: string }

const fieldGroups: Array<{ title: string; subtitle: string; icon: string; fields: FieldConfig[] }> = [
  {
    title: 'Technical context', subtitle: 'Help us understand where the invention fits.', icon: '01',
    fields: [
      { key: 'product_description', label: 'Product or use case', placeholder: 'What product could use this technology?', kind: 'textarea', group: 'Technical context' },
      { key: 'target_markets', label: 'Target markets', placeholder: 'e.g. grid storage, electric vehicles', kind: 'text', group: 'Technical context' },
      { key: 'known_competitors', label: 'Known companies in this space', placeholder: 'Separate company names with commas', kind: 'list', group: 'Technical context' },
    ],
  },
  {
    title: 'Market and financial inputs', subtitle: 'Numbers are optional. Percentage inputs are entered as whole percentages.', icon: '02',
    fields: [
      { key: 'market_size', label: 'Addressable market size', placeholder: 'e.g. 250000000', kind: 'number', group: 'Market and financial inputs', helper: 'USD estimate for the relevant market.' },
      { key: 'annual_revenue', label: 'Annual royalty base / revenue', placeholder: 'e.g. 42000000', kind: 'number', group: 'Market and financial inputs', helper: 'Revenue base the royalty would apply to.' },
      { key: 'forecast_revenue', label: 'Revenue forecast by year', placeholder: 'e.g. 42000000, 47000000, 51000000', kind: 'list', group: 'Market and financial inputs', helper: 'Comma-separated USD values, one per year.' },
      { key: 'forecast_cash_flows', label: 'Cash flow forecast by year', placeholder: 'e.g. 9000000, 11000000, 12500000', kind: 'list', group: 'Market and financial inputs', helper: 'Comma-separated USD values for the DCF approach.' },
      { key: 'gross_margin', label: 'Gross margin', placeholder: 'e.g. 34', kind: 'percent', group: 'Market and financial inputs' },
      { key: 'incremental_margin', label: 'Incremental margin attributable to the technology', placeholder: 'e.g. 18', kind: 'percent', group: 'Market and financial inputs', helper: 'Enter 18 for 18%.' },
      { key: 'discount_rate', label: 'Discount rate', placeholder: 'e.g. 12', kind: 'percent', group: 'Market and financial inputs', helper: 'Enter 12 for 12%.' },
      { key: 'tax_rate', label: 'Tax rate', placeholder: 'e.g. 25', kind: 'percent', group: 'Market and financial inputs' },
      { key: 'royalty_rate', label: 'Comparable royalty rate', placeholder: 'e.g. 4', kind: 'percent', group: 'Market and financial inputs', helper: 'Enter 4 for 4%; used as a comparable rate.' },
      { key: 'reproduction_cost', label: 'Reproduction cost', placeholder: 'e.g. 1800000', kind: 'number', group: 'Market and financial inputs' },
      { key: 'development_cost', label: 'Development cost to date', placeholder: 'e.g. 2400000', kind: 'number', group: 'Market and financial inputs' },
      { key: 'commercialization_cost', label: 'Remaining commercialization cost', placeholder: 'e.g. 600000', kind: 'number', group: 'Market and financial inputs' },
      { key: 'design_around_cost', label: 'Estimated design-around cost', placeholder: 'e.g. 3200000', kind: 'number', group: 'Market and financial inputs' },
    ],
  },
  {
    title: 'Licensing preferences', subtitle: 'Optional information to shape the negotiation brief.', icon: '03',
    fields: [
      { key: 'comparable_agreements', label: 'Comparable agreements', placeholder: 'Describe relevant deals, sources, or terms', kind: 'textarea', group: 'Licensing preferences' },
      { key: 'additional_context', label: 'Anything else we should know?', placeholder: 'Constraints, timing, or negotiation priorities', kind: 'textarea', group: 'Licensing preferences' },
    ],
  },
]

const allFields = fieldGroups.flatMap((group) => group.fields)
const percentKeys = new Set<FieldKey>(['gross_margin', 'incremental_margin', 'discount_rate', 'tax_rate', 'royalty_rate'])
const numericKeys = new Set<FieldKey>(['market_size', 'annual_revenue', 'reproduction_cost', 'development_cost', 'commercialization_cost', 'design_around_cost'])
const listKeys = new Set<FieldKey>(['forecast_revenue', 'forecast_cash_flows', 'known_competitors'])

function storageKey(id: string) { return `strategos:commercial:${id}` }

export function CommercialInfoPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { notify } = useToast()
  const [values, setValues] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<'save' | 'start' | null>(null)
  const [saved, setSaved] = useState(false)
  const [fieldError, setFieldError] = useState('')
  const upload = (location.state as { upload?: { filename: string; size_bytes: number } } | null)?.upload

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(storageKey(id))
      if (stored) setValues(JSON.parse(stored) as Record<string, string>)
    } catch {
      setValues({})
    }
  }, [id])

  const completedCount = useMemo(() => allFields.filter((field) => values[field.key]?.trim()).length, [values])

  function change(key: FieldKey, value: string) {
    const next = { ...values, [key]: value }
    setValues(next)
    setSaved(false)
    setFieldError('')
    try { window.localStorage.setItem(storageKey(id), JSON.stringify(next)) } catch { /* Browser storage is optional. */ }
  }

  function buildPayload(): CommercialPayload | null {
    const output: CommercialPayload = {}
    const invalid: string[] = []
    for (const field of allFields) {
      const raw = values[field.key]?.trim() || ''
      let inputValue: InputValue
      if (!raw) {
        inputValue = { value: null, source: 'missing', evidence: [] }
      } else if (listKeys.has(field.key)) {
        const items = raw.split(',').map((item) => item.trim()).filter(Boolean)
        const numericList = field.key === 'forecast_revenue' || field.key === 'forecast_cash_flows'
        const parsed = numericList ? items.map(Number) : items
        if (numericList && parsed.some((item) => !Number.isFinite(item))) invalid.push(field.label)
        inputValue = { value: parsed, source: 'user', evidence: [] }
      } else if (percentKeys.has(field.key)) {
        const parsed = Number(raw)
        if (!Number.isFinite(parsed) || parsed < 0 || parsed > 100) invalid.push(field.label)
        inputValue = { value: parsed / 100, source: 'user', evidence: [] }
      } else if (numericKeys.has(field.key)) {
        const parsed = Number(raw)
        if (!Number.isFinite(parsed) || parsed < 0) invalid.push(field.label)
        inputValue = { value: parsed, source: 'user', evidence: [] }
      } else {
        inputValue = { value: raw, source: 'user', evidence: [] }
      }
      output[field.key] = inputValue
    }
    if (invalid.length) {
      setFieldError(`Check these values: ${invalid.join(', ')}.`)
      return null
    }
    return output
  }

  async function saveOnly(event?: FormEvent) {
    event?.preventDefault()
    const payload = buildPayload()
    if (!payload) return false
    setBusy('save')
    try {
      await api.saveCommercialInfo(id, payload)
      setSaved(true)
      notify('Commercial information saved.', 'success')
      return true
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Could not save commercial information.')
      return false
    } finally {
      setBusy(null)
    }
  }

  async function startAssessment() {
    const payload = buildPayload()
    if (!payload) return
    setBusy('start')
    try {
      await api.saveCommercialInfo(id, payload)
      setSaved(true)
      navigate(`/assessments/${encodeURIComponent(id)}/progress`, { state: { start: true } })
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Could not save commercial information.')
      setBusy(null)
    }
  }

  function skip() {
    navigate(`/assessments/${encodeURIComponent(id)}/progress`, { state: { start: true } })
  }

  return (
    <div className="page-content form-page commercial-page">
      <div className="page-intro-row">
        <div><div className="breadcrumb-mini"><Link to="/">Workspace</Link><span>/</span><Link to={`/assessments/${encodeURIComponent(id)}/details`}>Assessment</Link><span>/</span><span>Commercial information</span></div><span className="section-eyebrow">STEP 02 OF 02</span><h1>Technical &amp; commercial information</h1><p>Every field is optional. Add what you know and leave the rest blank.</p></div>
        <div className="completion-chip"><span className="completion-ring">{completedCount}</span><span><strong>{completedCount} added</strong><small>of {allFields.length} optional inputs</small></span></div>
      </div>
      <div className="form-progress"><span className="form-progress-done" /><span className="form-progress-active" /><span /></div>

      {upload && <div className="upload-result-banner"><span className="upload-result-icon"><Check size={15} /></span><div><strong>Document uploaded</strong><span>{upload.filename} · {formatBytes(upload.size_bytes)}</span></div><span className="upload-storage-note">Stored with this assessment</span></div>}
      <div className="honesty-callout"><CircleHelp size={17} /><span><strong>About data sources:</strong> Patent document extraction is not connected in this demo. Values you add here are marked <b>User provided</b>; blank fields are marked <b>Not provided</b>.</span></div>

      <form onSubmit={saveOnly}>
        {fieldGroups.map((group) => <section className="form-card commercial-group" key={group.title}>
          <div className="form-card-heading"><span className="group-number">{group.icon}</span><div><h2>{group.title}</h2><p>{group.subtitle}</p></div></div>
          <div className="form-grid">
            {group.fields.map((field) => <label className={`form-field ${field.kind === 'textarea' ? 'span-two' : ''}`} key={field.key}>
              <span className="field-label-row"><span className="field-label">{field.label}</span><SourceBadge source={values[field.key]?.trim() ? 'user' : 'missing'} /></span>
              {field.kind === 'textarea' ? <textarea className="form-control form-textarea" value={values[field.key] || ''} onChange={(event) => change(field.key, event.target.value)} placeholder={field.placeholder} rows={3} /> : <div className="input-with-unit">{field.kind === 'number' && <span className="input-unit">$</span>}<input className={`form-control ${field.kind === 'number' ? 'has-prefix' : ''} ${field.kind === 'percent' ? 'has-suffix' : ''}`} type={field.kind === 'number' || field.kind === 'percent' ? 'number' : 'text'} min={field.kind === 'number' || field.kind === 'percent' ? 0 : undefined} max={field.kind === 'percent' ? 100 : undefined} step={field.kind === 'percent' ? '0.1' : field.kind === 'number' ? 'any' : undefined} value={values[field.key] || ''} onChange={(event) => change(field.key, event.target.value)} placeholder={field.placeholder} />{field.kind === 'percent' && <span className="input-unit input-unit-suffix">%</span>}</div>}
              {field.helper && <span className="field-helper">{field.helper}</span>}
            </label>)}
          </div>
        </section>)}

        {fieldError && <div className="inline-validation">{fieldError}</div>}
        <div className="form-footer commercial-footer">
          <Link to={`/assessments/${encodeURIComponent(id)}/details`} className="button button-quiet"><ArrowLeft size={16} /> Back</Link>
          <div className="footer-actions"><button type="button" className="button button-quiet" onClick={skip} disabled={busy !== null}><SkipForward size={16} /> Skip for now</button><button type="submit" className="button button-secondary" disabled={busy !== null}>{busy === 'save' ? <InlineSpinner label="Saving" /> : <><Save size={15} /> {saved ? 'Saved' : 'Save'}</>}</button><button type="button" className="button button-primary" onClick={() => void startAssessment()} disabled={busy !== null}>{busy === 'start' ? <InlineSpinner label="Preparing" /> : <>Start assessment <ArrowRight size={16} /></>}</button></div>
        </div>
      </form>
      <div className="commercial-footnote"><span className="shield-small">✓</span> Financial calculations run in Python using the values provided. No AI model calculates your valuation.</div>
    </div>
  )
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
