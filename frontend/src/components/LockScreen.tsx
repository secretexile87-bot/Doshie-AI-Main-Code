import React, { useState, useEffect, useMemo } from 'react'
import {
  Unlock,
  Shield,
  Key,
  Users,
  Cpu,
  User,
  Eye,
  EyeOff,
  Mail,
  Phone,
  ArrowLeft,
  CheckCircle2,
  X,
  AlertCircle,
  Lock,
  RefreshCw,
  Fingerprint,
} from 'lucide-react'
import type { GuiCustomization, Profile } from '../types'
import { isBiometricsSupported, authenticateWithBiometrics } from '../utils/webauthn'
import { getSeasonalInfo } from '../utils/seasonal'

interface LockScreenProps {
  isLocked: boolean
  onUnlock: (profileName: string) => void
  activeProfile: string
  availableProfiles: Profile[]
  customization: GuiCustomization
}

export const LockScreen: React.FC<LockScreenProps> = ({
  isLocked,
  onUnlock,
  activeProfile,
  availableProfiles,
  customization,
}) => {
  const seasonal = useMemo(() => getSeasonalInfo(), [])
  const [timeStr, setTimeStr] = useState('')
  const [dateStr, setDateStr] = useState('')
  const [selectedProfile, setSelectedProfile] = useState(activeProfile || 'Hermes')
  const [credential, setCredential] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [biometricsAvailable, setBiometricsAvailable] = useState(false)
  const [profileHasBiometrics, setProfileHasBiometrics] = useState(false)
  const [isBiometricAuthenticating, setIsBiometricAuthenticating] = useState(false)
  const [pendingMfaToken, setPendingMfaToken] = useState<string | null>(null)
  const [mfaRequired, setMfaRequired] = useState(false)
  // Reset Password / PIN State
  const [showResetModal, setShowResetModal] = useState(false)
  const [resetStep, setResetStep] = useState<'request' | 'verify' | 'reset' | 'success'>('request')
  const [resetMethod, setResetMethod] = useState<'email' | 'sms'>('email')
  const [resetProfile, setResetProfile] = useState(selectedProfile || 'Hermes')
  const [resetDestination, setResetDestination] = useState('')
  const [resetCode, setResetCode] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newAuthType, setNewAuthType] = useState<'pin' | 'password'>('pin')
  const [newCredential, setNewCredential] = useState('')
  const [confirmCredential, setConfirmCredential] = useState('')
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)
  const [resetError, setResetError] = useState('')
  const [resetSuccessMsg, setResetSuccessMsg] = useState('')
  const [devCode, setDevCode] = useState<string | null>(null)

  const openResetModal = () => {
    setResetProfile(selectedProfile.trim() || 'Hermes')
    setResetStep('request')
    setResetError('')
    setResetSuccessMsg('')
    setResetCode('')
    setResetToken('')
    setNewCredential('')
    setConfirmCredential('')
    setDevCode(null)
    setShowResetModal(true)
  }

  const handleRequestResetCode = async (e: React.FormEvent) => {
    e.preventDefault()
    const target = resetProfile.trim() || 'Hermes'
    const dest = resetDestination.trim()
    if (!dest) {
      setResetError(`Please provide your ${resetMethod === 'email' ? 'email address' : 'phone number'}.`)
      return
    }

    setResetLoading(true)
    setResetError('')
    setResetSuccessMsg('')
    setDevCode(null)

    try {
      const res = await fetch('/recovery/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: target,
          method: resetMethod,
          email: resetMethod === 'email' ? dest : undefined,
          phone: resetMethod === 'sms' ? dest : undefined,
          destination: dest,
        }),
      })
      const data = await res.json()
      if (res.ok && data.ok) {
        setResetSuccessMsg(data.message || `Verification code sent to ${data.destination || dest}.`)
        if (data.dev_code) {
          setDevCode(data.dev_code)
        }
        setResetStep('verify')
      } else {
        setResetError(data.error || 'Failed to send recovery code. Please verify the contact details.')
      }
    } catch {
      setResetError('Unable to connect to recovery server. Please try again.')
    } finally {
      setResetLoading(false)
    }
  }

  const handleVerifyResetCode = async (e: React.FormEvent) => {
    e.preventDefault()
    const code = resetCode.trim()
    if (!code || code.length < 6) {
      setResetError('Please enter the 6-digit verification code.')
      return
    }

    setResetLoading(true)
    setResetError('')

    try {
      const res = await fetch('/recovery/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: resetProfile.trim() || 'Hermes',
          code,
        }),
      })
      const data = await res.json()
      if (res.ok && data.ok && data.reset_token) {
        setResetToken(data.reset_token)
        setResetError('')
        setResetSuccessMsg('Code verified! Set your new PIN or password.')
        setResetStep('reset')
      } else {
        setResetError(data.error || 'Invalid or expired verification code.')
      }
    } catch {
      setResetError('Unable to verify recovery code. Please try again.')
    } finally {
      setResetLoading(false)
    }
  }

  const handleCompleteReset = async (e: React.FormEvent) => {
    e.preventDefault()
    const cred = newCredential.trim()
    const confirm = confirmCredential.trim()

    if (!cred) {
      setResetError('Please enter a new PIN or password.')
      return
    }
    if (newAuthType === 'pin' && (!/^\d+$/.test(cred) || cred.length < 3 || cred.length > 16)) {
      setResetError('PIN must be 3-16 digits.')
      return
    }
    if (newAuthType === 'password' && cred.length < 3) {
      setResetError('Password must be at least 3 characters.')
      return
    }
    if (cred !== confirm) {
      setResetError('Passwords or PINs do not match.')
      return
    }

    setResetLoading(true)
    setResetError('')

    try {
      const target = resetProfile.trim() || 'Hermes'
      const res = await fetch('/recovery/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: target,
          auth_type: newAuthType,
          credential: cred,
          reset_token: resetToken,
        }),
      })
      const data = await res.json()
      if (res.ok && data.ok) {
        setResetSuccessMsg(`Security updated! You can now unlock as ${target}.`)
        setResetStep('success')
        setTimeout(() => {
          setShowResetModal(false)
          onUnlock(target)
        }, 1500)
      } else {
        setResetError(data.error || 'Failed to update credentials. Session may have expired.')
      }
    } catch {
      setResetError('Network error. Unable to complete password reset.')
    } finally {
      setResetLoading(false)
    }
  }

  // Update real-time clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      const is24h = customization.lockScreenClockFormat === '24h'
      setTimeStr(
        now.toLocaleTimeString([], {
          hour: is24h ? '2-digit' : 'numeric',
          minute: '2-digit',
          second: '2-digit',
          hour12: !is24h,
        })
      )
      setDateStr(
        now.toLocaleDateString([], {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
          year: 'numeric',
        })
      )
    }

    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [customization.lockScreenClockFormat])

  useEffect(() => {
    if (activeProfile) {
      setSelectedProfile(activeProfile)
    }
  }, [activeProfile])

  useEffect(() => {
    let active = true
    const checkBio = async () => {
      const supported = await isBiometricsSupported()
      if (!active) return
      setBiometricsAvailable(supported)

      const target = selectedProfile.trim() || 'Hermes'
      const matched = availableProfiles.find(
        p => p.name.toLowerCase() === target.toLowerCase()
      )
      if (matched && matched.has_biometrics !== undefined) {
        setProfileHasBiometrics(!!matched.has_biometrics)
      } else {
        try {
          const res = await fetch(
            `/profile-lock/status?profile=${encodeURIComponent(target)}`
          )
          if (res.ok) {
            const data = await res.json()
            if (active) {
              setProfileHasBiometrics(!!data.has_biometrics)
            }
          }
        } catch {}
      }
    }
    checkBio()
    return () => {
      active = false
    }
  }, [selectedProfile, availableProfiles])

  const handleBiometricUnlock = async (mfaTokenOverride?: string) => {
    const targetProfile = selectedProfile.trim() || 'Hermes'
    const tokenToUse = mfaTokenOverride || pendingMfaToken || undefined
    setIsBiometricAuthenticating(true)
    setErrorMsg('')

    try {
      const res = await authenticateWithBiometrics(targetProfile, tokenToUse)
      if (res.ok && res.unlocked) {
        setCredential('')
        setPendingMfaToken(null)
        setMfaRequired(false)
        onUnlock(targetProfile)
      } else {
        setErrorMsg(res.error || 'Biometric verification failed. You can unlock with PIN or password.')
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Biometric authentication was cancelled or unavailable.')
    } finally {
      setIsBiometricAuthenticating(false)
    }
  }

  const handleAttemptUnlock = async (e: React.FormEvent) => {
    e.preventDefault()
    const targetProfile = selectedProfile.trim() || 'Hermes'
    const trimmedCredential = credential.trim()
    if (!trimmedCredential) {
      setErrorMsg('PIN or password is required to unlock.')
      return
    }

    setIsSubmitting(true)
    setErrorMsg('')

    try {
      const res = await fetch('/family-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: targetProfile,
          credential: trimmedCredential,
        }),
      })

      const data = await res.json()
      if (data.ok) {
        if (data.mfa_required && data.mfa_token) {
          setPendingMfaToken(data.mfa_token)
          setMfaRequired(true)
          setIsSubmitting(false)
          // Automatically trigger biometric passkey prompt for 2FA
          handleBiometricUnlock(data.mfa_token)
          return
        }
        setCredential('')
        setPendingMfaToken(null)
        setMfaRequired(false)
        onUnlock(targetProfile)
      } else {
        setErrorMsg(data.error || 'Incorrect PIN or password')
      }
    } catch {
      setErrorMsg('Unable to verify credentials. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Determine wallpaper style class / styles
  const isSeasonal = customization.lockScreenWallpaper === 'seasonal' || customization.theme === 'seasonal' || customization.seasonalThemeEnabled
  const wallpaper = customization.lockScreenWallpaper || (isSeasonal ? 'seasonal' : 'matrix')

  let bgClass = 'bg-[#040d07]'
  if (isSeasonal || wallpaper === 'seasonal') {
    if (seasonal.currentSeason === 'autumn') bgClass = 'bg-[#0f0803]'
    else if (seasonal.currentSeason === 'winter') bgClass = 'bg-[#040912]'
    else if (seasonal.currentSeason === 'spring') bgClass = 'bg-[#040d07]'
    else if (seasonal.currentSeason === 'summer') bgClass = 'bg-[#030d14]'
  } else if (wallpaper === 'cyberpunk') {
    bgClass = 'bg-[#080412]'
  } else if (wallpaper === 'oled') {
    bgClass = 'bg-black'
  } else if (wallpaper === 'aurora') {
    bgClass = 'bg-[#051119]'
  } else if (wallpaper === 'stars') {
    bgClass = 'bg-[#05070f]'
  }

  if (!isLocked) return null

  return (
    <div
      className={`fixed inset-0 z-[100] flex flex-col items-center justify-between p-4 sm:p-8 select-none text-white transition-all duration-500 overflow-y-auto ${bgClass}`}
    >
      {/* Dynamic Ambient Background Elements */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {(isSeasonal || wallpaper === 'seasonal') && (
          <>
            {seasonal.currentSeason === 'autumn' && (
              <>
                <div className="absolute top-1/4 left-1/3 -translate-x-1/2 w-[600px] h-[600px] bg-amber-600/15 rounded-full blur-[140px]" />
                <div className="absolute bottom-10 right-1/4 w-[500px] h-[450px] bg-orange-500/15 rounded-full blur-[130px]" />
                <div className="absolute inset-0 opacity-[0.04] bg-[radial-gradient(#f97316_1px,transparent_1px)] [background-size:28px_28px]" />
              </>
            )}
            {seasonal.currentSeason === 'winter' && (
              <>
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-sky-500/15 rounded-full blur-[140px]" />
                <div className="absolute bottom-10 right-1/4 w-[450px] h-[450px] bg-blue-600/15 rounded-full blur-[120px]" />
                <div className="absolute inset-0 opacity-[0.05] bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:28px_28px]" />
              </>
            )}
            {seasonal.currentSeason === 'spring' && (
              <>
                <div className="absolute top-1/4 left-1/4 w-[550px] h-[550px] bg-emerald-500/15 rounded-full blur-[140px]" />
                <div className="absolute bottom-1/4 right-1/4 w-[450px] h-[450px] bg-teal-500/15 rounded-full blur-[130px]" />
                <div className="absolute inset-0 opacity-[0.04] bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:28px_28px]" />
              </>
            )}
            {seasonal.currentSeason === 'summer' && (
              <>
                <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-cyan-500/15 rounded-full blur-[140px]" />
                <div className="absolute bottom-10 right-1/4 w-[450px] h-[450px] bg-amber-500/15 rounded-full blur-[120px]" />
                <div className="absolute inset-0 opacity-[0.04] bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:28px_28px]" />
              </>
            )}
          </>
        )}
        {wallpaper === 'matrix' && !isSeasonal && (
          <>
            <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-emerald-500/10 rounded-full blur-[140px]" />
            <div className="absolute -bottom-20 left-1/3 w-[500px] h-[400px] bg-teal-500/10 rounded-full blur-[120px]" />
            <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#10b981_1px,transparent_1px)] [background-size:24px_24px]" />
          </>
        )}
        {wallpaper === 'cyberpunk' && !isSeasonal && (
          <>
            <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-fuchsia-600/15 rounded-full blur-[140px]" />
            <div className="absolute bottom-10 right-1/4 w-[450px] h-[450px] bg-cyan-500/15 rounded-full blur-[120px]" />
          </>
        )}
        {wallpaper === 'aurora' && !isSeasonal && (
          <>
            <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-teal-500/15 rounded-full blur-[140px]" />
            <div className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] bg-indigo-500/15 rounded-full blur-[140px]" />
          </>
        )}
        {wallpaper === 'stars' && !isSeasonal && (
          <>
            <div className="absolute inset-0 opacity-[0.08] bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:32px_32px]" />
            <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[160px]" />
          </>
        )}
      </div>

      {/* Top Header: Security Badge, Seasonal Countdown Badge & Host */}
      <div className="relative z-10 w-full max-w-4xl flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md text-xs text-[var(--accent-light)] font-medium shadow-lg">
          <Shield className="w-4 h-4 text-[var(--accent)]" />
          <span>{customization.lockScreenCustomNote || 'Secure Workstation • RTX 5070 Local Engine'}</span>
        </div>

        {/* Small time till next season on top */}
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md text-xs text-[var(--accent-light)] font-medium shadow-lg">
          <span className="text-sm">{seasonal.icon}</span>
          <span className="text-white font-semibold">{seasonal.seasonName}</span>
          <span className="text-white/40">•</span>
          <span className="font-mono text-[11px] text-[var(--accent-light)]">{seasonal.countdownText}</span>
        </div>

        <div className="flex items-center gap-2 text-xs text-gray-400">
          <Cpu className="w-3.5 h-3.5 text-[var(--accent-light)]" />
          <span className="font-mono">Hermes Host</span>
        </div>
      </div>

      {/* Center Main: Digital Clock, Custom Title & Unlock Form */}
      <div className="relative z-10 my-auto flex flex-col items-center justify-center w-full max-w-md text-center py-4">
        {/* Large Digital Clock */}
        <div className="space-y-1 mb-5">
          <h1 className="text-5xl sm:text-6xl font-light tracking-tight text-white font-mono drop-shadow-md">
            {timeStr || '12:00:00'}
          </h1>
          <p className="text-xs sm:text-sm text-[var(--accent-light)] font-medium tracking-wide">
            {dateStr}
          </p>
        </div>

        {/* Custom Lock Screen Title & Subtitle */}
        <div className="mb-6 space-y-1.5">
          <div className="inline-flex items-center justify-center gap-2 text-2xl sm:text-3xl font-bold tracking-tight text-white">
            <span>{customization.assistantEmoji || '🦖'}</span>
            <span>{customization.lockScreenTitle || `${customization.assistantName || 'Doshie'} Workstation`}</span>
          </div>
          <p className="text-xs sm:text-sm text-gray-300/80 max-w-sm mx-auto leading-relaxed">
            {customization.lockScreenSubtitle || 'Private local AI environment secured. Type or select profile to unlock.'}
          </p>
        </div>

        {/* Profile Card Selector & Unlock Box */}
        <div className="w-full bg-white/[0.04] border border-white/10 backdrop-blur-xl p-4 sm:p-6 rounded-3xl shadow-2xl shadow-black/80 space-y-4">
          {/* Quick Profile Chips */}
          {customization.lockScreenShowQuickProfiles !== false && availableProfiles.length > 0 && (
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-400 mb-2 text-left flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-[var(--accent-light)]" />
                <span>Quick Profile Selection</span>
              </div>
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {availableProfiles.map(p => {
                  const isSel = selectedProfile.toLowerCase() === p.name.toLowerCase()
                  return (
                    <button
                      key={p.name}
                      type="button"
                      onClick={() => {
                        setSelectedProfile(p.name)
                        setCredential('')
                        setErrorMsg('')
                      }}
                      className={`flex-1 min-w-[85px] p-2.5 rounded-2xl border text-left transition-all cursor-pointer flex flex-col items-center justify-center gap-1 ${
                        isSel
                          ? 'bg-[var(--accent)]/30 border-[var(--accent)] text-white shadow-lg ring-1 ring-[var(--accent)]/40'
                          : 'bg-black/30 border-white/10 hover:bg-white/5 text-gray-300'
                      }`}
                    >
                      <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center font-bold text-xs text-white shadow-sm">
                        {p.name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-xs font-semibold truncate max-w-[75px]">{p.name}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Datalist for Profile suggestions */}
          <datalist id="lockscreen-profile-list">
            {availableProfiles.map(p => (
              <option key={p.name} value={p.name} />
            ))}
          </datalist>

          {/* MFA 2FA Biometric Prompt */}
          {mfaRequired ? (
            <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-left space-y-3 animate-in fade-in duration-200">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
                  <Fingerprint className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="font-bold text-xs sm:text-sm text-white">Two-Factor Authentication</h4>
                  <p className="text-[10px] text-amber-300/80">Step 1 verified • Complete sign-in with biometrics</p>
                </div>
              </div>

              {errorMsg && (
                <p className="text-xs text-rose-400 font-medium">{errorMsg}</p>
              )}

              <button
                type="button"
                onClick={() => handleBiometricUnlock()}
                disabled={isBiometricAuthenticating}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 active:scale-98 text-black text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition shadow-lg shadow-amber-950/40 cursor-pointer disabled:opacity-50"
              >
                <Fingerprint className="w-4 h-4 animate-pulse" />
                <span>{isBiometricAuthenticating ? 'Scanning Passkey / Biometrics...' : 'Verify Biometric (Touch Sensor)'}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setMfaRequired(false)
                  setPendingMfaToken(null)
                  setErrorMsg('')
                }}
                className="w-full py-1.5 text-center text-[11px] text-gray-400 hover:text-white underline cursor-pointer"
              >
                Back to PIN / Password
              </button>
            </div>
          ) : (
            <>
              {/* Biometric Quick Unlock (When Available & Profile Enrolled) */}
              {profileHasBiometrics && biometricsAvailable && (
                <div className="mb-4 space-y-2">
                  <button
                    type="button"
                    onClick={() => handleBiometricUnlock()}
                    disabled={isBiometricAuthenticating}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500 hover:from-emerald-500 hover:to-teal-500 active:scale-98 text-white text-xs sm:text-sm font-semibold flex items-center justify-center gap-2.5 transition duration-150 shadow-lg shadow-emerald-950/50 cursor-pointer disabled:opacity-50 border border-emerald-400/40"
                  >
                    <Fingerprint className="w-4 h-4 text-emerald-200 animate-pulse" />
                    <span>
                      {isBiometricAuthenticating
                        ? 'Scanning Passkey...'
                        : `Unlock with Biometrics (${selectedProfile || 'Profile'})`}
                    </span>
                  </button>

                  <div className="flex items-center my-2 gap-2 text-gray-500 text-[11px]">
                    <div className="flex-1 h-px bg-white/10" />
                    <span>or use PIN / Password</span>
                    <div className="flex-1 h-px bg-white/10" />
                  </div>
                </div>
              )}

              {/* Unlock Form */}
              <form onSubmit={handleAttemptUnlock} className="space-y-3">
                {/* Editable Profile Name Field */}
                <div className="text-left space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-[var(--accent-light)] flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-[var(--accent)]" />
                    <span>Profile Name</span>
                  </label>
                  <input
                    type="text"
                    value={selectedProfile}
                    list="lockscreen-profile-list"
                    onChange={e => {
                      setSelectedProfile(e.target.value)
                      setErrorMsg('')
                    }}
                    placeholder="Type profile name (e.g. Hermes)"
                    autoCapitalize="words"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/50 border border-white/15 focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/20 focus:outline-none text-xs sm:text-sm text-white placeholder-gray-500 font-medium"
                    required
                  />
                </div>

                {/* PIN or Password Field */}
                <div className="text-left space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-[var(--accent-light)] flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Key className="w-3.5 h-3.5 text-[var(--accent)]" />
                      <span>PIN or Password</span>
                    </span>
                    <span className="text-[10px] text-gray-400 font-normal lowercase">(required)</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={credential}
                      onChange={e => {
                        setCredential(e.target.value)
                        setErrorMsg('')
                      }}
                      placeholder={`Enter PIN or password for ${selectedProfile || 'Profile'}`}
                      className="w-full pl-3.5 pr-10 py-2.5 rounded-xl bg-black/50 border border-white/15 focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/20 focus:outline-none text-xs sm:text-sm text-white placeholder-gray-500"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-[var(--accent-light)] transition-colors cursor-pointer"
                      title={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {errorMsg && (
                  <p className="text-xs text-rose-400 font-medium animate-pulse">{errorMsg}</p>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] hover:opacity-90 active:scale-98 text-white text-xs sm:text-sm font-semibold flex items-center justify-center gap-2 transition duration-150 shadow-lg shadow-black/50 cursor-pointer disabled:opacity-50 mt-1"
                >
                  <Unlock className="w-4 h-4" />
                  <span>{isSubmitting ? 'Logging in...' : `Log In as ${selectedProfile || 'Profile'}`}</span>
                </button>

                {/* Forgot PIN / Password Trigger */}
                <div className="pt-2 text-center">
                  <button
                    type="button"
                    onClick={openResetModal}
                    className="text-[11px] text-[var(--accent-light)] hover:text-white underline underline-offset-4 opacity-80 hover:opacity-100 transition-opacity cursor-pointer font-medium"
                  >
                    Forgot PIN or Password? Reset via Phone or Email
                  </button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>

      {/* Password / PIN Reset Modal */}
      {showResetModal && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="relative w-full max-w-md bg-[#0d1612] border border-white/15 rounded-3xl p-6 shadow-2xl shadow-black text-left text-white space-y-4">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-white/10">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-[var(--accent)]/20 border border-[var(--accent)]/40 flex items-center justify-center text-[var(--accent)]">
                  <Key className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-white">Reset PIN or Password</h3>
                  <p className="text-[10px] text-gray-400 font-mono">Secure verification via Email or Phone (SMS)</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowResetModal(false)}
                className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Step 1: Request Verification Code */}
            {resetStep === 'request' && (
              <form onSubmit={handleRequestResetCode} className="space-y-3.5">
                {/* Profile selection */}
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Account Profile</label>
                  <input
                    type="text"
                    value={resetProfile}
                    onChange={e => {
                      setResetProfile(e.target.value)
                      setResetError('')
                    }}
                    placeholder="Account name (e.g. Hermes)"
                    className="w-full px-3 py-2 rounded-xl bg-black/50 border border-white/15 focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white font-medium"
                    required
                  />
                </div>

                {/* Method Switcher Tabs */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Recovery Method</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setResetMethod('email')
                        setResetError('')
                      }}
                      className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                        resetMethod === 'email'
                          ? 'bg-[var(--accent)]/20 border-[var(--accent)] text-white shadow-sm ring-1 ring-[var(--accent)]/30'
                          : 'bg-black/30 border-white/10 text-gray-400 hover:bg-white/5'
                      }`}
                    >
                      <Mail className="w-3.5 h-3.5 text-[var(--accent)]" />
                      <span>Email Address</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setResetMethod('sms')
                        setResetError('')
                      }}
                      className={`py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                        resetMethod === 'sms'
                          ? 'bg-[var(--accent)]/20 border-[var(--accent)] text-white shadow-sm ring-1 ring-[var(--accent)]/30'
                          : 'bg-black/30 border-white/10 text-gray-400 hover:bg-white/5'
                      }`}
                    >
                      <Phone className="w-3.5 h-3.5 text-[var(--accent)]" />
                      <span>Phone / SMS</span>
                    </button>
                  </div>
                </div>

                {/* Destination input */}
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                    {resetMethod === 'email' ? 'Recovery Email Address' : 'Recovery Phone Number'}
                  </label>
                  <input
                    type={resetMethod === 'email' ? 'email' : 'tel'}
                    value={resetDestination}
                    onChange={e => {
                      setResetDestination(e.target.value)
                      setResetError('')
                    }}
                    placeholder={resetMethod === 'email' ? 'you@example.com' : '+15551234567'}
                    className="w-full px-3 py-2 rounded-xl bg-black/50 border border-white/15 focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white placeholder-gray-500"
                    required
                  />
                  <p className="text-[10px] text-gray-400">
                    {resetMethod === 'email'
                      ? 'We will send a 6-digit confirmation code to this email.'
                      : 'We will send a 6-digit SMS text code with international code.'}
                  </p>
                </div>

                {resetError && (
                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{resetError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={resetLoading}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] text-white text-xs font-semibold shadow-lg shadow-black/50 hover:opacity-90 active:scale-98 transition-all disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer mt-2"
                >
                  {resetLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Mail className="w-3.5 h-3.5" />}
                  <span>{resetLoading ? 'Sending Code...' : `Send 6-Digit Code via ${resetMethod.toUpperCase()}`}</span>
                </button>
              </form>
            )}

            {/* Step 2: Verify Code */}
            {resetStep === 'verify' && (
              <form onSubmit={handleVerifyResetCode} className="space-y-3.5">
                <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-200 text-xs space-y-1">
                  <div className="font-semibold flex items-center gap-1.5 text-emerald-300">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Verification Code Sent</span>
                  </div>
                  <p className="text-[11px] text-emerald-200/90">{resetSuccessMsg}</p>
                </div>

                {devCode && (
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs font-mono flex items-center justify-between">
                    <span>Local Workstation Code:</span>
                    <span className="text-sm font-bold tracking-widest text-amber-300">{devCode}</span>
                  </div>
                )}

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                    6-Digit Verification Code
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={resetCode}
                    onChange={e => {
                      setResetCode(e.target.value.replace(/\D/g, ''))
                      setResetError('')
                    }}
                    placeholder="123456"
                    className="w-full text-center tracking-[0.4em] font-mono text-lg py-2.5 rounded-xl bg-black/60 border border-white/20 focus:border-[var(--accent)] focus:outline-none text-white font-bold"
                    autoFocus
                    required
                  />
                </div>

                {resetError && (
                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{resetError}</span>
                  </div>
                )}

                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setResetStep('request')
                      setResetError('')
                    }}
                    className="px-3.5 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 text-xs text-gray-300 font-medium flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" />
                    <span>Back</span>
                  </button>
                  <button
                    type="submit"
                    disabled={resetLoading || resetCode.length < 6}
                    className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] text-white text-xs font-semibold shadow-lg hover:opacity-90 active:scale-98 transition-all disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {resetLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Key className="w-3.5 h-3.5" />}
                    <span>{resetLoading ? 'Verifying...' : 'Verify Code'}</span>
                  </button>
                </div>
              </form>
            )}

            {/* Step 3: Set New Password or PIN */}
            {resetStep === 'reset' && (
              <form onSubmit={handleCompleteReset} className="space-y-3.5">
                <div className="space-y-1.5">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Security Format</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setNewAuthType('pin')}
                      className={`py-1.5 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        newAuthType === 'pin'
                          ? 'bg-[var(--accent)]/20 border-[var(--accent)] text-white shadow-sm ring-1 ring-[var(--accent)]/30'
                          : 'bg-black/30 border-white/10 text-gray-400 hover:bg-white/5'
                      }`}
                    >
                      <Key className="w-3 h-3 text-[var(--accent)]" />
                      <span>PIN (Digits)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setNewAuthType('password')}
                      className={`py-1.5 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        newAuthType === 'password'
                          ? 'bg-[var(--accent)]/20 border-[var(--accent)] text-white shadow-sm ring-1 ring-[var(--accent)]/30'
                          : 'bg-black/30 border-white/10 text-gray-400 hover:bg-white/5'
                      }`}
                    >
                      <Lock className="w-3 h-3 text-[var(--accent)]" />
                      <span>Password (Text)</span>
                    </button>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                    New {newAuthType === 'pin' ? 'PIN Code' : 'Password'}
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={newCredential}
                      onChange={e => {
                        setNewCredential(e.target.value)
                        setResetError('')
                      }}
                      placeholder={`Enter new ${newAuthType === 'pin' ? 'PIN (e.g. 4-8 digits)' : 'password'}`}
                      className="w-full pl-3 pr-10 py-2 rounded-xl bg-black/50 border border-white/15 focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-white"
                    >
                      {showNewPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                    Confirm New {newAuthType === 'pin' ? 'PIN' : 'Password'}
                  </label>
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={confirmCredential}
                    onChange={e => {
                      setConfirmCredential(e.target.value)
                      setResetError('')
                    }}
                    placeholder={`Re-enter new ${newAuthType === 'pin' ? 'PIN' : 'password'}`}
                    className="w-full px-3 py-2 rounded-xl bg-black/50 border border-white/15 focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                    required
                  />
                </div>

                {resetError && (
                  <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>{resetError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={resetLoading}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] text-white text-xs font-semibold shadow-lg hover:opacity-90 active:scale-98 transition-all disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer mt-2"
                >
                  {resetLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  <span>{resetLoading ? 'Saving...' : 'Save & Unlock Workstation'}</span>
                </button>
              </form>
            )}

            {/* Step 4: Success state */}
            {resetStep === 'success' && (
              <div className="py-6 text-center space-y-2">
                <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mx-auto text-xl animate-bounce">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <h4 className="text-base font-bold text-white">PIN / Password Updated</h4>
                <p className="text-xs text-gray-300">{resetSuccessMsg}</p>
                <p className="text-[10px] text-emerald-400 font-mono">Unlocking workstation session...</p>
              </div>
            )}

          </div>
        </div>
      )}

      {/* Bottom Footer */}
      <div className="relative z-10 text-center text-xs text-gray-500 pb-2">
        Press <kbd className="px-1.5 py-0.5 rounded bg-white/10 border border-white/10 font-mono text-[10px] text-gray-300">Enter</kbd> to unlock • Antigravity 2.0 Secure Session
      </div>
    </div>
  )
}
