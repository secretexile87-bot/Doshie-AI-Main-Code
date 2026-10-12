/**
 * WebAuthn & Native Biometric Authentication Utility for Doshie
 * Supports Fingerprint, Face Unlock, Touch ID, Face ID, Windows Hello, and Android Biometrics
 */

export function bufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

export function base64UrlToBuffer(base64url: string): ArrayBuffer {
  let base64 = base64url.replace(/-/g, '+').replace(/_/g, '/')
  const pad = base64.length % 4
  if (pad) {
    base64 += '='.repeat(4 - pad)
  }
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

export function getNativeBiometricPlugin(): any {
  if (typeof window === 'undefined') return null
  const cap = (window as any).Capacitor
  return cap?.Plugins?.DiYoshiBiometric || null
}

export function isNativePlatform(): boolean {
  if (typeof window === 'undefined') return false
  const cap = (window as any).Capacitor
  return Boolean(
    cap?.isNativePlatform?.() ||
    (cap && typeof cap.getPlatform === 'function' && cap.getPlatform() !== 'web') ||
    cap?.Plugins?.DiYoshiBiometric
  )
}

export async function isBiometricsSupported(): Promise<boolean> {
  if (typeof window === 'undefined') return false

  // Check native Android / Capacitor biometric plugin first
  const nativePlugin = getNativeBiometricPlugin()
  if (nativePlugin && typeof nativePlugin.isAvailable === 'function') {
    try {
      const res = await nativePlugin.isAvailable()
      if (res && (res.isAvailable || res.hasHardware)) {
        return true
      }
    } catch (e) {
      console.warn('Native biometric check error:', e)
    }
  }

  // Fallback to standard WebAuthn API in browser
  if (!window.PublicKeyCredential) return false
  try {
    if (typeof PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable === 'function') {
      const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
      return !!available
    }
    return true
  } catch {
    return false
  }
}

export function getDeviceLabel(): string {
  const ua = navigator.userAgent
  let device = 'Biometric Passkey'
  if (isNativePlatform() || /Android/i.test(ua)) {
    device = 'Android Biometrics'
  } else if (/iPhone|iPad|iPod/i.test(ua)) {
    device = 'Apple Touch/Face ID'
  } else if (/Macintosh/i.test(ua)) {
    device = 'Mac Touch ID'
  } else if (/Windows/i.test(ua)) {
    device = 'Windows Hello'
  } else if (/Linux/i.test(ua)) {
    device = 'Linux Biometric Key'
  }
  return device
}

export async function enrollBiometricPasskey(
  profile: string,
  deviceName?: string
): Promise<{ ok: boolean; message?: string; error?: string }> {
  try {
    const nativePlugin = getNativeBiometricPlugin()
    if (nativePlugin && typeof nativePlugin.authenticate === 'function') {
      // 1. Get registration challenge
      let challenge = ''
      try {
        const chRes = await fetch('/profile-lock/biometrics/native-challenge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile, type: 'register' }),
        })
        if (chRes.ok) {
          const chData = await chRes.json()
          challenge = chData.challenge || ''
        }
      } catch (err) {
        console.warn('Could not fetch registration challenge:', err)
      }

      // 2. Launch native Android BiometricPrompt
      const authRes = await nativePlugin.authenticate({
        title: 'Enroll Biometric Passkey',
        subtitle: 'Touch the fingerprint sensor or glance at camera',
        description: `Secure access for profile ${profile}`,
      })

      if (!authRes || (!authRes.success && !authRes.verified)) {
        return { ok: false, error: 'Biometric verification was not recognized.' }
      }

      // 3. Generate or retrieve stable device key for this profile
      const storageKey = `diyoshi_native_bio_${profile.toLowerCase()}`
      let credentialId = localStorage.getItem(storageKey)
      if (!credentialId) {
        credentialId = `android-bio-${Math.random().toString(36).substring(2, 10)}-${Date.now().toString(36)}`
        localStorage.setItem(storageKey, credentialId)
      }
      localStorage.setItem('diyoshi_native_bio_active', credentialId)

      // 4. Register with backend
      const name = deviceName || getDeviceLabel()
      const regRes = await fetch('/profile-lock/biometrics/native-register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile,
          credential_id: credentialId,
          name,
          challenge,
        }),
      })

      const regData = await regRes.json()
      if (!regRes.ok || !regData.ok) {
        return { ok: false, error: regData.error || 'Failed to register native biometric credential.' }
      }

      return {
        ok: true,
        message: regData.message || 'Android biometrics enrolled successfully!',
      }
    }

    if (!window.PublicKeyCredential) {
      return { ok: false, error: 'WebAuthn biometrics are not supported on this browser.' }
    }

    const optionsRes = await fetch('/profile-lock/webauthn/register-options', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile }),
    })
    const optionsData = await optionsRes.json()
    if (!optionsRes.ok || !optionsData.ok) {
      return { ok: false, error: optionsData.error || 'Failed to initialize biometric enrollment.' }
    }

    const challengeBuffer = base64UrlToBuffer(optionsData.challenge)
    const userIdBuffer = base64UrlToBuffer(optionsData.user.id)

    const publicKeyCredentialCreationOptions: CredentialCreationOptions = {
      publicKey: {
        challenge: challengeBuffer,
        rp: {
          name: optionsData.rp.name || 'Doshie AI Assistant',
          id: optionsData.rp.id || undefined,
        },
        user: {
          id: userIdBuffer,
          name: optionsData.user.name,
          displayName: optionsData.user.displayName,
        },
        pubKeyCredParams: [
          { alg: -7, type: 'public-key' },
          { alg: -257, type: 'public-key' },
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'preferred',
          requireResidentKey: false,
        },
        timeout: 60000,
        attestation: 'none',
      },
    }

    const credential = (await navigator.credentials.create(
      publicKeyCredentialCreationOptions
    )) as PublicKeyCredential

    if (!credential) {
      return { ok: false, error: 'Biometric enrollment was cancelled.' }
    }

    const rawResponse = credential.response as AuthenticatorAttestationResponse
    const payload = {
      profile,
      name: deviceName || getDeviceLabel(),
      credential: {
        id: credential.id,
        rawId: bufferToBase64Url(credential.rawId),
        type: credential.type,
        response: {
          clientDataJSON: bufferToBase64Url(rawResponse.clientDataJSON),
          attestationObject: bufferToBase64Url(rawResponse.attestationObject),
        },
      },
    }

    const verifyRes = await fetch('/profile-lock/webauthn/register-verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const verifyData = await verifyRes.json()
    if (!verifyRes.ok || !verifyData.ok) {
      return { ok: false, error: verifyData.error || 'Failed to verify biometric registration.' }
    }

    return { ok: true, message: verifyData.message || 'Biometric passkey enrolled successfully!' }
  } catch (err: any) {
    if (
      err.code === 'USER_CANCELED' ||
      err.message?.toLowerCase().includes('cancel') ||
      err.name === 'NotAllowedError'
    ) {
      return { ok: false, error: 'Biometric prompt was cancelled.' }
    }
    return { ok: false, error: err.message || 'Biometric enrollment failed.' }
  }
}

export async function authenticateWithBiometrics(
  profile: string,
  mfaToken?: string
): Promise<{ ok: boolean; profile?: string; unlocked?: boolean; error?: string }> {
  try {
    const nativePlugin = getNativeBiometricPlugin()
    if (nativePlugin && typeof nativePlugin.authenticate === 'function') {
      // 1. Get login challenge
      let challenge = ''
      try {
        const chRes = await fetch('/profile-lock/biometrics/native-challenge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile, type: 'login' }),
        })
        if (chRes.ok) {
          const chData = await chRes.json()
          challenge = chData.challenge || ''
        }
      } catch (err) {
        console.warn('Could not fetch login challenge:', err)
      }

      // 2. Launch native Android BiometricPrompt
      const authRes = await nativePlugin.authenticate({
        title: 'Unlock Doshie',
        subtitle: 'Touch the fingerprint sensor or glance at camera',
        description: `Biometric quick unlock for ${profile}`,
      })

      if (!authRes || (!authRes.success && !authRes.verified)) {
        return { ok: false, error: 'Biometric verification failed.' }
      }

      // 3. Retrieve stored credential ID
      const storageKey = `diyoshi_native_bio_${profile.toLowerCase()}`
      const credentialId =
        localStorage.getItem(storageKey) ||
        localStorage.getItem('diyoshi_native_bio_active') ||
        ''

      // 4. Verify with backend
      const verifyRes = await fetch('/profile-lock/biometrics/native-verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile,
          credential_id: credentialId,
          challenge,
          mfa_token: mfaToken,
        }),
      })

      const verifyData = await verifyRes.json()
      if (!verifyRes.ok || !verifyData.ok) {
        return { ok: false, error: verifyData.error || 'Biometric verification failed.' }
      }

      return {
        ok: true,
        profile: verifyData.profile || profile,
        unlocked: true,
      }
    }

    if (!window.PublicKeyCredential) {
      return { ok: false, error: 'WebAuthn biometrics are not supported on this browser.' }
    }

    const optionsRes = await fetch('/profile-lock/webauthn/login-options', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile }),
    })
    const optionsData = await optionsRes.json()
    if (!optionsRes.ok || !optionsData.ok) {
      return { ok: false, error: optionsData.error || 'No biometrics found for this profile.' }
    }

    const challengeBuffer = base64UrlToBuffer(optionsData.challenge)
    const allowCredentials = (optionsData.allowCredentials || []).map((c: any) => ({
      id: base64UrlToBuffer(c.id),
      type: 'public-key',
      transports: c.transports || ['internal'],
    }))

    const requestOptions: CredentialRequestOptions = {
      publicKey: {
        challenge: challengeBuffer,
        timeout: 60000,
        userVerification: 'preferred',
        rpId: optionsData.rpId || undefined,
        allowCredentials: allowCredentials.length > 0 ? allowCredentials : undefined,
      },
    }

    const assertion = (await navigator.credentials.get(requestOptions)) as PublicKeyCredential

    if (!assertion) {
      return { ok: false, error: 'Biometric verification was cancelled.' }
    }

    const rawResponse = assertion.response as AuthenticatorAssertionResponse
    const payload = {
      profile,
      mfa_token: mfaToken,
      credential: {
        id: assertion.id,
        rawId: bufferToBase64Url(assertion.rawId),
        type: assertion.type,
        response: {
          clientDataJSON: bufferToBase64Url(rawResponse.clientDataJSON),
          authenticatorData: bufferToBase64Url(rawResponse.authenticatorData),
          signature: bufferToBase64Url(rawResponse.signature),
          userHandle: rawResponse.userHandle ? bufferToBase64Url(rawResponse.userHandle) : null,
        },
      },
    }

    const verifyRes = await fetch('/profile-lock/webauthn/login-verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const verifyData = await verifyRes.json()
    if (!verifyRes.ok || !verifyData.ok) {
      return { ok: false, error: verifyData.error || 'Biometric verification failed.' }
    }

    return {
      ok: true,
      profile: verifyData.profile || profile,
      unlocked: true,
    }
  } catch (err: any) {
    if (
      err.code === 'USER_CANCELED' ||
      err.message?.toLowerCase().includes('cancel') ||
      err.name === 'NotAllowedError'
    ) {
      return { ok: false, error: 'Biometric prompt was cancelled.' }
    }
    return { ok: false, error: err.message || 'Biometric verification failed.' }
  }
}
