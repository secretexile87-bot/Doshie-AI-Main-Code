import React, { useState, useRef, useEffect, useCallback } from 'react'
import {
  Camera,
  X,
  RotateCcw,
  Sparkles,
  Layers,
  Check,
  RefreshCw,
  Eye,
  AlertCircle,
  FlipHorizontal,
  Compass
} from 'lucide-react'

interface CameraCaptureModalProps {
  isOpen: boolean
  onClose: () => void
  onCapture: (files: File[], metadata?: { is4D: boolean; frameCount: number }) => void
}

type CameraMode = 'standard' | '4d_spatial'

interface CapturedFrame {
  dataUrl: string
  timestamp: number
  gyro?: { alpha: number | null; beta: number | null; gamma: number | null }
}

export const CameraCaptureModal: React.FC<CameraCaptureModalProps> = ({
  isOpen,
  onClose,
  onCapture,
}) => {
  const [mode, setMode] = useState<CameraMode>('standard')
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment')
  const [streamActive, setStreamActive] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [isCapturing4D, setIsCapturing4D] = useState(false)
  const [progress4D, setProgress4D] = useState({ current: 0, total: 4 })
  const [capturedSingle, setCapturedSingle] = useState<string | null>(null)
  const [captured4DFrames, setCaptured4DFrames] = useState<CapturedFrame[]>([])
  const [active4DIndex, setActive4DIndex] = useState(0)
  const [flash, setFlash] = useState(false)

  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const nativeFileInputRef = useRef<HTMLInputElement>(null)
  const currentOrientationRef = useRef<{ alpha: number | null; beta: number | null; gamma: number | null }>({
    alpha: null,
    beta: null,
    gamma: null,
  })

  // Start Camera Stream
  const startCamera = useCallback(async () => {
    setCameraError(null)
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError('Camera access is not supported in this browser. You can use native file upload below.')
      return
    }

    try {
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
        setStreamActive(true)
      }
    } catch (err: any) {
      console.warn('Camera stream error:', err)
      // Fallback try without facingMode constraints
      try {
        const fallbackStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        streamRef.current = fallbackStream
        if (videoRef.current) {
          videoRef.current.srcObject = fallbackStream
          await videoRef.current.play()
          setStreamActive(true)
        }
      } catch (fallbackErr: any) {
        setCameraError(
          fallbackErr.name === 'NotAllowedError' || fallbackErr.name === 'PermissionDeniedError'
            ? 'Camera permission denied. Please allow camera access in your browser settings or use the file picker.'
            : 'Unable to start camera. Please check your camera permissions.'
        )
        setStreamActive(false)
      }
    }
  }, [facingMode])

  // Stop Camera Stream
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setStreamActive(false)
  }, [])

  // Listen for device orientation (for 4D photo motion tracking)
  useEffect(() => {
    const handleOrientation = (e: DeviceOrientationEvent) => {
      currentOrientationRef.current = {
        alpha: e.alpha !== null ? Math.round(e.alpha) : null,
        beta: e.beta !== null ? Math.round(e.beta) : null,
        gamma: e.gamma !== null ? Math.round(e.gamma) : null,
      }
    }

    if (window.DeviceOrientationEvent) {
      window.addEventListener('deviceorientation', handleOrientation)
    }
    return () => {
      window.removeEventListener('deviceorientation', handleOrientation)
    }
  }, [])

  // Manage camera lifecycle with modal open/close
  useEffect(() => {
    if (isOpen) {
      setCapturedSingle(null)
      setCaptured4DFrames([])
      startCamera()
    } else {
      stopCamera()
    }
    return () => {
      stopCamera()
    }
  }, [isOpen, startCamera, stopCamera])

  // Flip Camera between Front / Back
  const handleFlipCamera = () => {
    setFacingMode(prev => (prev === 'environment' ? 'user' : 'environment'))
  }

  // Trigger Flash Animation
  const triggerFlash = () => {
    setFlash(true)
    setTimeout(() => setFlash(false), 150)
  }

  // Grab single canvas frame from video
  const grabFrame = (): string | null => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return null

    const width = video.videoWidth || 1280
    const height = video.videoHeight || 720
    canvas.width = width
    canvas.height = height

    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    // If using user-facing front camera, mirror image for natural photo feel
    if (facingMode === 'user') {
      ctx.translate(width, 0)
      ctx.scale(-1, 1)
    }
    ctx.drawImage(video, 0, 0, width, height)

    return canvas.toDataURL('image/jpeg', 0.92)
  }

  // Take Standard Photo
  const handleCaptureStandard = () => {
    triggerFlash()
    const frame = grabFrame()
    if (frame) {
      setCapturedSingle(frame)
    }
  }

  // Take 4D Spatial Photo Burst
  const handleCapture4D = async () => {
    if (isCapturing4D) return
    setIsCapturing4D(true)
    const totalFrames = 4
    const intervalMs = 400
    const frames: CapturedFrame[] = []

    setProgress4D({ current: 0, total: totalFrames })

    for (let i = 0; i < totalFrames; i++) {
      triggerFlash()
      const dataUrl = grabFrame()
      if (dataUrl) {
        frames.push({
          dataUrl,
          timestamp: Date.now(),
          gyro: { ...currentOrientationRef.current },
        })
      }
      setProgress4D({ current: i + 1, total: totalFrames })
      if (i < totalFrames - 1) {
        await new Promise(r => setTimeout(r, intervalMs))
      }
    }

    setIsCapturing4D(false)
    if (frames.length > 0) {
      setCaptured4DFrames(frames)
      setActive4DIndex(Math.floor(frames.length / 2))
    }
  }

  // Convert DataUrl to File helper
  const dataUrlToFile = (dataUrl: string, filename: string): File => {
    const arr = dataUrl.split(',')
    const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/jpeg'
    const bstr = atob(arr[1])
    let n = bstr.length
    const u8arr = new Uint8Array(n)
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n)
    }
    return new File([u8arr], filename, { type: mime })
  }

  // Confirm Standard Photo
  const handleConfirmSingle = () => {
    if (!capturedSingle) return
    const file = dataUrlToFile(capturedSingle, `camera_photo_${Date.now()}.jpg`)
    onCapture([file], { is4D: false, frameCount: 1 })
    onClose()
  }

  // Confirm 4D Spatial Photo
  const handleConfirm4D = () => {
    if (captured4DFrames.length === 0) return
    const timestamp = Date.now()
    const files = captured4DFrames.map((f, idx) =>
      dataUrlToFile(f.dataUrl, `4D_spatial_angle_${idx + 1}_of_${captured4DFrames.length}_${timestamp}.jpg`)
    )
    onCapture(files, { is4D: true, frameCount: captured4DFrames.length })
    onClose()
  }

  // Handle native fallback file input
  const handleNativeFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (fileList && fileList.length > 0) {
      const files = Array.from(fileList)
      onCapture(files, { is4D: false, frameCount: files.length })
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/85 backdrop-blur-xl animate-fadeIn select-none">
      <div className="relative w-full max-w-lg bg-[#0e1620] border border-white/10 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Flash Effect Overlay */}
        {flash && <div className="absolute inset-0 bg-white z-40 pointer-events-none animate-fadeOut duration-150" />}

        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 sm:px-5 py-3 border-b border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent-light)] flex items-center justify-center">
              <Camera className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
                <span>Doshie Camera & 4D Studio</span>
                {mode === '4d_spatial' && (
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    4D Mode
                  </span>
                )}
              </h2>
              <p className="text-[11px] text-neutral-400">
                {mode === 'standard' ? 'Instant photo capture for chat & vision' : 'Spatial parallax burst for 4D photo'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-xl text-neutral-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
            title="Close camera"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Mode Selector Tabs (Single Photo vs 4D Spatial Photo) */}
        {!capturedSingle && captured4DFrames.length === 0 && (
          <div className="flex items-center justify-center gap-2 p-2 bg-black/40 border-b border-white/5">
            <button
              type="button"
              onClick={() => setMode('standard')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                mode === 'standard'
                  ? 'bg-[var(--accent)] text-black shadow-md'
                  : 'text-neutral-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Standard Photo</span>
            </button>

            <button
              type="button"
              onClick={() => setMode('4d_spatial')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                mode === '4d_spatial'
                  ? 'bg-gradient-to-r from-purple-500 to-indigo-500 text-white shadow-md shadow-purple-900/40'
                  : 'text-neutral-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-200" />
              <span>4D Spatial Photo</span>
            </button>
          </div>
        )}

        {/* Viewfinder / Preview Area */}
        <div className="relative flex-1 min-h-[320px] max-h-[460px] bg-black overflow-hidden flex items-center justify-center">
          <canvas ref={canvasRef} className="hidden" />

          {/* Fallback Native Input */}
          <input
            type="file"
            ref={nativeFileInputRef}
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handleNativeFileSelect}
          />

          {/* Standard Captured Preview */}
          {capturedSingle ? (
            <div className="relative w-full h-full flex items-center justify-center bg-black">
              <img
                src={capturedSingle}
                alt="Captured Snapshot"
                className="w-full h-full object-contain max-h-[460px]"
              />
              <div className="absolute top-3 left-3 px-2 py-1 rounded-lg bg-black/60 backdrop-blur-md border border-white/10 text-white text-[11px] font-medium flex items-center gap-1">
                <Check className="w-3.5 h-3.5 text-[var(--accent-light)]" />
                <span>Photo Captured</span>
              </div>
            </div>
          ) : captured4DFrames.length > 0 ? (
            /* 4D Spatial Burst Preview with Parallax Angle Slider */
            <div className="relative w-full h-full flex flex-col items-center justify-center bg-black">
              <img
                src={captured4DFrames[active4DIndex]?.dataUrl}
                alt={`4D Angle ${active4DIndex + 1}`}
                className="w-full h-full object-contain max-h-[380px]"
              />

              {/* Parallax scrubber pill */}
              <div className="absolute bottom-3 inset-x-4 flex flex-col items-center gap-1.5 p-2 rounded-2xl bg-black/75 backdrop-blur-md border border-white/10">
                <div className="flex items-center justify-between w-full px-2 text-[11px] text-purple-200 font-medium">
                  <span className="flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-purple-400" />
                    <span>4D Angle {active4DIndex + 1} of {captured4DFrames.length}</span>
                  </span>
                  <span className="text-neutral-400 text-[10px]">Slide to view parallax</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={captured4DFrames.length - 1}
                  value={active4DIndex}
                  onChange={e => setActive4DIndex(Number(e.target.value))}
                  className="w-full accent-purple-500 cursor-pointer h-1.5"
                />
              </div>
            </div>
          ) : cameraError ? (
            /* Camera Error / Permission Blocked Message */
            <div className="flex flex-col items-center justify-center p-6 text-center text-neutral-300 max-w-sm space-y-3">
              <AlertCircle className="w-10 h-10 text-amber-400" />
              <p className="text-xs text-neutral-300 leading-relaxed">{cameraError}</p>
              <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
                <button
                  type="button"
                  onClick={startCamera}
                  className="px-3.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Retry Camera</span>
                </button>
                <button
                  type="button"
                  onClick={() => nativeFileInputRef.current?.click()}
                  className="px-3.5 py-1.5 rounded-xl bg-[var(--accent)] hover:opacity-90 text-black text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
                >
                  <Camera className="w-3.5 h-3.5" />
                  <span>Open System Camera</span>
                </button>
              </div>
            </div>
          ) : (
            /* Live Camera Viewfinder */
            <div className="relative w-full h-full flex items-center justify-center">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />

              {/* Viewfinder Target Reticle */}
              <div className="absolute inset-8 pointer-events-none border border-white/20 rounded-2xl flex items-center justify-center">
                <div className="w-12 h-12 border border-white/30 rounded-full" />
                <div className="absolute inset-x-0 h-[1px] bg-white/10" />
                <div className="absolute inset-y-0 w-[1px] bg-white/10" />
              </div>

              {/* 4D Spatial Guide Banner */}
              {mode === '4d_spatial' && (
                <div className="absolute top-3 inset-x-3 mx-auto max-w-xs px-3 py-1.5 rounded-xl bg-purple-950/80 border border-purple-500/40 backdrop-blur-md text-center text-purple-200 text-xs shadow-lg animate-fadeIn">
                  <div className="font-semibold flex items-center justify-center gap-1">
                    <Compass className="w-3.5 h-3.5 text-purple-400 animate-spin" style={{ animationDuration: '6s' }} />
                    <span>4D Spatial Photo Guide</span>
                  </div>
                  <div className="text-[10.5px] text-purple-300/90 mt-0.5">
                    {isCapturing4D
                      ? `Capturing angle ${progress4D.current} of ${progress4D.total}... Pivot slowly!`
                      : 'Hold steady and pivot slowly across your subject ↔️'}
                  </div>
                </div>
              )}

              {/* Flip Camera Button */}
              {streamActive && (
                <button
                  type="button"
                  onClick={handleFlipCamera}
                  disabled={isCapturing4D}
                  title="Switch front/back camera"
                  className="absolute bottom-3 right-3 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 border border-white/15 backdrop-blur-md flex items-center justify-center text-white cursor-pointer active:scale-95 transition-all"
                >
                  <FlipHorizontal className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="p-4 sm:p-5 border-t border-white/10 bg-white/[0.02] flex items-center justify-between">
          {capturedSingle ? (
            /* Review Single Photo */
            <div className="flex items-center justify-between w-full">
              <button
                type="button"
                onClick={() => setCapturedSingle(null)}
                className="px-4 py-2 rounded-2xl bg-white/5 hover:bg-white/10 text-neutral-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Retake</span>
              </button>

              <button
                type="button"
                onClick={handleConfirmSingle}
                className="px-5 py-2 rounded-2xl bg-[var(--accent)] hover:opacity-90 text-black text-xs font-bold flex items-center gap-2 cursor-pointer shadow-lg shadow-[var(--accent)]/30 active:scale-95 transition-all"
              >
                <Check className="w-4 h-4" />
                <span>Attach Photo</span>
              </button>
            </div>
          ) : captured4DFrames.length > 0 ? (
            /* Review 4D Spatial Photo */
            <div className="flex items-center justify-between w-full">
              <button
                type="button"
                onClick={() => setCaptured4DFrames([])}
                className="px-4 py-2 rounded-2xl bg-white/5 hover:bg-white/10 text-neutral-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Retake 4D</span>
              </button>

              <button
                type="button"
                onClick={handleConfirm4D}
                className="px-5 py-2 rounded-2xl bg-gradient-to-r from-purple-500 to-indigo-500 hover:opacity-90 text-white text-xs font-bold flex items-center gap-2 cursor-pointer shadow-lg shadow-purple-900/40 active:scale-95 transition-all"
              >
                <Sparkles className="w-4 h-4" />
                <span>Attach 4D Photo</span>
              </button>
            </div>
          ) : (
            /* Shutter Trigger Row */
            <div className="flex items-center justify-between w-full">
              <button
                type="button"
                onClick={() => nativeFileInputRef.current?.click()}
                title="System Camera"
                className="p-2.5 rounded-full text-neutral-400 hover:text-white hover:bg-white/5 border border-white/5 transition-colors cursor-pointer text-xs flex items-center gap-1.5"
              >
                <Eye className="w-4 h-4" />
                <span className="hidden sm:inline">System Picker</span>
              </button>

              {/* Center Shutter Button */}
              {mode === 'standard' ? (
                <button
                  type="button"
                  onClick={handleCaptureStandard}
                  disabled={!streamActive}
                  title="Take Photo"
                  className="w-16 h-16 rounded-full border-4 border-white flex items-center justify-center p-1 cursor-pointer active:scale-90 transition-transform disabled:opacity-40 disabled:pointer-events-none shadow-xl"
                >
                  <div className="w-full h-full bg-white rounded-full hover:bg-[var(--accent)] transition-colors" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleCapture4D}
                  disabled={!streamActive || isCapturing4D}
                  title="Capture 4D Spatial Photo"
                  className="px-6 py-3 rounded-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center gap-2 cursor-pointer shadow-xl shadow-purple-900/50 active:scale-95 transition-all disabled:opacity-40 disabled:pointer-events-none"
                >
                  <Sparkles className="w-4 h-4 animate-pulse" />
                  <span>{isCapturing4D ? `Capturing (${progress4D.current}/${progress4D.total})...` : 'Snap 4D Burst'}</span>
                </button>
              )}

              <div className="w-16 flex justify-end">
                {mode === '4d_spatial' && (
                  <span className="text-[10px] font-mono text-purple-300">4 Angles</span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
