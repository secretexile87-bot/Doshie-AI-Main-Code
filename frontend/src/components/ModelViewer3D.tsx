import React, { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import {
  RotateCcw,
  Play,
  Pause,
  Grid,
  Maximize2,
  Minimize2,
  Code2,
  Box,
  Eye,
  Sparkles,
} from 'lucide-react'

interface ModelViewer3DProps {
  code: string
  title?: string
  initialModelType?: string
}

export const ModelViewer3D: React.FC<ModelViewer3DProps> = ({
  code,
  title = 'Interactive 3D Model',
  initialModelType,
}) => {
  const mountRef = useRef<HTMLDivElement>(null)
  const [isAutoRotating, setIsAutoRotating] = useState(true)
  const [isWireframe, setIsWireframe] = useState(false)
  const [showGrid, setShowGrid] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showCode, setShowCode] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const controlsRef = useRef<OrbitControls | null>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const materialsRef = useRef<THREE.Material[]>([])
  const gridHelperRef = useRef<THREE.GridHelper | null>(null)
  const resetCameraRef = useRef<() => void>(() => {})

  // Detect model type from code or title or initialModelType
  const detectedType = (() => {
    const genericTags = ['3d', 'threejs', 'three', 'gltf', 'stl', 'obj', 'model3d', 'webgl', 'custom', 'model']
    if (initialModelType && !genericTags.includes(initialModelType.toLowerCase().trim())) {
      return initialModelType.toLowerCase().trim()
    }

    const text = (title + '\n' + code).toLowerCase()

    // 1. Check explicit type / model / subject header
    const typeMatch = text.match(/(?:type|model|subject|object|prompt):\s*([a-z0-9_\-\s]+)/i)
    if (typeMatch) {
      const explicit = typeMatch[1].trim()
      if (explicit.includes('house') || explicit.includes('home') || explicit.includes('cottage') || explicit.includes('cabin') || explicit.includes('bungalow') || explicit.includes('mansion') || explicit.includes('residence')) return 'house'
      if (explicit.includes('train') || explicit.includes('locomotive')) return 'train'
      if (explicit.includes('building') || explicit.includes('skyscraper') || explicit.includes('tower') || explicit.includes('city') || explicit.includes('architecture')) return 'building'
      if (explicit.includes('car') || explicit.includes('automobile') || explicit.includes('vehicle') || explicit.includes('sportscar')) return 'car'
      if (explicit.includes('robot') || explicit.includes('mech') || explicit.includes('android')) return 'robot'
      if (explicit.includes('rocket') || explicit.includes('spaceship') || explicit.includes('shuttle')) return 'rocket'
      if (explicit.includes('plane') || explicit.includes('airplane') || explicit.includes('jet') || explicit.includes('aircraft')) return 'plane'
      if (explicit.includes('solar') || explicit.includes('planet') || explicit.includes('orbit') || explicit.includes('earth')) return 'planet'
      if (explicit.includes('tree') || explicit.includes('plant') || explicit.includes('nature') || explicit.includes('forest')) return 'tree'
      if (!genericTags.includes(explicit)) return explicit
    }

    // 2. Keyword fallback across comment lines, title, or prompt
    if (text.includes('house') || text.includes('home') || text.includes('cottage') || text.includes('cabin') || text.includes('bungalow') || text.includes('mansion') || text.includes('residence')) return 'house'
    if (text.includes('train') || text.includes('locomotive') || text.includes('railroad') || text.includes('railway') || text.includes('boiler') || text.includes('smokestack')) return 'train'
    if (text.includes('building') || text.includes('skyscraper') || text.includes('tower') || text.includes('city') || text.includes('architecture')) return 'building'
    if (text.includes('car') || text.includes('automobile') || text.includes('vehicle') || text.includes('sportscar') || text.includes('sedan') || text.includes('truck')) return 'car'
    if (text.includes('robot') || text.includes('mech') || text.includes('android') || text.includes('cyborg') || text.includes('bot')) return 'robot'
    if (text.includes('rocket') || text.includes('spaceship') || text.includes('shuttle') || text.includes('spacecraft')) return 'rocket'
    if (text.includes('plane') || text.includes('airplane') || text.includes('jet') || text.includes('aircraft')) return 'plane'
    if (text.includes('solar') || text.includes('planet') || text.includes('orbit') || text.includes('earth') || text.includes('galaxy')) return 'planet'
    if (text.includes('tree') || text.includes('plant') || text.includes('nature') || text.includes('forest')) return 'tree'

    return 'custom'
  })()

  const displayTitle = (() => {
    if (title && title !== 'Interactive 3D Model') return title
    switch (detectedType) {
      case 'house':
        return '3D Cozy Home & Residence'
      case 'train':
        return '3D Steam Locomotive & Train'
      case 'building':
        return '3D Modern Skyscraper & Architecture'
      case 'tree':
        return '3D Nature & Forest Tree'
      case 'car':
        return '3D Sports Car'
      case 'robot':
        return '3D Sci-Fi Robot'
      case 'rocket':
        return '3D Rocket & Spacecraft'
      case 'plane':
        return '3D Supersonic Jet'
      case 'planet':
        return '3D Planetary Orbit'
      default:
        return 'Interactive 3D Model'
    }
  })()

  useEffect(() => {
    const container = mountRef.current
    if (!container) return

    // Setup Scene
    const scene = new THREE.Scene()
    sceneRef.current = scene
    scene.background = new THREE.Color(0x0a0e14)
    scene.fog = new THREE.FogExp2(0x0a0e14, 0.035)

    // Setup Camera
    const width = container.clientWidth || 400
    const height = container.clientHeight || 300
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    if (detectedType === 'house') {
      camera.position.set(5.5, 3.8, 5.5)
    } else if (detectedType === 'train') {
      camera.position.set(6, 4, 6)
    } else if (detectedType === 'building') {
      camera.position.set(8, 7, 8)
    } else if (detectedType === 'tree') {
      camera.position.set(5, 3.8, 5)
    } else if (detectedType === 'robot') {
      camera.position.set(4, 3, 5)
    } else if (detectedType === 'rocket') {
      camera.position.set(5, 3.5, 6)
    } else if (detectedType === 'car') {
      camera.position.set(5, 3, 5)
    } else if (detectedType === 'plane') {
      camera.position.set(5, 3.5, 5)
    } else {
      camera.position.set(5, 3.5, 6)
    }

    // Setup Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    container.innerHTML = ''
    container.appendChild(renderer.domElement)

    // Setup Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controlsRef.current = controls
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.autoRotate = isAutoRotating
    controls.autoRotateSpeed = 2.0
    controls.maxPolarAngle = Math.PI / 2 + 0.05 // Don't go completely under floor
    controls.minDistance = 2
    controls.maxDistance = 25

    resetCameraRef.current = () => {
      if (detectedType === 'house') {
        camera.position.set(5.5, 3.8, 5.5)
        controls.target.set(0, 1.3, 0)
      } else if (detectedType === 'train') {
        camera.position.set(6, 4, 6)
        controls.target.set(0, 1.2, 0)
      } else if (detectedType === 'building') {
        camera.position.set(8, 7, 8)
        controls.target.set(0, 4.5, 0)
      } else if (detectedType === 'tree') {
        camera.position.set(5, 3.8, 5)
        controls.target.set(0, 2.8, 0)
      } else if (detectedType === 'robot') {
        camera.position.set(4, 3, 5)
        controls.target.set(0, 2.0, 0)
      } else if (detectedType === 'rocket') {
        camera.position.set(5, 3.5, 6)
        controls.target.set(0, 2.5, 0)
      } else if (detectedType === 'car') {
        camera.position.set(5, 3, 5)
        controls.target.set(0, 0.8, 0)
      } else if (detectedType === 'plane') {
        camera.position.set(5, 3.5, 5)
        controls.target.set(0, 1.5, 0)
      } else {
        camera.position.set(5, 3.5, 6)
        controls.target.set(0, 1.5, 0)
      }
      controls.update()
    }

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8)
    scene.add(ambientLight)

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8)
    keyLight.position.set(8, 12, 6)
    keyLight.castShadow = true
    keyLight.shadow.mapSize.width = 1024
    keyLight.shadow.mapSize.height = 1024
    keyLight.shadow.camera.near = 0.5
    keyLight.shadow.camera.far = 30
    keyLight.shadow.bias = -0.0005
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.9)
    fillLight.position.set(-8, 5, -5)
    scene.add(fillLight)

    const rimLight = new THREE.DirectionalLight(0xf43f5e, 0.6)
    rimLight.position.set(0, -5, -6)
    scene.add(rimLight)

    // Studio Grid & Ground Platform
    const grid = new THREE.GridHelper(20, 20, 0x38bdf8, 0x1e293b)
    grid.position.y = 0
    gridHelperRef.current = grid
    scene.add(grid)

    // Shadow Receiver Ground Plane
    const shadowPlaneGeo = new THREE.PlaneGeometry(30, 30)
    const shadowPlaneMat = new THREE.ShadowMaterial({ opacity: 0.4 })
    const shadowPlane = new THREE.Mesh(shadowPlaneGeo, shadowPlaneMat)
    shadowPlane.rotation.x = -Math.PI / 2
    shadowPlane.position.y = -0.01
    shadowPlane.receiveShadow = true
    scene.add(shadowPlane)

    const materials: THREE.Material[] = []
    materialsRef.current = materials
    const animatedObjects: Array<(delta: number, elapsed: number) => void> = []

    // Helper to register materials for wireframe toggle
    const regMat = <T extends THREE.Material>(m: T): T => {
      materials.push(m)
      return m
    }

    try {
      // 1. Procedural Models based on detected type
      if (detectedType === 'train') {
        const trainGroup = new THREE.Group()

        // Track Rails
        const railMat = regMat(new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8, roughness: 0.3 }))
        const sleeperMat = regMat(new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.9 }))

        // Sleepers (ties)
        for (let z = -5; z <= 5; z += 0.5) {
          const tie = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.08, 0.25), sleeperMat)
          tie.position.set(0, 0.04, z)
          tie.receiveShadow = true
          trainGroup.add(tie)
        }

        // Two steel rails
        const railL = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.15, 12), railMat)
        railL.position.set(-0.85, 0.15, 0)
        railL.castShadow = true
        trainGroup.add(railL)

        const railR = railL.clone()
        railR.position.set(0.85, 0.15, 0)
        trainGroup.add(railR)

        // Locomotive Body Materials
        const bodyMat = regMat(new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.4, metalness: 0.6 }))
        const redAccentMat = regMat(new THREE.MeshStandardMaterial({ color: 0xbe123c, roughness: 0.3, metalness: 0.4 }))
        const brassMat = regMat(new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.2, metalness: 0.9 }))
        const wheelMat = regMat(new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.5, metalness: 0.8 }))
        const glowLampMat = new THREE.MeshBasicMaterial({ color: 0xfef08a })

        // Boiler Cylinder (Main engine body)
        const boilerGeo = new THREE.CylinderGeometry(0.75, 0.75, 3.2, 32)
        const boiler = new THREE.Mesh(boilerGeo, bodyMat)
        boiler.rotation.x = Math.PI / 2
        boiler.position.set(0, 1.45, -0.6)
        boiler.castShadow = true
        trainGroup.add(boiler)

        // Boiler Front Plate
        const frontBoiler = new THREE.Mesh(new THREE.SphereGeometry(0.75, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), redAccentMat)
        frontBoiler.rotation.x = -Math.PI / 2
        frontBoiler.position.set(0, 1.45, -2.2)
        frontBoiler.castShadow = true
        trainGroup.add(frontBoiler)

        // Golden bands around boiler
        for (const bz of [-0.2, -0.9, -1.6]) {
          const band = new THREE.Mesh(new THREE.TorusGeometry(0.77, 0.025, 16, 32), brassMat)
          band.position.set(0, 1.45, bz)
          trainGroup.add(band)
        }

        // Smokestack (Chimney)
        const stackGeo = new THREE.CylinderGeometry(0.22, 0.16, 0.8, 16)
        const smokestack = new THREE.Mesh(stackGeo, redAccentMat)
        smokestack.position.set(0, 2.4, -1.8)
        smokestack.castShadow = true
        trainGroup.add(smokestack)

        const stackRim = new THREE.Mesh(new THREE.TorusGeometry(0.24, 0.04, 16, 32), brassMat)
        stackRim.rotation.x = Math.PI / 2
        stackRim.position.set(0, 2.8, -1.8)
        trainGroup.add(stackRim)

        // Steam Dome (Golden dome on boiler)
        const dome = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16, 16), brassMat)
        dome.position.set(0, 2.25, -0.8)
        dome.scale.set(1, 1.3, 1)
        dome.castShadow = true
        trainGroup.add(dome)

        // Cab (Cabin for driver)
        const cab = new THREE.Mesh(new THREE.BoxGeometry(1.7, 1.9, 1.6), redAccentMat)
        cab.position.set(0, 1.7, 1.3)
        cab.castShadow = true
        trainGroup.add(cab)

        // Cab Roof curved
        const roof = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.05, 1.8, 24, 1, false, 0, Math.PI), bodyMat)
        roof.rotation.x = Math.PI / 2
        roof.rotation.z = Math.PI
        roof.position.set(0, 2.55, 1.3)
        roof.scale.set(0.9, 0.4, 1)
        roof.castShadow = true
        trainGroup.add(roof)

        // Windows on Cab
        const windowMat = regMat(new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.1, metalness: 0.9, transparent: true, opacity: 0.7 }))
        const winL = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 0.5), windowMat)
        winL.rotation.y = -Math.PI / 2
        winL.position.set(-0.86, 2.0, 1.3)
        trainGroup.add(winL)

        const winR = winL.clone()
        winR.rotation.y = Math.PI / 2
        winR.position.set(0.86, 2.0, 1.3)
        trainGroup.add(winR)

        // Cowcatcher / Pilot Grill at front
        const cowcatcherGroup = new THREE.Group()
        for (let i = -0.7; i <= 0.7; i += 0.22) {
          const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.7, 8), redAccentMat)
          bar.position.set(i, 0.45, -2.5 - Math.abs(i) * 0.4)
          bar.rotation.x = -Math.PI / 6
          bar.castShadow = true
          cowcatcherGroup.add(bar)
        }
        trainGroup.add(cowcatcherGroup)

        // Headlight with volumetric beam glow
        const lamp = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.16, 0.4, 16), brassMat)
        lamp.rotation.x = Math.PI / 2
        lamp.position.set(0, 1.8, -2.3)
        trainGroup.add(lamp)

        const lampLens = new THREE.Mesh(new THREE.CircleGeometry(0.18, 16), glowLampMat)
        lampLens.rotation.y = Math.PI
        lampLens.position.set(0, 1.8, -2.51)
        trainGroup.add(lampLens)

        const headlightLight = new THREE.SpotLight(0xfef08a, 4, 12, Math.PI / 6, 0.5)
        headlightLight.position.set(0, 1.8, -2.5)
        headlightLight.target.position.set(0, 0.5, -10)
        scene.add(headlightLight.target)
        trainGroup.add(headlightLight)

        // Main Wheels (Large 4-6 driving wheels)
        const wheels: THREE.Mesh[] = []
        const wheelRadius = 0.55
        for (const z of [-0.2, 0.8, 1.8]) {
          // Left Wheel
          const wheelL = new THREE.Mesh(new THREE.CylinderGeometry(wheelRadius, wheelRadius, 0.14, 24), wheelMat)
          wheelL.rotation.z = Math.PI / 2
          wheelL.position.set(-0.88, wheelRadius + 0.1, z)
          wheelL.castShadow = true
          trainGroup.add(wheelL)
          wheels.push(wheelL)

          // Right Wheel
          const wheelR = wheelL.clone()
          wheelR.position.set(0.88, wheelRadius + 0.1, z)
          trainGroup.add(wheelR)
          wheels.push(wheelR)
        }

        // Front small wheels
        for (const z of [-1.5, -2.1]) {
          const smallRadius = 0.3
          const swL = new THREE.Mesh(new THREE.CylinderGeometry(smallRadius, smallRadius, 0.12, 16), wheelMat)
          swL.rotation.z = Math.PI / 2
          swL.position.set(-0.88, smallRadius + 0.1, z)
          swL.castShadow = true
          trainGroup.add(swL)
          wheels.push(swL)

          const swR = swL.clone()
          swR.position.set(0.88, smallRadius + 0.1, z)
          trainGroup.add(swR)
          wheels.push(swR)
        }

        // Connecting Side Rods
        const rodMat = regMat(new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 }))
        const sideRodL = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.08, 2.2), rodMat)
        sideRodL.position.set(-0.98, wheelRadius + 0.1, 0.8)
        trainGroup.add(sideRodL)

        const sideRodR = sideRodL.clone()
        sideRodR.position.set(0.98, wheelRadius + 0.1, 0.8)
        trainGroup.add(sideRodR)

        // Tender Car (Coal / Fuel Car coupled behind)
        const tender = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.2, 2.2), bodyMat)
        tender.position.set(0, 1.0, 3.4)
        tender.castShadow = true
        trainGroup.add(tender)

        // Coal chunks in tender
        const coalMat = regMat(new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.9 }))
        const coalPile = new THREE.Mesh(new THREE.DodecahedronGeometry(0.7, 1), coalMat)
        coalPile.position.set(0, 1.5, 3.4)
        coalPile.scale.set(1, 0.5, 1.4)
        trainGroup.add(coalPile)

        // Tender Wheels
        for (const z of [2.7, 4.1]) {
          const twL = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 0.12, 16), wheelMat)
          twL.rotation.z = Math.PI / 2
          twL.position.set(-0.85, 0.45, z)
          twL.castShadow = true
          trainGroup.add(twL)
          wheels.push(twL)

          const twR = twL.clone()
          twR.position.set(0.85, 0.45, z)
          trainGroup.add(twR)
          wheels.push(twR)
        }

        // Animated Steam Puffs from Smokestack
        const smokePuffs: Array<{ mesh: THREE.Mesh; speed: number; startY: number }> = []
        const smokeMat = regMat(new THREE.MeshStandardMaterial({
          color: 0xffffff,
          roughness: 1.0,
          transparent: true,
          opacity: 0.45,
        }))
        for (let s = 0; s < 7; s++) {
          const puff = new THREE.Mesh(new THREE.DodecahedronGeometry(0.18 + s * 0.04, 1), smokeMat)
          puff.position.set(0, 2.8 + s * 0.4, -1.8 - s * 0.4)
          trainGroup.add(puff)
          smokePuffs.push({
            mesh: puff,
            speed: 0.8 + Math.random() * 0.4,
            startY: 2.8,
          })
        }

        animatedObjects.push((_delta, elapsed) => {
          // Rotate train wheels
          for (const w of wheels) {
            w.rotation.x += 0.05
          }
          // Cycle side rods
          sideRodL.position.y = wheelRadius + 0.1 + Math.sin(elapsed * 5) * 0.15
          sideRodR.position.y = wheelRadius + 0.1 + Math.cos(elapsed * 5) * 0.15

          // Animate steam puffs rising and drifting back
          smokePuffs.forEach((p) => {
            p.mesh.position.y += 0.015 * p.speed
            p.mesh.position.z += 0.02 * p.speed
            p.mesh.scale.multiplyScalar(1.004)
            if (p.mesh.position.y > 5.5) {
              p.mesh.position.set(0, p.startY, -1.8)
              p.mesh.scale.set(1, 1, 1)
            }
          })
        })

        scene.add(trainGroup)
        controls.target.set(0, 1.2, 0)
      } else if (detectedType === 'robot') {
        // High-tech Sci-Fi Robot
        const botGroup = new THREE.Group()
        const metalMat = regMat(new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8, roughness: 0.2 }))
        const accentMat = regMat(new THREE.MeshStandardMaterial({ color: 0x38bdf8, metalness: 0.6, roughness: 0.3 }))
        const glowVisorMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 })

        // Torso
        const torso = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.6, 0.9), metalMat)
        torso.position.y = 2.2
        torso.castShadow = true
        botGroup.add(torso)

        // Chest Core Arc
        const core = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.1, 16), glowVisorMat)
        core.rotation.x = Math.PI / 2
        core.position.set(0, 2.3, 0.48)
        botGroup.add(core)

        // Head
        const head = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.75, 0.8), accentMat)
        head.position.y = 3.4
        head.castShadow = true
        botGroup.add(head)

        // Visor Eye
        const visor = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.18, 0.1), glowVisorMat)
        visor.position.set(0, 3.4, 0.42)
        botGroup.add(visor)

        // Antenna
        const ant = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.5, 8), metalMat)
        ant.position.set(0.3, 3.9, 0)
        botGroup.add(ant)

        // Arms
        for (const side of [-1, 1]) {
          const arm = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.2, 0.3), metalMat)
          arm.position.set(side * 1.0, 2.1, 0)
          arm.castShadow = true
          botGroup.add(arm)

          const leg = new THREE.Mesh(new THREE.BoxGeometry(0.4, 1.4, 0.45), metalMat)
          leg.position.set(side * 0.45, 0.7, 0)
          leg.castShadow = true
          botGroup.add(leg)
        }

        scene.add(botGroup)
        controls.target.set(0, 2.0, 0)
      } else if (detectedType === 'rocket') {
        // Space Shuttle / Rocket
        const rocketGroup = new THREE.Group()
        const hullMat = regMat(new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.5, roughness: 0.2 }))
        const wingMat = regMat(new THREE.MeshStandardMaterial({ color: 0xe11d48, metalness: 0.3, roughness: 0.4 }))
        const fireMat = new THREE.MeshBasicMaterial({ color: 0xf97316 })

        // Body Cylinder
        const body = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 3.5, 32), hullMat)
        body.position.y = 2.4
        body.castShadow = true
        rocketGroup.add(body)

        // Nose Cone
        const cone = new THREE.Mesh(new THREE.ConeGeometry(0.6, 1.2, 32), wingMat)
        cone.position.y = 4.75
        cone.castShadow = true
        rocketGroup.add(cone)

        // Fins
        for (let i = 0; i < 4; i++) {
          const fin = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.9, 0.6), wingMat)
          const angle = (i * Math.PI) / 2
          fin.position.set(Math.sin(angle) * 0.75, 1.2, Math.cos(angle) * 0.75)
          fin.rotation.y = angle
          fin.castShadow = true
          rocketGroup.add(fin)
        }

        // Thruster flame
        const flame = new THREE.Mesh(new THREE.ConeGeometry(0.4, 1.2, 16), fireMat)
        flame.rotation.x = Math.PI
        flame.position.y = 0.2
        rocketGroup.add(flame)

        animatedObjects.push((_d, elapsed) => {
          flame.scale.y = 1.0 + Math.sin(elapsed * 20) * 0.25
        })

        scene.add(rocketGroup)
        controls.target.set(0, 2.5, 0)
      } else if (detectedType === 'car') {
        // High-performance Modern Sports Car
        const carGroup = new THREE.Group()
        const carBodyMat = regMat(new THREE.MeshStandardMaterial({
          color: 0xdc2626,
          metalness: 0.85,
          roughness: 0.15,
        }))
        const glassMat = regMat(new THREE.MeshStandardMaterial({
          color: 0x0f172a,
          metalness: 0.9,
          roughness: 0.1,
          transparent: true,
          opacity: 0.8,
        }))
        const carWheelMat = regMat(new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.7 }))
        const rimMat = regMat(new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.9, roughness: 0.15 }))
        const carTrimMat = regMat(new THREE.MeshStandardMaterial({ color: 0x09090b, roughness: 0.5 }))
        const headlightMat = new THREE.MeshBasicMaterial({ color: 0xffffff })
        const taillightMat = new THREE.MeshBasicMaterial({ color: 0xff0033 })

        // Lower chassis
        const chassis = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.45, 4.6), carBodyMat)
        chassis.position.y = 0.5
        chassis.castShadow = true
        carGroup.add(chassis)

        // Front bumper / splitter
        const splitter = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.1, 0.6), carTrimMat)
        splitter.position.set(0, 0.25, -2.35)
        splitter.castShadow = true
        carGroup.add(splitter)

        // Cockpit / Cabin
        const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.55, 2.2), carBodyMat)
        cabin.position.set(0, 0.95, 0.1)
        cabin.castShadow = true
        carGroup.add(cabin)

        // Windshield (slanted)
        const windshield = new THREE.Mesh(new THREE.BoxGeometry(1.42, 0.5, 0.7), glassMat)
        windshield.position.set(0, 0.96, -0.75)
        windshield.rotation.x = -Math.PI / 4.5
        carGroup.add(windshield)

        // Rear window (slanted)
        const rearWindow = new THREE.Mesh(new THREE.BoxGeometry(1.42, 0.48, 0.8), glassMat)
        rearWindow.position.set(0, 0.94, 0.95)
        rearWindow.rotation.x = Math.PI / 5
        carGroup.add(rearWindow)

        // Side windows
        for (const side of [-1, 1]) {
          const sideWindow = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.38), glassMat)
          sideWindow.position.set(side * 0.76, 0.96, 0.1)
          sideWindow.rotation.y = side * (Math.PI / 2)
          carGroup.add(sideWindow)
        }

        // Headlights
        for (const side of [-0.68, 0.68]) {
          const lightMesh = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.12, 0.1), headlightMat)
          lightMesh.position.set(side, 0.55, -2.31)
          carGroup.add(lightMesh)

          const spot = new THREE.SpotLight(0xffffff, 3, 10, Math.PI / 6, 0.4)
          spot.position.set(side, 0.55, -2.35)
          spot.target.position.set(side, 0.2, -10)
          scene.add(spot.target)
          carGroup.add(spot)
        }

        // Taillight bar across back
        const taillight = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.1, 0.08), taillightMat)
        taillight.position.set(0, 0.6, 2.31)
        carGroup.add(taillight)

        // Rear Aerodynamic Spoiler Wing
        const spoilerWing = new THREE.Mesh(new THREE.BoxGeometry(1.85, 0.06, 0.4), carTrimMat)
        spoilerWing.position.set(0, 1.25, 2.1)
        spoilerWing.castShadow = true
        carGroup.add(spoilerWing)

        for (const side of [-0.55, 0.55]) {
          const strut = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.35, 0.15), carTrimMat)
          strut.position.set(side, 1.05, 2.05)
          carGroup.add(strut)
        }

        // Exhaust pipes
        for (const side of [-0.3, 0.3]) {
          const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.25, 16), rimMat)
          pipe.rotation.x = Math.PI / 2
          pipe.position.set(side, 0.32, 2.35)
          carGroup.add(pipe)
        }

        // 4 Sports Wheels with Rims
        const carWheels: THREE.Mesh[] = []
        const wheelPositions = [
          { x: -1.02, z: -1.35 },
          { x: 1.02, z: -1.35 },
          { x: -1.02, z: 1.35 },
          { x: 1.02, z: 1.35 },
        ]

        wheelPositions.forEach((pos) => {
          const wheelHub = new THREE.Group()
          wheelHub.position.set(pos.x, 0.42, pos.z)

          const tire = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.26, 24), carWheelMat)
          tire.rotation.z = Math.PI / 2
          tire.castShadow = true
          wheelHub.add(tire)

          const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.27, 16), rimMat)
          rim.rotation.z = Math.PI / 2
          wheelHub.add(rim)

          carGroup.add(wheelHub)
          carWheels.push(tire)
        })

        animatedObjects.push((_d, _elapsed) => {
          carWheels.forEach((w) => {
            w.rotation.x += 0.04
          })
        })

        scene.add(carGroup)
        controls.target.set(0, 0.8, 0)
      } else if (detectedType === 'plane') {
        // Sleek Supersonic Jet
        const planeGroup = new THREE.Group()
        const fuselageMat = regMat(new THREE.MeshStandardMaterial({ color: 0xf1f5f9, metalness: 0.6, roughness: 0.25 }))
        const canopyMat = regMat(new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.9, roughness: 0.1, transparent: true, opacity: 0.8 }))
        const wingMat = regMat(new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7, roughness: 0.3 }))
        const afterburnerMat = new THREE.MeshBasicMaterial({ color: 0x0284c7 })

        // Fuselage Body
        const fuselage = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.35, 5.0, 24), fuselageMat)
        fuselage.rotation.x = Math.PI / 2
        fuselage.position.set(0, 1.8, 0)
        fuselage.castShadow = true
        planeGroup.add(fuselage)

        // Nose Cone
        const nose = new THREE.Mesh(new THREE.ConeGeometry(0.45, 1.6, 24), fuselageMat)
        nose.rotation.x = -Math.PI / 2
        nose.position.set(0, 1.8, -3.3)
        nose.castShadow = true
        planeGroup.add(nose)

        // Canopy Cockpit
        const canopy = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 16), canopyMat)
        canopy.position.set(0, 2.15, -1.2)
        canopy.scale.set(0.9, 0.8, 2.4)
        planeGroup.add(canopy)

        // Delta Main Wings
        const leftWing = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.06, 2.2), wingMat)
        leftWing.position.set(-1.4, 1.75, 0.3)
        leftWing.rotation.y = -Math.PI / 7
        leftWing.castShadow = true
        planeGroup.add(leftWing)

        const rightWing = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.06, 2.2), wingMat)
        rightWing.position.set(1.4, 1.75, 0.3)
        rightWing.rotation.y = Math.PI / 7
        rightWing.castShadow = true
        planeGroup.add(rightWing)

        // Vertical Stabilizer / Tail Fin
        const tailFin = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.2, 1.2), wingMat)
        tailFin.position.set(0, 2.6, 2.1)
        tailFin.rotation.x = -Math.PI / 8
        tailFin.castShadow = true
        planeGroup.add(tailFin)

        // Twin Afterburners
        for (const side of [-0.22, 0.22]) {
          const jet = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 0.5, 16), wingMat)
          jet.rotation.x = Math.PI / 2
          jet.position.set(side, 1.8, 2.6)
          planeGroup.add(jet)

          const flame = new THREE.Mesh(new THREE.ConeGeometry(0.14, 0.8, 16), afterburnerMat)
          flame.rotation.x = Math.PI / 2
          flame.position.set(side, 1.8, 3.1)
          planeGroup.add(flame)

          animatedObjects.push((_d, elapsed) => {
            flame.scale.z = 1.0 + Math.sin(elapsed * 25 + side) * 0.3
          })
        }

        // Slight banking / floating animation
        animatedObjects.push((_d, elapsed) => {
          planeGroup.rotation.z = Math.sin(elapsed * 1.5) * 0.08
          planeGroup.position.y = Math.sin(elapsed * 2.0) * 0.1
        })

        scene.add(planeGroup)
        controls.target.set(0, 1.8, 0)
      } else if (detectedType === 'planet') {
        // Planetary Orbit System
        const solarGroup = new THREE.Group()
        const planetMat = regMat(new THREE.MeshStandardMaterial({
          color: 0x0284c7,
          roughness: 0.6,
          metalness: 0.2,
        }))
        const planet = new THREE.Mesh(new THREE.SphereGeometry(1.4, 32, 32), planetMat)
        planet.position.y = 1.8
        planet.castShadow = true
        solarGroup.add(planet)

        // Planetary Rings
        const ringGeo = new THREE.RingGeometry(1.8, 2.7, 48)
        const ringMat = regMat(new THREE.MeshStandardMaterial({
          color: 0x38bdf8,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.75,
        }))
        const rings = new THREE.Mesh(ringGeo, ringMat)
        rings.rotation.x = Math.PI / 2.5
        rings.position.y = 1.8
        solarGroup.add(rings)

        // Moon
        const moonMat = regMat(new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.8 }))
        const moon = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16, 16), moonMat)
        solarGroup.add(moon)

        animatedObjects.push((_d, elapsed) => {
          planet.rotation.y += 0.005
          rings.rotation.z += 0.003
          moon.position.set(
            Math.cos(elapsed * 1.2) * 3.4,
            1.8 + Math.sin(elapsed * 1.2) * 0.5,
            Math.sin(elapsed * 1.2) * 3.4
          )
        })

        scene.add(solarGroup)
        controls.target.set(0, 1.8, 0)
      } else if (detectedType === 'house') {
        // Detailed Cozy Suburban Home & Architecture
        const houseGroup = new THREE.Group()

        // Materials
        const lawnMat = regMat(new THREE.MeshStandardMaterial({ color: 0x16a34a, roughness: 0.85 }))
        const pathMat = regMat(new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.9 }))
        const sidingMat = regMat(new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.6 }))
        const brickMat = regMat(new THREE.MeshStandardMaterial({ color: 0xb91c1c, roughness: 0.85 }))
        const roofShingleMat = regMat(new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.45 }))
        const trimMat = regMat(new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.5 }))
        const woodDoorMat = regMat(new THREE.MeshStandardMaterial({ color: 0x92400e, roughness: 0.5 }))
        const windowGlowMat = regMat(new THREE.MeshStandardMaterial({
          color: 0xfef08a,
          emissive: 0xfef08a,
          emissiveIntensity: 0.65,
          roughness: 0.2,
        }))
        const brassMat = regMat(new THREE.MeshStandardMaterial({ color: 0xfacc15, metalness: 0.8, roughness: 0.2 }))
        const darkWoodMat = regMat(new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.8 }))
        const bushMat = regMat(new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.6 }))
        const flowerMat = regMat(new THREE.MeshStandardMaterial({ color: 0xf43f5e, roughness: 0.5 }))
        const smokeMat = regMat(new THREE.MeshStandardMaterial({
          color: 0xe2e8f0,
          transparent: true,
          opacity: 0.6,
          roughness: 1.0,
        }))

        // 1. Green Lawn Base
        const lawn = new THREE.Mesh(new THREE.BoxGeometry(6.6, 0.25, 6.2), lawnMat)
        lawn.position.y = 0.125
        lawn.receiveShadow = true
        houseGroup.add(lawn)

        // 2. Stone Walkway to front porch
        for (let i = 0; i < 5; i++) {
          const stone = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.04, 0.35), pathMat)
          stone.position.set(0, 0.26, 1.45 + i * 0.42)
          stone.receiveShadow = true
          houseGroup.add(stone)
        }

        // 3. Foundation / Brick Base
        const foundation = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.4, 2.8), brickMat)
        foundation.position.set(0, 0.4, 0)
        foundation.castShadow = true
        foundation.receiveShadow = true
        houseGroup.add(foundation)

        // 4. Main House Walls (1st Floor)
        const walls = new THREE.Mesh(new THREE.BoxGeometry(3.4, 1.6, 2.6), sidingMat)
        walls.position.set(0, 1.4, 0)
        walls.castShadow = true
        walls.receiveShadow = true
        houseGroup.add(walls)

        // Horizontal siding lines texture details
        for (let y = 0.7; y <= 2.1; y += 0.2) {
          const sidingLine = new THREE.Mesh(new THREE.BoxGeometry(3.42, 0.02, 2.62), sidingMat)
          sidingLine.position.set(0, y, 0)
          houseGroup.add(sidingLine)
        }

        // 5. Gable Triangular Walls (Front and Back)
        const gableShape = new THREE.Shape()
        gableShape.moveTo(-1.7, 0)
        gableShape.lineTo(0, 1.15)
        gableShape.lineTo(1.7, 0)
        gableShape.closePath()

        const gableGeo = new THREE.ShapeGeometry(gableShape)
        const frontGable = new THREE.Mesh(gableGeo, sidingMat)
        frontGable.position.set(0, 2.2, 1.305)
        houseGroup.add(frontGable)

        const backGable = new THREE.Mesh(gableGeo, sidingMat)
        backGable.position.set(0, 2.2, -1.305)
        backGable.rotation.y = Math.PI
        houseGroup.add(backGable)

        // 6. Pitched Roof Slopes
        const roofLeft = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.1, 3.1), roofShingleMat)
        roofLeft.position.set(-0.95, 2.76, 0)
        roofLeft.rotation.z = Math.PI * 0.185
        roofLeft.castShadow = true
        houseGroup.add(roofLeft)

        const roofRight = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.1, 3.1), roofShingleMat)
        roofRight.position.set(0.95, 2.76, 0)
        roofRight.rotation.z = -Math.PI * 0.185
        roofRight.castShadow = true
        houseGroup.add(roofRight)

        // Ridge Beam on Top
        const ridge = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.16, 3.12), roofShingleMat)
        ridge.position.set(0, 3.42, 0)
        houseGroup.add(ridge)

        // 7. Brick Chimney
        const chimney = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.4, 0.5), brickMat)
        chimney.position.set(0.9, 2.9, -0.4)
        chimney.castShadow = true
        houseGroup.add(chimney)

        const chimneyCap = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.08, 0.62), pathMat)
        chimneyCap.position.set(0.9, 3.64, -0.4)
        houseGroup.add(chimneyCap)

        // Chimney Smoke Puffs
        const smokePuff1 = new THREE.Mesh(new THREE.SphereGeometry(0.14, 10, 10), smokeMat)
        smokePuff1.position.set(0.9, 3.85, -0.4)
        houseGroup.add(smokePuff1)

        const smokePuff2 = new THREE.Mesh(new THREE.SphereGeometry(0.2, 10, 10), smokeMat)
        smokePuff2.position.set(0.98, 4.15, -0.42)
        houseGroup.add(smokePuff2)

        // 8. Front Porch & Doorway
        const porchDeck = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.2, 0.9), pathMat)
        porchDeck.position.set(0, 0.35, 1.6)
        porchDeck.receiveShadow = true
        houseGroup.add(porchDeck)

        const porchStep = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.12, 0.35), pathMat)
        porchStep.position.set(0, 0.2, 2.1)
        porchStep.receiveShadow = true
        houseGroup.add(porchStep)

        // Porch Columns
        const columnL = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 1.4, 8), sidingMat)
        columnL.position.set(-0.65, 1.15, 1.95)
        columnL.castShadow = true
        houseGroup.add(columnL)

        const columnR = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 1.4, 8), sidingMat)
        columnR.position.set(0.65, 1.15, 1.95)
        columnR.castShadow = true
        houseGroup.add(columnR)

        // Porch Awning / Roof
        const porchAwning = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.1, 1.05), roofShingleMat)
        porchAwning.position.set(0, 1.9, 1.62)
        porchAwning.castShadow = true
        houseGroup.add(porchAwning)

        // Front Door
        const door = new THREE.Mesh(new THREE.BoxGeometry(0.65, 1.15, 0.06), woodDoorMat)
        door.position.set(0, 1.18, 1.32)
        door.castShadow = true
        houseGroup.add(door)

        const doorTrim = new THREE.Mesh(new THREE.BoxGeometry(0.75, 1.25, 0.04), trimMat)
        doorTrim.position.set(0, 1.18, 1.31)
        houseGroup.add(doorTrim)

        const doorKnob = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), brassMat)
        doorKnob.position.set(0.22, 1.15, 1.36)
        houseGroup.add(doorKnob)

        // Porch Lantern Light
        const lantern = new THREE.Mesh(new THREE.SphereGeometry(0.06, 8, 8), windowGlowMat)
        lantern.position.set(0.48, 1.55, 1.33)
        houseGroup.add(lantern)

        // 9. Windows with Cozy Warm Light & Shutters
        const makeWindow = (wx: number, wy: number, wz: number) => {
          const win = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.65, 0.05), windowGlowMat)
          win.position.set(wx, wy, wz)
          houseGroup.add(win)
          const hBar = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.03, 0.06), trimMat)
          hBar.position.set(wx, wy, wz)
          houseGroup.add(hBar)
          const vBar = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.65, 0.06), trimMat)
          vBar.position.set(wx, wy, wz)
          houseGroup.add(vBar)
          const leftShutter = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.65, 0.04), trimMat)
          leftShutter.position.set(wx - 0.36, wy, wz)
          houseGroup.add(leftShutter)
          const rightShutter = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.65, 0.04), trimMat)
          rightShutter.position.set(wx + 0.36, wy, wz)
          houseGroup.add(rightShutter)
        }

        makeWindow(-1.0, 1.35, 1.32)
        makeWindow(1.0, 1.35, 1.32)

        // Attic Round Window
        const atticWin = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.05, 16), windowGlowMat)
        atticWin.rotation.x = Math.PI / 2
        atticWin.position.set(0, 2.55, 1.32)
        houseGroup.add(atticWin)

        const atticTrim = new THREE.Mesh(new THREE.TorusGeometry(0.25, 0.03, 8, 24), trimMat)
        atticTrim.position.set(0, 2.55, 1.33)
        houseGroup.add(atticTrim)

        // Side Windows
        const sideWinL = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.65, 0.65), windowGlowMat)
        sideWinL.position.set(-1.72, 1.35, 0)
        houseGroup.add(sideWinL)

        const sideWinR = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.65, 0.65), windowGlowMat)
        sideWinR.position.set(1.72, 1.35, 0)
        houseGroup.add(sideWinR)

        // 10. Front Yard Landscaping: Bushes & Small Tree
        const bushCoords = [
          [-1.3, 0.45, 1.4], [-1.0, 0.45, 1.45],
          [1.0, 0.45, 1.45], [1.3, 0.45, 1.4]
        ]
        bushCoords.forEach(([bx, by, bz]) => {
          const bush = new THREE.Mesh(new THREE.DodecahedronGeometry(0.24, 1), bushMat)
          bush.position.set(bx, by, bz)
          bush.castShadow = true
          houseGroup.add(bush)

          const fl = new THREE.Mesh(new THREE.SphereGeometry(0.04, 6, 6), flowerMat)
          fl.position.set(bx + 0.05, by + 0.15, bz + 0.1)
          houseGroup.add(fl)
        })

        // Cozy Pine Tree in Front Yard
        const treeTrunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.7, 8), darkWoodMat)
        treeTrunk.position.set(-2.2, 0.55, 1.8)
        treeTrunk.castShadow = true
        houseGroup.add(treeTrunk)

        const foliage1 = new THREE.Mesh(new THREE.ConeGeometry(0.65, 0.9, 8), bushMat)
        foliage1.position.set(-2.2, 1.1, 1.8)
        foliage1.castShadow = true
        houseGroup.add(foliage1)

        const foliage2 = new THREE.Mesh(new THREE.ConeGeometry(0.48, 0.8, 8), bushMat)
        foliage2.position.set(-2.2, 1.6, 1.8)
        foliage2.castShadow = true
        houseGroup.add(foliage2)

        // Animated Chimney Smoke
        animatedObjects.push((_d, elapsed) => {
          smokePuff1.position.y = 3.85 + Math.sin(elapsed * 2) * 0.08
          smokePuff1.scale.setScalar(0.9 + Math.sin(elapsed * 2) * 0.15)
          smokePuff2.position.y = 4.18 + Math.sin(elapsed * 2 + 1) * 0.12
          smokePuff2.scale.setScalar(1.0 + Math.cos(elapsed * 2) * 0.2)
        })

        scene.add(houseGroup)
        controls.target.set(0, 1.4, 0)
      } else if (detectedType === 'building') {
        // Modern Architectural Skyscraper Complex
        const buildingGroup = new THREE.Group()
        const glassMat = regMat(new THREE.MeshStandardMaterial({
          color: 0x0284c7,
          metalness: 0.9,
          roughness: 0.1,
          transparent: true,
          opacity: 0.85,
        }))
        const steelMat = regMat(new THREE.MeshStandardMaterial({
          color: 0x1e293b,
          metalness: 0.8,
          roughness: 0.3,
        }))
        const concreteMat = regMat(new THREE.MeshStandardMaterial({
          color: 0x334155,
          roughness: 0.8,
        }))
        const warmLightMat = new THREE.MeshBasicMaterial({ color: 0xfef08a })
        const beaconMat = new THREE.MeshBasicMaterial({ color: 0xef4444 })

        // Plaza Base Podium
        const plaza = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.3, 6.0), concreteMat)
        plaza.position.y = 0.15
        plaza.receiveShadow = true
        buildingGroup.add(plaza)

        // Lower Tower Tier (Podium Floors 1-4)
        const tier1 = new THREE.Mesh(new THREE.BoxGeometry(3.6, 1.8, 3.2), steelMat)
        tier1.position.set(0, 1.2, 0)
        tier1.castShadow = true
        buildingGroup.add(tier1)

        // Tier 1 Glass Façade Panels
        const t1Glass = new THREE.Mesh(new THREE.BoxGeometry(3.65, 1.6, 3.25), glassMat)
        t1Glass.position.set(0, 1.2, 0)
        buildingGroup.add(t1Glass)

        // Middle Tower Tier (Floors 5-16)
        const tier2 = new THREE.Mesh(new THREE.BoxGeometry(2.6, 3.8, 2.4), steelMat)
        tier2.position.set(0, 4.0, 0)
        tier2.castShadow = true
        buildingGroup.add(tier2)

        const t2Glass = new THREE.Mesh(new THREE.BoxGeometry(2.65, 3.7, 2.45), glassMat)
        t2Glass.position.set(0, 4.0, 0)
        buildingGroup.add(t2Glass)

        // Upper Penthouse Tier (Floors 17-24)
        const tier3 = new THREE.Mesh(new THREE.BoxGeometry(1.8, 2.2, 1.8), glassMat)
        tier3.position.set(0, 7.0, 0)
        tier3.castShadow = true
        buildingGroup.add(tier3)

        // Crown Architectural Angles
        const crown = new THREE.Mesh(new THREE.ConeGeometry(1.2, 1.2, 4), steelMat)
        crown.position.set(0, 8.7, 0)
        crown.rotation.y = Math.PI / 4
        buildingGroup.add(crown)

        // Spire Antenna
        const spire = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.08, 2.0, 8), steelMat)
        spire.position.set(0, 10.1, 0)
        spire.castShadow = true
        buildingGroup.add(spire)

        // Red Flashing Aviation Warning Beacon
        const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 12), beaconMat)
        beacon.position.set(0, 11.1, 0)
        buildingGroup.add(beacon)

        // Internal Floor Slabs / Illuminated Window Bands
        for (let y = 0.6; y <= 7.8; y += 0.6) {
          const slab = new THREE.Mesh(new THREE.BoxGeometry(2.7, 0.04, 2.5), warmLightMat)
          slab.position.set(0, y, 0)
          buildingGroup.add(slab)
        }

        // Surrounding Plaza Elements: Trees and Street Lamps
        const treeWoodMat = regMat(new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.9 }))
        const treeFoliageMat = regMat(new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.6 }))
        const treePositions = [
          [-2.2, -2.2], [2.2, -2.2], [-2.2, 2.2], [2.2, 2.2],
          [-2.2, 0], [2.2, 0]
        ]
        treePositions.forEach(([tx, tz]) => {
          const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.6, 8), treeWoodMat)
          trunk.position.set(tx, 0.6, tz)
          trunk.castShadow = true
          buildingGroup.add(trunk)

          const foliage = new THREE.Mesh(new THREE.DodecahedronGeometry(0.35, 1), treeFoliageMat)
          foliage.position.set(tx, 1.05, tz)
          foliage.castShadow = true
          buildingGroup.add(foliage)
        })

        // Beacon blinking animation
        animatedObjects.push((_d, elapsed) => {
          beacon.visible = Math.sin(elapsed * 4) > 0
        })

        scene.add(buildingGroup)
        controls.target.set(0, 4.5, 0)
      } else if (detectedType === 'tree') {
        // Detailed Nature Foliage Tree
        const natureGroup = new THREE.Group()
        const barkMat = regMat(new THREE.MeshStandardMaterial({ color: 0x451a03, roughness: 0.9 }))
        const leafMat = regMat(new THREE.MeshStandardMaterial({ color: 0x16a34a, roughness: 0.5 }))
        const leafAccentMat = regMat(new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.6 }))
        const grassMat = regMat(new THREE.MeshStandardMaterial({ color: 0x14532d, roughness: 0.8 }))

        // Grass Mound Base
        const mound = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.8, 0.3, 24), grassMat)
        mound.position.y = 0.15
        mound.receiveShadow = true
        natureGroup.add(mound)

        // Tree Trunk
        const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.55, 3.2, 16), barkMat)
        trunk.position.y = 1.6
        trunk.castShadow = true
        natureGroup.add(trunk)

        // Multiple Canopy Foliage Clouds
        const canopyLayers = [
          { y: 3.2, r: 1.4, mat: leafMat },
          { y: 3.8, r: 1.2, mat: leafAccentMat },
          { y: 4.4, r: 1.0, mat: leafMat },
          { y: 4.9, r: 0.7, mat: leafAccentMat },
        ]

        canopyLayers.forEach((layer, idx) => {
          const canopy = new THREE.Mesh(new THREE.DodecahedronGeometry(layer.r, 2), layer.mat)
          canopy.position.set(
            idx % 2 === 0 ? 0.1 : -0.1,
            layer.y,
            idx % 2 === 1 ? 0.1 : -0.1
          )
          canopy.scale.set(1.2, 0.8, 1.2)
          canopy.castShadow = true
          natureGroup.add(canopy)
        })

        // Gentle wind sway animation
        animatedObjects.push((_d, elapsed) => {
          natureGroup.rotation.z = Math.sin(elapsed * 1.5) * 0.02
        })

        scene.add(natureGroup)
        controls.target.set(0, 2.8, 0)
      } else {
        // Default / Custom: Procedural Floating Geometric Orb / Polyhedron
        const geomGroup = new THREE.Group()
        const shapeMat = regMat(new THREE.MeshStandardMaterial({
          color: 0x38bdf8,
          metalness: 0.8,
          roughness: 0.2,
        }))
        const mainMesh = new THREE.Mesh(new THREE.IcosahedronGeometry(1.5, 1), shapeMat)
        mainMesh.position.y = 1.8
        mainMesh.castShadow = true
        geomGroup.add(mainMesh)

        // Outer Rings
        const ringMat = regMat(new THREE.MeshStandardMaterial({ color: 0xa855f7, metalness: 0.9, roughness: 0.1 }))
        const ring1 = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.06, 16, 64), ringMat)
        ring1.position.y = 1.8
        ring1.rotation.x = Math.PI / 3
        geomGroup.add(ring1)

        const ring2 = new THREE.Mesh(new THREE.TorusGeometry(2.6, 0.05, 16, 64), ringMat)
        ring2.position.y = 1.8
        ring2.rotation.y = Math.PI / 4
        geomGroup.add(ring2)

        animatedObjects.push((delta) => {
          mainMesh.rotation.y += delta * 0.5
          mainMesh.rotation.x += delta * 0.3
          ring1.rotation.z += delta * 0.6
          ring2.rotation.x += delta * 0.4
        })

        scene.add(geomGroup)
        controls.target.set(0, 1.8, 0)
      }
    } catch (err: any) {
      console.error('Error constructing 3D scene:', err)
      setError(err?.message || 'Failed to render 3D model')
    }

    // Animation Loop
    let animationFrameId: number
    const clock = new THREE.Clock()

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      const delta = clock.getDelta()
      const elapsed = clock.getElapsedTime()

      animatedObjects.forEach((fn) => fn(delta, elapsed))
      controls.update()
      renderer.render(scene, camera)
    }

    animate()

    // Handle Window Resize
    const handleResize = () => {
      if (!container) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
      controls.dispose()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [detectedType, code])

  // Update OrbitControls autoRotate
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = isAutoRotating
    }
  }, [isAutoRotating])

  // Toggle Wireframe
  useEffect(() => {
    materialsRef.current.forEach((m) => {
      if ('wireframe' in m) {
        ;(m as any).wireframe = isWireframe
      }
    })
  }, [isWireframe])

  // Toggle Grid
  useEffect(() => {
    if (gridHelperRef.current) {
      gridHelperRef.current.visible = showGrid
    }
  }, [showGrid])

  return (
    <div
      className={`my-3 rounded-2xl border border-sky-500/30 bg-[#0a0e14] shadow-2xl overflow-hidden transition-all flex flex-col ${
        isFullscreen ? 'fixed inset-4 z-50 shadow-black' : 'relative w-full max-w-2xl'
      }`}
    >
      {/* 3D Header Controls */}
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-black/60 border-b border-white/10 text-xs backdrop-blur-md select-none">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-sky-500/20 border border-sky-500/40 flex items-center justify-center text-sky-300">
            <Box className="w-3.5 h-3.5 animate-pulse" />
          </div>
          <span className="font-bold text-white tracking-wide">
            {displayTitle}
          </span>
          <span className="px-2 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/30 text-[10px] font-semibold text-sky-300 uppercase tracking-wider">
            Interactive WebGL
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Auto Rotate Toggle */}
          <button
            type="button"
            onClick={() => setIsAutoRotating(!isAutoRotating)}
            title={isAutoRotating ? 'Pause rotation' : 'Start auto-rotation'}
            className={`p-1.5 rounded-xl border text-[11px] transition-all cursor-pointer ${
              isAutoRotating
                ? 'bg-sky-500/20 border-sky-500/50 text-sky-300'
                : 'bg-white/5 border-white/10 text-neutral-400 hover:text-white'
            }`}
          >
            {isAutoRotating ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          {/* Wireframe Toggle */}
          <button
            type="button"
            onClick={() => setIsWireframe(!isWireframe)}
            title={isWireframe ? 'Solid mode' : 'Wireframe mode'}
            className={`p-1.5 rounded-xl border text-[11px] transition-all cursor-pointer ${
              isWireframe
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                : 'bg-white/5 border-white/10 text-neutral-400 hover:text-white'
            }`}
          >
            <Eye className="w-3.5 h-3.5" />
          </button>

          {/* Grid Toggle */}
          <button
            type="button"
            onClick={() => setShowGrid(!showGrid)}
            title={showGrid ? 'Hide grid floor' : 'Show grid floor'}
            className={`p-1.5 rounded-xl border text-[11px] transition-all cursor-pointer ${
              showGrid
                ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
                : 'bg-white/5 border-white/10 text-neutral-400 hover:text-white'
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
          </button>

          {/* Reset View */}
          <button
            type="button"
            onClick={() => resetCameraRef.current()}
            title="Reset camera view"
            className="p-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-neutral-400 hover:text-white transition-all cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Code toggle */}
          <button
            type="button"
            onClick={() => setShowCode(!showCode)}
            title="Toggle source code"
            className={`p-1.5 rounded-xl border text-[11px] transition-all cursor-pointer ${
              showCode
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                : 'bg-white/5 border-white/10 text-neutral-400 hover:text-white'
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
          </button>

          {/* Fullscreen Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit full screen' : 'Expand full screen'}
            className="p-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-neutral-400 hover:text-white transition-all cursor-pointer"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Main View Area: Live Canvas vs Code */}
      <div className="relative w-full flex-1 min-h-[340px] sm:min-h-[420px] bg-[#0a0e14]">
        {showCode ? (
          <div className="p-4 h-full max-h-[440px] overflow-auto font-mono text-xs text-sky-200/90 bg-black/90">
            <pre className="whitespace-pre-wrap">{code}</pre>
          </div>
        ) : (
          <>
            <div ref={mountRef} className="w-full h-full min-h-[340px] sm:min-h-[420px] cursor-grab active:cursor-grabbing" />

            {/* Gesture Hint Pill */}
            <div className="absolute bottom-3 left-3 pointer-events-none px-2.5 py-1 rounded-full bg-black/70 backdrop-blur-md border border-white/10 text-[10px] text-neutral-300 flex items-center gap-1.5 shadow-lg select-none">
              <Sparkles className="w-3 h-3 text-sky-400" />
              <span>Drag to orbit · Scroll to zoom</span>
            </div>
          </>
        )}

        {error && (
          <div className="absolute top-4 left-4 right-4 p-3 rounded-xl bg-rose-950/80 border border-rose-500/40 text-xs text-rose-200">
            {error}
          </div>
        )}
      </div>
    </div>
  )
}
