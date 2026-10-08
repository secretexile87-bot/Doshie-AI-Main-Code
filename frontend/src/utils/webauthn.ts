/**
 * WebAuthn Biometric & Passkey Authentication Utility for Doshie
 * Supports Fingerprint, Touch ID, Face ID, Windows Hello, and Android Biometrics
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

export async function isBiometricsSupported(): Promise<boolean> {
  if (typeof window === 'undefined') return false
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
  if (/Android/i.test(ua)) {
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
    if (err.name === 'NotAllowedError') {
      return { ok: false, error: 'Biometric prompt was cancelled or timed out.' }
    }
    return { ok: false, error: err.message || 'Biometric enrollment failed.' }
  }
}

export async function authenticateWithBiometrics(
  profile: string,
  mfaToken?: string
): Promise<{ ok: boolean; profile?: string; unlocked?: boolean; error?: string }> {
  try {
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
    if (err.name === 'NotAllowedError') {
      return { ok: false, error: 'Biometric prompt was cancelled.' }
    }
    return { ok: false, error: err.message || 'Biometric verification failed.' }
  }
}
