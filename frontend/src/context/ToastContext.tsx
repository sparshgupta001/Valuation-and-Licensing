import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'

type ToastTone = 'error' | 'success' | 'info'
interface ToastEntry { id: number; message: string; tone: ToastTone }
interface ToastContextValue { notify: (message: string, tone?: ToastTone) => void }

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([])
  const notify = useCallback((message: string, tone: ToastTone = 'error') => {
    const id = Date.now() + Math.random()
    setToasts((current) => [...current, { id, message, tone }])
    window.setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 5200)
  }, [])
  const contextValue = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => {
          const Icon = toast.tone === 'error' ? AlertCircle : toast.tone === 'success' ? CheckCircle2 : Info
          return (
            <div key={toast.id} className={`toast toast-${toast.tone}`} role="status">
              <Icon size={18} />
              <span>{toast.message}</span>
              <button aria-label="Dismiss notification" onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}>
                <X size={16} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside ToastProvider')
  return context
}
