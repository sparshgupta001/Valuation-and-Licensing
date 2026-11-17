export type SourceTag = 'user' | 'extracted' | 'missing'
export type AssessmentState = 'created' | 'running' | 'review_required' | 'completed' | 'partial' | 'failed'
export type StepState = 'pending' | 'running' | 'completed' | 'skipped' | 'failed'
export type ClaimAssessment = 'STRONG' | 'PARTIAL' | 'GAP'

export interface EvidenceItem {
  document_name: string
  page: number | null
  passage: string
  source_type: string
  uri?: string | null
}

export interface AIOutputMetadata {
  confidence: number
  evidence: EvidenceItem[]
  needs_human_review: boolean
}

export interface InputValue {
  value: unknown | null
  source: SourceTag
  evidence: EvidenceItem[]
}

export interface AssessmentCreate {
  title: string
  application_number: string
  technology_domain?: string | null
  owner_name?: string | null
  filing_date?: string | null
  jurisdiction?: string | null
  current_status?: string | null
  licensing_objective?: string | null
}

export interface CommercialInfo {
  product_description?: InputValue | null
  target_markets?: InputValue | null
  market_size?: InputValue | null
  annual_revenue?: InputValue | null
  forecast_revenue?: InputValue | null
  forecast_cash_flows?: InputValue | null
  gross_margin?: InputValue | null
  royalty_rate?: InputValue | null
  discount_rate?: InputValue | null
  tax_rate?: InputValue | null
  development_cost?: InputValue | null
  reproduction_cost?: InputValue | null
  commercialization_cost?: InputValue | null
  comparable_agreements?: InputValue | null
  known_competitors?: InputValue | null
  design_around_cost?: InputValue | null
  incremental_margin?: InputValue | null
  additional_context?: InputValue | null
}

export interface Claim {
  claim_number: string
  text: string
  independent: boolean
  depends_on: string[]
  limitations: string[]
  confidence: number
  evidence: string[]
  needs_human_review: boolean
}

export interface PatentProfile extends AIOutputMetadata {
  title: string
  application_number: string
  abstract?: string | null
  owner_name?: string | null
  inventors: string[]
  filing_date?: string | null
  jurisdiction?: string | null
  current_status?: string | null
  technology_domain?: string | null
  claims: Claim[]
  technical_features: string[]
}

export interface CompetitorTarget extends AIOutputMetadata {
  company_name: string
  similarity_score: number
  company_activity_evidence: EvidenceItem[]
  commercial_relevance_evidence: EvidenceItem[]
  explanation: string
  eligible_for_outreach: boolean
}

export interface ClaimChartRow extends AIOutputMetadata {
  claim_number: string
  limitation: string
  assessment: ClaimAssessment
  explanation: string
}

export interface ClaimChart {
  claim_number: string
  rows: ClaimChartRow[]
  needs_human_review: boolean
}

export interface MethodResult {
  method: string
  value: number | null
  currency: string
  available: boolean
  notes: string[]
}

export interface PercentileRange {
  p10: number | null
  p50: number | null
  p90: number | null
  currency: string
}

export interface ValuationResult extends AIOutputMetadata {
  assessment_id: string
  methods: MethodResult[]
  combined_estimate: number | null
  percentiles: PercentileRange
  assumptions: string[]
  patent_strength_score: number | null
  strength_score_rubric: string
}

export interface NegotiationBrief extends AIOutputMetadata {
  assessment_id: string
  royalty_base?: string | null
  opening_offer_rate: number | null
  target_low_rate: number | null
  target_high_rate: number | null
  scenario_analysis: string[]
  negotiation_points: string[]
  missing_inputs: string[]
}

export interface StepStatus {
  name: string
  state: StepState
  started_at?: string | null
  completed_at?: string | null
  error?: string | null
}

export interface AssessmentStatus {
  assessment_id: string
  state: AssessmentState
  steps: StepStatus[]
  human_review_pending: boolean
  updated_at: string
}

export interface ReportSection {
  title: string
  summary: string
  evidence: string[]
  confidence: number
  needs_human_review: boolean
}

export interface AssessmentReport {
  assessment_id: string
  patent_overview: ReportSection
  patent_intelligence: ReportSection
  competitor_landscape: ReportSection
  claim_charts: ReportSection
  ip_valuation: ReportSection
  patent_strength: ReportSection
  licensing_strategy: ReportSection
  negotiation_strategy: ReportSection
  recommendations: ReportSection
}

export interface AssessmentResults {
  patent_profile: PatentProfile | null
  competitors: CompetitorTarget[]
  claim_charts: ClaimChart[]
  valuation: ValuationResult | null
  negotiation: NegotiationBrief | null
  report: AssessmentReport | null
  errors: string[]
  human_review_corrections: Array<Record<string, unknown>>
}

export interface AssessmentCreated {
  assessment_id: string
  state: AssessmentState
}

export interface UploadResult {
  document_id: string
  filename: string
  size_bytes: number
}

export interface ReviewCorrection {
  step: string
  correction: Record<string, unknown>
  reviewer_note?: string | null
}
