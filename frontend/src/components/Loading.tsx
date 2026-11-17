export function PageSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-4" aria-label="Loading">
      <div className="skeleton h-9 w-2/5" />
      <div className="skeleton h-4 w-3/5" />
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: rows }).map((_, index) => <div className="skeleton h-32" key={index} />)}
      </div>
    </div>
  )
}

export function InlineSpinner({ label = 'Working' }: { label?: string }) {
  return <span className="inline-flex items-center gap-2"><span className="spinner" aria-hidden="true" />{label}</span>
}
