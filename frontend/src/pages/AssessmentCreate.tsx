import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent, type ReactNode } from 'react'
import { ArrowLeft, ArrowRight, Check, FileText, FlaskConical, Upload, X } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { InlineSpinner } from '../components/Loading'
import { useToast } from '../context/ToastContext'
import type { AssessmentCreate as AssessmentPayload } from '../types/api'

interface FormValues {
  title: string
  application_number: string
  technology_domain: string
  owner_name: string
  filing_date: string
  jurisdiction: string
  current_status: string
  licensing_objective: string
}

const initialValues: FormValues = {
  title: '', application_number: '', technology_domain: '', owner_name: '', filing_date: '',
  jurisdiction: '', current_status: '', licensing_objective: '',
}
const acceptedExtensions = ['.pdf', '.docx', '.json']
const demoPatent = {
  title: 'Adaptive thermal management for battery systems',
  application_number: 'US-2024-0186421-A1',
  abstract: 'A modular system that dynamically routes coolant based on cell-level temperature readings.',
  claims: [{ claim_number: '1', text: 'A battery thermal management system comprising a sensor array and a variable flow controller.' }],
}

function validDocument(file: File): boolean {
  return acceptedExtensions.some((extension) => file.name.toLowerCase().endsWith(extension))
}

export function AssessmentCreatePage() {
  const navigate = useNavigate()
  const { id: routeId } = useParams()
  const { notify } = useToast()
  const [values, setValues] = useState<FormValues>(initialValues)
  const [file, setFile] = useState<File | null>(null)
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues | 'document', string>>>({})
  const [busy, setBusy] = useState(false)
  const [assessmentId, setAssessmentId] = useState(routeId || '')
  const [uploadSaved, setUploadSaved] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const isRetry = Boolean(routeId)

  useEffect(() => {
    setAssessmentId(routeId || '')
    if (routeId) {
      try {
        const stored = window.localStorage.getItem(`strategos:assessment-form:${routeId}`)
        if (stored) setValues(JSON.parse(stored) as FormValues)
      } catch { /* Saved form details are a convenience, not a backend dependency. */ }
    }
  }, [routeId])

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
    setErrors((current) => ({ ...current, [key]: undefined }))
  }

  function acceptFile(nextFile: File | undefined) {
    if (!nextFile) return
    if (!validDocument(nextFile)) {
      setErrors((current) => ({ ...current, document: 'Choose a PDF, DOCX, or JSON document.' }))
      return
    }
    setFile(nextFile)
    setErrors((current) => ({ ...current, document: undefined }))
    setUploadSaved(false)
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    acceptFile(event.dataTransfer.files[0])
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    acceptFile(event.target.files?.[0])
  }

  function loadDemo() {
    setValues({
      title: demoPatent.title,
      application_number: demoPatent.application_number,
      technology_domain: 'Battery energy storage',
      owner_name: 'Northstar Energy Systems',
      filing_date: '2024-03-18',
      jurisdiction: 'United States',
      current_status: 'pending',
      licensing_objective: 'out-license',
    })
    setFile(new File([JSON.stringify(demoPatent, null, 2)], 'northstar-demo-patent.json', { type: 'application/json' }))
    setErrors({})
    setUploadSaved(false)
  }

  function validate(): boolean {
    const next: Partial<Record<keyof FormValues | 'document', string>> = {}
    if (!routeId && !values.title.trim()) next.title = 'Patent title is required.'
    if (!routeId && !values.application_number.trim()) next.application_number = 'Application number is required.'
    if (!file) next.document = routeId ? 'Select the patent document to finish this assessment.' : 'Upload the patent document to continue.'
    else if (!validDocument(file)) next.document = 'Choose a PDF, DOCX, or JSON document.'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!validate()) return
    setBusy(true)
    let activeId = assessmentId
    try {
      if (!activeId) {
        const payload: AssessmentPayload = {
          title: values.title.trim(),
          application_number: values.application_number.trim(),
          technology_domain: values.technology_domain.trim() || null,
          owner_name: values.owner_name.trim() || null,
          filing_date: values.filing_date || null,
          jurisdiction: values.jurisdiction.trim() || null,
          current_status: values.current_status || null,
          licensing_objective: values.licensing_objective || null,
        }
        const created = await api.createAssessment(payload)
        activeId = created.assessment_id
        setAssessmentId(activeId)
        try { window.localStorage.setItem(`strategos:assessment-form:${activeId}`, JSON.stringify(values)) } catch { /* Browser storage is optional. */ }
      }
      const uploaded = await api.uploadDocument(activeId, file!)
      setUploadSaved(true)
      try { window.localStorage.setItem('strategos:lastAssessment', JSON.stringify({ id: activeId, title: values.title || 'Patent assessment', application_number: values.application_number, updated_at: new Date().toISOString() })) } catch { /* Browser storage is optional. */ }
      notify(`${uploaded.filename} uploaded and ready.`, 'success')
      navigate(`/assessments/${encodeURIComponent(activeId)}/commercial`, { state: { upload: uploaded } })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'The assessment could not be created.'
      notify(message)
      if (activeId && !routeId) navigate(`/assessments/${encodeURIComponent(activeId)}/details`, { replace: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page-content form-page">
      <div className="page-intro-row">
        <div><div className="breadcrumb-mini"><Link to="/">Workspace</Link><span>/</span><span>New assessment</span></div><span className="section-eyebrow">STEP 01 OF 02</span><h1>{isRetry ? 'Add your patent document' : 'Create IP assessment'}</h1><p>Start with the essentials. You can add more context in the next step.</p></div>
        <button type="button" className="button button-quiet demo-button" onClick={loadDemo} disabled={busy}><FlaskConical size={16} /> Load demo data</button>
      </div>

      <div className="form-progress"><span className="form-progress-active" /><span /><span /></div>
      <form onSubmit={submit} noValidate>
        <section className="form-card">
          <div className="form-card-heading"><div className="form-card-icon"><FileText size={18} /></div><div><h2>Patent basics</h2><p>Identify the asset and its current position.</p></div><span className="required-note"><i /> Required fields</span></div>
          <div className="form-grid">
            <Field label="Patent title" required error={errors.title} className="span-two"><input className={`form-control ${errors.title ? 'form-control-error' : ''}`} value={values.title} onChange={(event) => update('title', event.target.value)} placeholder="e.g. Adaptive thermal management system" disabled={busy || isRetry} /></Field>
            <Field label="Application number" required error={errors.application_number}><input className={`form-control ${errors.application_number ? 'form-control-error' : ''}`} value={values.application_number} onChange={(event) => update('application_number', event.target.value)} placeholder="e.g. US-2024-0186421-A1" disabled={busy || isRetry} /></Field>
            <Field label="Technology domain"><input className="form-control" value={values.technology_domain} onChange={(event) => update('technology_domain', event.target.value)} placeholder="e.g. Energy storage" disabled={busy || isRetry} /></Field>
            <Field label="Owner / company"><input className="form-control" value={values.owner_name} onChange={(event) => update('owner_name', event.target.value)} placeholder="Company or inventor name" disabled={busy || isRetry} /></Field>
            <Field label="Filing date"><input type="date" className="form-control" value={values.filing_date} onChange={(event) => update('filing_date', event.target.value)} disabled={busy || isRetry} /></Field>
            <Field label="Jurisdiction"><input className="form-control" value={values.jurisdiction} onChange={(event) => update('jurisdiction', event.target.value)} placeholder="e.g. United States" disabled={busy || isRetry} /></Field>
            <Field label="Current status"><select className="form-control" value={values.current_status} onChange={(event) => update('current_status', event.target.value)} disabled={busy || isRetry}><option value="">Select status</option><option value="pending">Pending</option><option value="granted">Granted</option><option value="published">Published</option><option value="expired">Expired</option><option value="unknown">Not sure</option></select></Field>
            <Field label="Licensing objective"><select className="form-control" value={values.licensing_objective} onChange={(event) => update('licensing_objective', event.target.value)} disabled={busy || isRetry}><option value="">Choose a direction</option><option value="out-license">Out-license</option><option value="sell">Sell the patent</option><option value="cross-license">Cross-license</option><option value="defensive">Defensive use</option></select></Field>
          </div>
        </section>

        <section className="form-card upload-form-card">
          <div className="form-card-heading"><div className="form-card-icon"><Upload size={18} /></div><div><h2>Patent document</h2><p>Add a source file to keep it with this assessment.</p></div><span className="file-types">PDF · DOCX · JSON</span></div>
          <input ref={fileInputRef} type="file" accept=".pdf,.docx,.json,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/json" className="sr-only" onChange={onFileChange} />
          {!file ? <div className={`dropzone ${errors.document ? 'dropzone-error' : ''}`} onDragOver={(event) => event.preventDefault()} onDrop={onDrop} onClick={() => fileInputRef.current?.click()} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') fileInputRef.current?.click() }}>
            <span className="dropzone-icon"><Upload size={21} /></span><span className="dropzone-title">Drag your patent document here</span><span className="dropzone-subtitle">or <strong>browse files</strong> from your computer</span><span className="dropzone-limit">PDF, DOCX, or JSON · up to 25 MB</span>
          </div> : <div className="selected-file"><span className="selected-file-icon"><FileText size={20} /></span><span className="selected-file-details"><strong>{file.name}</strong><small>{formatBytes(file.size)}{uploadSaved ? ' · Uploaded' : ' · Ready to upload'}</small></span>{uploadSaved && <span className="uploaded-check"><Check size={14} /> Saved</span>}<button type="button" className="icon-button" aria-label="Remove selected file" onClick={() => { setFile(null); setUploadSaved(false) }} disabled={busy}><X size={17} /></button></div>}
          {errors.document && <p className="field-error mt-2">{errors.document}</p>}
          <div className="upload-honesty"><span className="info-dot">i</span><span>For this demo, the backend stores the document but does not extract or verify its contents. Patent analysis is labeled as a placeholder.</span></div>
        </section>

        <div className="form-footer"><Link to="/" className="button button-quiet"><ArrowLeft size={16} /> Back to workspace</Link><button className="button button-primary" type="submit" disabled={busy}>{busy ? <InlineSpinner label="Saving assessment" /> : <>Continue to commercial details <ArrowRight size={16} /></>}</button></div>
      </form>
      <div className="form-privacy"><ShieldSmall /> Your information stays in this demo workspace and is used only to build this assessment.</div>
    </div>
  )
}

function Field({ label, required, error, className = '', children }: { label: string; required?: boolean; error?: string; className?: string; children: ReactNode }) {
  return <label className={`form-field ${className}`}><span className="field-label">{label}{required && <span className="field-required">*</span>}</span>{children}{error && <span className="field-error">{error}</span>}</label>
}

function ShieldSmall() {
  return <span className="shield-small">✓</span>
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
