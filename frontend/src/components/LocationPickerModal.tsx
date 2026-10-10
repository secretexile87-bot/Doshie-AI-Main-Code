import React, { useState, useEffect } from 'react'
import { MapPin, X, Search, Compass, Check, Loader2 } from 'lucide-react'
import type { ClientLocation } from './ChatComposer'

interface LocationPickerModalProps {
  isOpen: boolean
  currentLocation?: ClientLocation | null
  onClose: () => void
  onSelectLocation: (loc: ClientLocation) => void
}

const COMMON_CITIES = [
  'El Paso, TX',
  'Dallas, TX',
  'Austin, TX',
  'Houston, TX',
  'San Antonio, TX',
  'Phoenix, AZ',
  'Albuquerque, NM',
  'Denver, CO',
  'Los Angeles, CA',
  'New York, NY',
]

export const LocationPickerModal: React.FC<LocationPickerModalProps> = ({
  isOpen,
  currentLocation,
  onClose,
  onSelectLocation,
}) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Array<{ name: string; latitude: number; longitude: number }>>([])
  const [isSearching, setIsSearching] = useState(false)
  const [isDetectingIp, setIsDetectingIp] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen) {
      setQuery('')
      setResults([])
      setErrorMsg(null)
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return

    setIsSearching(true)
    setErrorMsg(null)
    try {
      const res = await fetch(`/api/location/search?q=${encodeURIComponent(trimmed)}`)
      const data = await res.json()
      if (data.results && data.results.length > 0) {
        setResults(data.results)
      } else {
        // Fallback: accept the entered text directly as city
        onSelectLocation({
          name: trimmed,
          city: trimmed,
          latitude: 0,
          longitude: 0,
        })
        onClose()
      }
    } catch {
      onSelectLocation({
        name: trimmed,
        city: trimmed,
        latitude: 0,
        longitude: 0,
      })
      onClose()
    } finally {
      setIsSearching(false)
    }
  }

  const handleUseIpLocation = async () => {
    setIsDetectingIp(true)
    setErrorMsg(null)
    try {
      const res = await fetch('/api/location/ip')
      const data = await res.json()
      if (data.ok && data.name) {
        onSelectLocation({
          name: data.name,
          city: data.city,
          region: data.region,
          country: data.country,
          latitude: data.latitude || 0,
          longitude: data.longitude || 0,
        })
        onClose()
      } else {
        setErrorMsg('Could not detect location from network IP.')
      }
    } catch {
      setErrorMsg('Failed to reach network location service.')
    } finally {
      setIsDetectingIp(false)
    }
  }

  const handleSelectResult = (item: { name: string; latitude: number; longitude: number }) => {
    // Clean up long Nominatim display names
    const parts = item.name.split(',').map(s => s.trim())
    const shortName = parts.length >= 2 ? `${parts[0]}, ${parts[1]}` : parts[0]
    onSelectLocation({
      name: shortName,
      city: parts[0],
      region: parts[1],
      latitude: item.latitude,
      longitude: item.longitude,
    })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md bg-[#0d1612] border border-emerald-500/30 rounded-3xl p-5 shadow-2xl text-white">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <MapPin className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Set Your Location</h3>
              <p className="text-[11px] text-neutral-400">For accurate weather and local queries</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-white/10 text-neutral-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current Location Badge */}
        {currentLocation && (
          <div className="mt-3 px-3 py-2 rounded-xl bg-emerald-950/40 border border-emerald-500/20 text-xs flex items-center justify-between">
            <span className="text-neutral-300">
              Active: <strong className="text-emerald-300">{currentLocation.name}</strong>
            </span>
            <span className="text-[10px] text-emerald-400 font-mono">Current</span>
          </div>
        )}

        {/* Detect Network IP Button */}
        <div className="mt-3">
          <button
            type="button"
            onClick={handleUseIpLocation}
            disabled={isDetectingIp}
            className="w-full py-2.5 px-3 rounded-2xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 hover:text-white flex items-center justify-center gap-2 text-xs font-semibold transition-all cursor-pointer disabled:opacity-50"
          >
            {isDetectingIp ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Detecting Network Location...</span>
              </>
            ) : (
              <>
                <Compass className="w-3.5 h-3.5 text-emerald-400" />
                <span>Auto-Detect Location (Network IP)</span>
              </>
            )}
          </button>
        </div>

        {errorMsg && (
          <p className="mt-2 text-xs text-rose-400 text-center">{errorMsg}</p>
        )}

        {/* Search City Form */}
        <form onSubmit={handleSearch} className="mt-4">
          <label className="block text-[11px] font-semibold text-neutral-300 uppercase tracking-wider mb-1.5">
            Or Type Your City
          </label>
          <div className="relative flex items-center">
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. El Paso, TX or Dallas"
              className="w-full pl-9 pr-16 py-2.5 rounded-2xl bg-black/40 border border-white/15 focus:border-emerald-400 focus:outline-none text-sm text-white placeholder-neutral-500"
            />
            <Search className="w-4 h-4 text-neutral-400 absolute left-3 pointer-events-none" />
            <button
              type="submit"
              disabled={!query.trim() || isSearching}
              className="absolute right-1.5 px-3 py-1 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-neutral-950 text-xs font-bold transition-all disabled:opacity-40 cursor-pointer"
            >
              {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Set'}
            </button>
          </div>
        </form>

        {/* Search Results */}
        {results.length > 0 && (
          <div className="mt-3 max-h-40 overflow-y-auto space-y-1.5 pr-1">
            {results.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectResult(item)}
                className="w-full text-left px-3 py-2 rounded-xl bg-white/5 hover:bg-emerald-500/15 border border-white/10 hover:border-emerald-500/40 text-xs text-neutral-200 transition-all flex items-center justify-between cursor-pointer"
              >
                <span className="truncate pr-2">{item.name}</span>
                <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              </button>
            ))}
          </div>
        )}

        {/* Quick Common Presets */}
        <div className="mt-4 pt-3 border-t border-white/10">
          <span className="text-[10px] uppercase tracking-wider font-semibold text-neutral-400 block mb-2">
            Quick Cities
          </span>
          <div className="flex flex-wrap gap-1.5">
            {COMMON_CITIES.map(city => (
              <button
                key={city}
                type="button"
                onClick={() => {
                  onSelectLocation({
                    name: city,
                    city: city.split(',')[0].trim(),
                    latitude: 0,
                    longitude: 0,
                  })
                  onClose()
                }}
                className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-emerald-500/20 border border-white/10 hover:border-emerald-500/40 text-[11px] text-neutral-300 hover:text-white transition-all cursor-pointer"
              >
                {city}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
