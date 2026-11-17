import { lazy, Suspense } from 'react'
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { PageSkeleton } from './components/Loading'
import { ToastProvider } from './context/ToastContext'
import { AssessmentCreatePage } from './pages/AssessmentCreate'
import { CommercialInfoPage } from './pages/CommercialInfo'
import { Dashboard } from './pages/Dashboard'
import { ProgressPage } from './pages/Progress'

const ReportPage = lazy(() => import('./pages/Report').then((module) => ({ default: module.ReportPage })))

export default function App() {
  return <BrowserRouter><ToastProvider><Routes><Route element={<AppShell />}>
    <Route path="/" element={<Dashboard />} />
    <Route path="/assessments/new" element={<AssessmentCreatePage />} />
    <Route path="/assessments/:id/details" element={<AssessmentCreatePage />} />
    <Route path="/assessments/:id/commercial" element={<CommercialInfoPage />} />
    <Route path="/assessments/:id/progress" element={<ProgressPage />} />
    <Route path="/assessments/:id/report" element={<Suspense fallback={<div className="page-content"><PageSkeleton rows={3} /></div>}><ReportPage /></Suspense>} />
    <Route path="*" element={<NotFound />} />
  </Route></Routes></ToastProvider></BrowserRouter>
}

function NotFound() {
  return <div className="page-content"><div className="empty-state-card"><h1>That page isn’t here</h1><p>Start from your workspace or create a new patent assessment.</p><Link to="/" className="button button-primary">Go to workspace</Link></div></div>
}
