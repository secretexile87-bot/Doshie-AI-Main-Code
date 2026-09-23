import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Ensure mobile / Samsung Fold / Android edge-to-edge status bar and taskbar insets are respected
const updateSafeAreas = () => {
  const isAndroid = /android/i.test(navigator.userAgent)
  const isStandalone =
    window.matchMedia('(display-mode: standalone)').matches ||
    (window.navigator as any).standalone === true ||
    document.referrer.includes('android-app://')

  // Apply elevated safe padding in standalone PWA / Android modes to prevent status bar and taskbar overlaps
  if (isAndroid || isStandalone) {
    document.documentElement.style.setProperty(
      '--native-safe-top',
      'max(env(safe-area-inset-top, 0px), 40px)'
    )
    document.documentElement.style.setProperty(
      '--native-safe-bottom',
      'max(env(safe-area-inset-bottom, 0px), 24px)'
    )
  }
}

updateSafeAreas()
window.addEventListener('resize', updateSafeAreas)
window.addEventListener('orientationchange', updateSafeAreas)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
