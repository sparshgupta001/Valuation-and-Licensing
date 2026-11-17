import { Check, CircleAlert, Sparkles } from 'lucide-react'

export function PlaceholderBadge({ className = '' }: { className?: string }) {
  return <span className={`tag tag-placeholder ${className}`} title="This module returns placeholder output and does not represent completed analysis."><Sparkles size={12} /> Placeholder</span>
}

export function ReviewBadge({ reviewed = false, className = '' }: { reviewed?: boolean; className?: string }) {
  return reviewed
    ? <span className={`tag tag-reviewed ${className}`} title="The human review endpoint recorded an approval or correction."><Check size={12} /> Review recorded</span>
    : <span className={`tag tag-review ${className}`} title="The API marks this output as needing human validation."><CircleAlert size={12} /> Needs review</span>
}

export function ClaimBadge({ assessment }: { assessment: 'STRONG' | 'PARTIAL' | 'GAP' }) {
  return <span className={`claim-badge claim-${assessment.toLowerCase()}`}>{assessment}</span>
}

export function SourceBadge({ source }: { source: 'user' | 'extracted' | 'missing' }) {
  const label = source === 'user' ? 'User provided' : source === 'extracted' ? 'Extracted' : 'Not provided'
  return <span className={`source-badge source-${source}`} title={source === 'extracted' ? 'This value came from document extraction.' : undefined}>{label}</span>
}
