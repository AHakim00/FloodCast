/**
API client composable — fetches data from the FastAPI backend.
Handles base URL, polling, and error states.
*/

import { ref, onMounted, onUnmounted, type Ref } from 'vue'

const API_BASE = '/api/v1'

// ─── Fallback Demo Data for Static Deployment (GitHub Pages) ─────────────────
// Returns fallback node data for the dashboard, used when the fetch fails (e.g., due to CORS or network issues).
const FALLBACK_NODES: NodeData[] = [
  {
    id: 'Drain_46',
    name: 'Drain 46 - Sungai Padungan',
    latitude: 1.5535,
    longitude: 110.3485,
    node_type: '2D_Inundation',
    alert_threshold: 2.0,
    warning_threshold: 3.0,
    danger_threshold: 4.0,
    current_water_level: 2.78,
    status: 'alert'
  },
  {
    id: 'Drain_102',
    name: 'Drain 102 - Sungai Sarawak',
    latitude: 1.5601,
    longitude: 110.3422,
    node_type: '1D_Channel',
    alert_threshold: 2.2,
    warning_threshold: 3.2,
    danger_threshold: 4.2,
    current_water_level: 1.85,
    status: 'normal'
  }
]

// Returns fallback summary data for the dashboard, used when the fetch fails (e.g., due to CORS or network issues).
const FALLBACK_SUMMARY: DashboardSummaryData = {
  total_nodes: 2,
  active_alerts: 0,
  latest_update: '01 Sept 2026, 07:09',
  max_water_level: 2.78,
  max_water_level_node: 'Drain_46',
  max_water_level_time: null,
  nodes_in_alert: 1,
  nodes_in_warning: 0,
  nodes_in_danger: 0
}

// Returns fallback forecast data for a specific node, used when the fetch fails (e.g., due to CORS or network issues).
function getFallbackForecast(nodeId: string): ForecastData {
  const isDrain46 = nodeId === 'Drain_46'
  const times = ['09:30', '10:30', '11:30', '12:30', '13:30', '14:30', '15:30', '16:30', '17:30']
  const readings: WaterLevelReading[] = times.map((t, idx) => {
    const baseLevel = isDrain46 ? 1.35 : 1.15
    const peak = isDrain46 ? 1.43 : 0.8
    const val = baseLevel + Math.sin((idx / (times.length - 1)) * Math.PI) * peak
    return {
      timestamp: `2026-09-01T${t}:00`,
      seconds: idx * 3600,
      water_level: parseFloat(val.toFixed(2))
    }
  })
  return {
    node_id: nodeId,
    node_name: isDrain46 ? 'Drain 46 - Sungai Padungan' : 'Drain 102 - Sungai Sarawak',
    latitude: isDrain46 ? 1.5535 : 1.5601,
    longitude: isDrain46 ? 110.3485 : 110.3422,
    alert_threshold: isDrain46 ? 2.0 : 2.2,
    warning_threshold: isDrain46 ? 3.0 : 3.2,
    danger_threshold: isDrain46 ? 4.0 : 4.2,
    readings,
    total_readings: readings.length
  }
}

// ─── Fallback Contour Timesteps for Static Deployment (GitHub Pages) ─────────
const FALLBACK_TIMESTEPS = ['0930', '1030', '1130', '1230', '1330', '1430', '1530', '1630', '1730']

// ─── Fallback Contour GeoJSON for Static Deployment (GitHub Pages) ─────────
const FALLBACK_GEOJSON: ContourGeoJSON = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [110.342, 1.558],
            [110.347, 1.556],
            [110.352, 1.553],
            [110.350, 1.550],
            [110.344, 1.552],
            [110.340, 1.555],
            [110.342, 1.558]
          ]
        ]
      },
      properties: {
        Zone: 'Padungan Inundation Zone',
        Depth: 0.84,
        depth: 0.84,
        Elevation: 3.25,
        elevation: 3.25,
        Hazard: 'MEDIUM',
        timestep_label: '13:30'
      }
    }
  ]
}

// Returns fallback data for specific API paths, used when the fetch fails (e.g., due to CORS or network issues).
function getFallbackData(path: string, params?: Record<string, string>): any {
  if (path.includes('/nodes')) return FALLBACK_NODES
  if (path.includes('/node-forecast')) {
    const id = params?.node_id || 'Drain_46'
    return getFallbackForecast(id)
  }
  if (path.includes('/alerts/active')) return { alerts: [], total_active: 0 }
  if (path.includes('/dashboard/summary')) return FALLBACK_SUMMARY
  if (path.includes('/contours/timesteps')) return FALLBACK_TIMESTEPS
  if (path.includes('/contours/metadata')) return { frames: [] }
  if (path.includes('/contours/has-maxima')) return { available: true, timestep: 'maxima', filename: 'FloodContours_260826_maxima.shp' }
  if (path.includes('/contours/')) return FALLBACK_GEOJSON
  return undefined
}

// Generic fetch wrapper with error handling and static demo fallback.
// If the fetch fails (e.g., due to CORS or network issues), it will return fallback data for demo purposes.
async function apiFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const configuredApiBase = (import.meta.env.VITE_API_URL as string | undefined) || ''

  // Construct the full URL based on the configured API base and the provided path and parameters.
  let targetUrl: string
  if (configuredApiBase && configuredApiBase.startsWith('http')) {
    const cleanPath = path.startsWith('/api/v1') ? path.replace('/api/v1', '') : path
    const url = new URL(configuredApiBase.replace(/\/$/, '') + '/api/v1' + cleanPath)
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          url.searchParams.set(k, v)
        }
      })
    }
    targetUrl = url.toString()
  } else {
    // If no configured API base, use relative path with current origin
    const url = new URL(path, window.location.origin)
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          url.searchParams.set(k, v)
        }
      })
    }
    targetUrl = url.toString()
  }

  // Attempt to fetch data from the backend API. If it fails, use fallback demo data.
  try {
    const response = await fetch(targetUrl)
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }
    return await response.json()
  } catch (err) {
    const fallback = getFallbackData(path, params)
    if (fallback !== undefined) {
      return fallback as T
    }
    throw err
  }
}

// ─── Types ───────────────────────────────────────────────────────────────────
// Node Data Type
export interface NodeData {
  id: string
  name: string
  latitude: number
  longitude: number
  node_type: string
  alert_threshold: number
  warning_threshold: number
  danger_threshold: number
  current_water_level: number | null
  status: 'normal' | 'alert' | 'warning' | 'danger'
}

// ─── Water Level Reading Type ─────────────────────────────────────────────
export interface WaterLevelReading {
  timestamp: string
  seconds: number | null
  water_level: number
}

// ─── Forecast Types ───────────────────────────────────────────────────────
export interface ForecastData {
  node_id: string
  node_name: string
  latitude: number
  longitude: number
  alert_threshold: number
  warning_threshold: number
  danger_threshold: number
  readings: WaterLevelReading[]
  total_readings: number
}

// ─── Alert & Dashboard Types ───────────────────────────────────────────────
export interface AlertData {
  alert_definition_id: string
  onset_time: string | null
  end_time: string | null
  priority: string | null
  target_id: string | null
  target_type: string | null
  category: string | null
  peak_value: number | null
  peak_value_units: string | null
  peak_time: string | null
  is_active: boolean
}

// ─── Contour GeoJSON Types ───────────────────────────────────────────────
export interface AlertListData {
  alerts: AlertData[]
  total_active: number
}

// ─── Dashboard Summary Types ─────────────────────────────────────────────
export interface DashboardSummaryData {
  total_nodes: number
  active_alerts: number
  latest_update: string | null
  max_water_level: number | null
  max_water_level_node: string | null
  max_water_level_time: string | null
  nodes_in_alert: number
  nodes_in_warning: number
  nodes_in_danger: number
}

// ─── Contour GeoJSON Types ─────────────────────────────────────────────
export interface GeoJSONFeatureProperties {
  Zone?: string
  Depth?: number
  depth?: number
  Elevation?: number
  elevation?: number
  MaxDepth?: number
  Hazard?: string
  Timestep?: string
  timestep?: string
  timestep_label?: string
  [key: string]: any
}

// ─── Contour GeoJSON Types ─────────────────────────────────────────────
export interface ContourGeoJSON {
  type: string
  features: Array<{
    type: string
    geometry: any
    properties: GeoJSONFeatureProperties
  }>
}

/// ─── API Functions ──────────────────────────────────────────────────────────
// Fetches the list of nodes from the backend API.
export async function fetchNodes(): Promise<NodeData[]> {
  return apiFetch<NodeData[]>(`${API_BASE}/nodes`)
}

// Fetches the forecast data for a specific node by its ID.
export async function fetchNodeForecast(nodeId: string): Promise<ForecastData> {
  return apiFetch<ForecastData>(`${API_BASE}/node-forecast`, { node_id: nodeId })
}

// Fetches the list of active alerts from the backend API.
export async function fetchActiveAlerts(): Promise<AlertListData> {
  return apiFetch<AlertListData>(`${API_BASE}/alerts/active`)
}

// Fetches the dashboard summary data from the backend API.
export async function fetchDashboardSummary(): Promise<DashboardSummaryData> {
  return apiFetch<DashboardSummaryData>(`${API_BASE}/dashboard/summary`)
}

// Fetches the list of available contour timesteps from the backend API.
export async function fetchContourTimesteps(): Promise<string[]> {
  return apiFetch<string[]>(`${API_BASE}/contours/timesteps`)
}

// Fetches the contour GeoJSON data for a specific timestamp from the backend API.
export async function fetchContourGeoJSON(timestamp: string): Promise<ContourGeoJSON> {
  return apiFetch<ContourGeoJSON>(`${API_BASE}/contours/${timestamp}`)
}

// Metadata for each contour frame (includes the frame date from the file name).
export interface ContourFrameMeta {
  timestep: string | null
  label: string | null
  date: string | null
  filename: string
}

export async function fetchContourMetadata(): Promise<{ frames: ContourFrameMeta[] }> {
  return apiFetch<{ frames: ContourFrameMeta[] }>(`${API_BASE}/contours/metadata`)
}

// Checks if the maxima contour data is available and retrieves its details.
export async function checkHasMaxima(): Promise<{ available: boolean; timestep: string | null; filename: string | null }> {
  return apiFetch<{ available: boolean; timestep: string | null; filename: string | null }>(`${API_BASE}/contours/has-maxima`)
}

// ─── Polling Composable ─────────────────────────────────────────────────────
// This composable provides a polling mechanism to repeatedly fetch data at a specified interval.
export function usePolling<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number = 60000
) 
{
  // Reactive references to hold the fetched data, loading state, and any error messages.
  const data: Ref<T | null> = ref(null)
  const loading = ref(true)
  const error = ref<string | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null
  
  async function refresh() {
    try {
      error.value = null
      data.value = await fetchFn()
    } catch (e: any) {
      error.value = e.message || 'Unknown error'
      console.error('Polling error:', e)
    } finally {
      loading.value = false
    }
  }

  // Start polling when the component is mounted and set up the interval for refreshing data.
  onMounted(() => {
    refresh()
    timer = setInterval(refresh, intervalMs)
  })

  // Clear the polling interval when the component is unmounted to prevent memory leaks.
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  // Return the reactive references and the refresh function for use in components.
  return { data, loading, error, refresh }
}
