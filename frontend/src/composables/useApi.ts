/**
 * API client composable — fetches data from the FastAPI backend.
 * Supports normal API mode and static demo mode for GitHub Pages.
 */

import { ref, onMounted, onUnmounted, type Ref } from 'vue'

import {
  fetchDemoReadings,
  fetchDemoContour,
} from '@/services/demoData'

// ─── Configuration ──────────────────────────────────────────────────────────

const API_BASE = '/api/v1'
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

// ─── Types ──────────────────────────────────────────────────────────────────

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

export interface WaterLevelReading {
  timestamp: string
  seconds: number | null
  water_level: number
}

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

export interface AlertListData {
  alerts: AlertData[]
  total_active: number
}

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

export interface ContourGeoJSON {
  type: string
  features: Array<{
    type: string
    geometry: any
    properties: GeoJSONFeatureProperties
  }>
}

export interface ContourFrameMeta {
  timestep: string | null
  label: string | null
  date: string | null
  filename: string
}

// ─── Fallback Nodes ─────────────────────────────────────────────────────────

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
    status: 'alert',
  },
  {
    id: 'Drain_53',
    name: 'Drain 53 - Sungai Sarawak',
    latitude: 1.5601,
    longitude: 110.3422,
    node_type: '1D_Channel',
    alert_threshold: 2.2,
    warning_threshold: 3.2,
    danger_threshold: 4.2,
    current_water_level: 1.85,
    status: 'normal',
  },
]

// ─── Fallback Dashboard Summary ──────────────────────────────────────────────

const FALLBACK_SUMMARY: DashboardSummaryData = {
  total_nodes: 2,
  active_alerts: 0,
  latest_update: '01 Sept 2026, 07:09',
  max_water_level: 2.78,
  max_water_level_node: 'Drain_46',
  max_water_level_time: null,
  nodes_in_alert: 1,
  nodes_in_warning: 0,
  nodes_in_danger: 0,
}

// ─── Fallback Forecast ──────────────────────────────────────────────────────

function getFallbackForecast(nodeId: string): ForecastData {
  const isDrain46 = nodeId === 'Drain_46'

  const times = [
    '09:30',
    '10:30',
    '11:30',
    '12:30',
    '13:30',
    '14:30',
    '15:30',
    '16:30',
    '17:30',
  ]

  const readings: WaterLevelReading[] = times.map((time, index) => {
    const baseLevel = isDrain46 ? 1.35 : 1.15
    const peak = isDrain46 ? 1.43 : 0.8

    const level =
      baseLevel +
      Math.sin((index / (times.length - 1)) * Math.PI) * peak

    return {
      timestamp: `2026-09-01T${time}:00`,
      seconds: index * 3600,
      water_level: Number(level.toFixed(2)),
    }
  })

  return {
    node_id: nodeId,
    node_name: isDrain46
      ? 'Drain 46 - Sungai Padungan'
      : 'Drain 102 - Sungai Sarawak',
    latitude: isDrain46 ? 1.5535 : 1.5601,
    longitude: isDrain46 ? 110.3485 : 110.3422,
    alert_threshold: isDrain46 ? 2.0 : 2.2,
    warning_threshold: isDrain46 ? 3.0 : 3.2,
    danger_threshold: isDrain46 ? 4.0 : 4.2,
    readings,
    total_readings: readings.length,
  }
}

// ─── Fallback Contours ───────────────────────────────────────────────────────

const FALLBACK_TIMESTEPS = [
  '0930',
  '1030',
  '1130',
  '1230',
  '1330',
  '1430',
  '1530',
  '1630',
  '1730',
]

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
            [110.342, 1.558],
          ],
        ],
      },
      properties: {
        Zone: 'Padungan Inundation Zone',
        Depth: 0.84,
        depth: 0.84,
        Elevation: 3.25,
        elevation: 3.25,
        Hazard: 'MEDIUM',
        timestep_label: '13:30',
      },
    },
  ],
}

// ─── Fallback API Handler ───────────────────────────────────────────────────

function getFallbackData(
  path: string,
  params?: Record<string, string>,
): any {
  if (path.endsWith('/nodes')) {
    return FALLBACK_NODES
  }

  if (path.endsWith('/node-forecast')) {
    return getFallbackForecast(params?.node_id || 'Drain_46')
  }

  if (path.endsWith('/alerts/active')) {
    return {
      alerts: [],
      total_active: 0,
    }
  }

  if (path.endsWith('/dashboard/summary')) {
    return FALLBACK_SUMMARY
  }

  if (path.endsWith('/contours/timesteps')) {
    return FALLBACK_TIMESTEPS
  }

  if (path.endsWith('/contours/metadata')) {
    return {
      frames: [],
    }
  }

  if (path.endsWith('/contours/has-maxima')) {
    return {
      available: true,
      timestep: 'maxima',
      filename: 'FloodContours_260826_Maxima.geojson',
    }
  }

  if (path.includes('/contours/')) {
    return FALLBACK_GEOJSON
  }

  return undefined
}

// ─── Demo Mode Data Cache ───────────────────────────────────────────────────

type DemoReadings = Awaited<ReturnType<typeof fetchDemoReadings>>

let cachedDemoReadings: DemoReadings | null = null

async function getDemoReadings(): Promise<DemoReadings> {
  if (cachedDemoReadings === null) {
    const readings = await fetchDemoReadings()

    if (readings.length === 0) {
      throw new Error('No demo readings found in the CSV file.')
    }

    cachedDemoReadings = readings
  }

  return cachedDemoReadings
}

// ─── Demo Mode Helpers ───────────────────────────────────────────────────────

type DemoSensorId = 'Drain_46' | 'Drain_53'

const DEMO_SENSOR_IDS = ['Drain_46', 'Drain_53']
// const DEMO_SENSOR_IDS: DemoSensorId[] = ['Drain_46', 'Drain_53']

function isDemoSensorId(value: string): value is DemoSensorId {
  return DEMO_SENSOR_IDS.includes(value as DemoSensorId)
}

function getSensorReadings(
  readings: DemoReadings,
  nodeId: string,
): WaterLevelReading[] {
  if (!isDemoSensorId(nodeId)) {
    throw new Error(`No demo CSV data configured for ${nodeId}.`)
  }

  return readings.map((row) => ({
    timestamp: new Date(
      `${row.Time.replace(' ', 'T')}+08:00`,
    ).toISOString(),
    seconds: row.Seconds,
    water_level: row[nodeId],
  }))
}

function getSensorMetadata(nodeId: string): NodeData {
  const node = FALLBACK_NODES.find((item) => item.id === nodeId)

  if (!node) {
    throw new Error(
      `Metadata for ${nodeId} is unavailable. Configure its verified coordinates and thresholds before displaying it as a map node.`,
    )
  }

  return node
}

function getStatus(
  level: number,
  node: NodeData,
): NodeData['status'] {
  if (level >= node.danger_threshold) return 'danger'
  if (level >= node.warning_threshold) return 'warning'
  if (level >= node.alert_threshold) return 'alert'

  return 'normal'
}

function getLatestLevel(
  readings: DemoReadings,
  nodeId: string,
): number {
  const latest = readings[readings.length - 1]

  if (!latest) {
    throw new Error('No demo readings found in the CSV file.')
  }

  if (!isDemoSensorId(nodeId)) {
    throw new Error(`No demo CSV data configured for ${nodeId}.`)
  }

  return latest[nodeId]
}

// ─── Demo Mode API Handler ───────────────────────────────────────────────────

async function getDemoData(
  path: string,
  params?: Record<string, string>,
): Promise<unknown> {
  // Return contour data without loading the CSV.
  if (path.endsWith('/contours/timesteps')) {
    return ['1800']
  }

  if (path.endsWith('/contours/metadata')) {
    return {
      frames: [
        {
          timestep: '1800',
          label: '18:00',
          date: '2026-08-26',
          filename: 'FloodContours_260826_1800.geojson',
        },
      ],
    } satisfies { frames: ContourFrameMeta[] }
  }

  if (path.endsWith('/contours/has-maxima')) {
    return {
      available: true,
      timestep: 'maxima',
      filename: 'FloodContours_260826_Maxima.geojson',
    }
  }

  if (path.includes('/contours/')) {
    const timestamp = path.split('/').pop() || ''

    return await fetchDemoContour(timestamp)
  }

  // Load the CSV only for endpoints that need water-level readings.
  const readings = await getDemoReadings()

  // GET /api/v1/nodes
  if (path.endsWith('/nodes')) {
    return DEMO_SENSOR_IDS
      .filter((id) => FALLBACK_NODES.some((node) => node.id === id))
      .map((id) => {
        const node = getSensorMetadata(id)
        const level = getLatestLevel(readings, id)

        return {
          ...node,
          current_water_level: level,
          status: getStatus(level, node),
        }
      })
  }

  // GET /api/v1/node-forecast?node_id=Drain_46
  if (path.endsWith('/node-forecast')) {
    const nodeId = params?.node_id || 'Drain_46'
    const node = getSensorMetadata(nodeId)
    const sensorReadings = getSensorReadings(readings, nodeId)

    return {
      node_id: nodeId,
      node_name: node.name,
      latitude: node.latitude,
      longitude: node.longitude,
      alert_threshold: node.alert_threshold,
      warning_threshold: node.warning_threshold,
      danger_threshold: node.danger_threshold,
      readings: sensorReadings,
      total_readings: sensorReadings.length,
    } satisfies ForecastData
  }

  // GET /api/v1/dashboard/summary
  if (path.endsWith('/dashboard/summary')) {
    const availableNodes = DEMO_SENSOR_IDS
      .filter((id) => FALLBACK_NODES.some((node) => node.id === id))
      .map((id) => {
        const node = getSensorMetadata(id)
        const level = getLatestLevel(readings, id)

        return {
          node,
          level,
          status: getStatus(level, node),
        }
      })

    let maxLevel = -Infinity
    let maxNode: string | null = null
    let maxTime: string | null = null

    for (const nodeId of DEMO_SENSOR_IDS) {
      for (const reading of readings) {
        const level = reading[nodeId]

        if (level > maxLevel) {
          maxLevel = level
          maxNode = nodeId
          maxTime = reading.Time
        }
      }
    }

    return {
      total_nodes: availableNodes.length,
      active_alerts: availableNodes.filter(
        (item) => item.status !== 'normal',
      ).length,
      latest_update: readings[readings.length - 1]?.Time ?? null,
      max_water_level: Number.isFinite(maxLevel) ? maxLevel : null,
      max_water_level_node: maxNode,
      max_water_level_time: maxTime,
      nodes_in_alert: availableNodes.filter(
        (item) => item.status === 'alert',
      ).length,
      nodes_in_warning: availableNodes.filter(
        (item) => item.status === 'warning',
      ).length,
      nodes_in_danger: availableNodes.filter(
        (item) => item.status === 'danger',
      ).length,
    } satisfies DashboardSummaryData
  }

  // GET /api/v1/alerts/active
  if (path.endsWith('/alerts/active')) {
    const alerts: AlertData[] = []
    const latestReading = readings[readings.length - 1]

    if (!latestReading) {
      return {
        alerts,
        total_active: 0,
      } satisfies AlertListData
    }

    for (const nodeId of DEMO_SENSOR_IDS) {
      const node = FALLBACK_NODES.find((item) => item.id === nodeId)

      // Do not create map-related alerts for sensors without verified metadata.
      if (!node) continue

      const level = getLatestLevel(readings, nodeId)
      const status = getStatus(level, node)

      if (status === 'normal') continue

      alerts.push({
        alert_definition_id: `DEMO-${nodeId}`,
        onset_time: latestReading.Time,
        end_time: null,
        priority: status.toUpperCase(),
        target_id: nodeId,
        target_type: 'NODE',
        category: 'Water Level',
        peak_value: level,
        peak_value_units: 'm',
        peak_time: latestReading.Time,
        is_active: true,
      })
    }

    return {
      alerts,
      total_active: alerts.length,
    } satisfies AlertListData
  }

  throw new Error(`No demo data handler configured for ${path}.`)
}

// ─── Generic API Fetch Wrapper ──────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  params?: Record<string, string>,
): Promise<T> {
  const configuredApiBase =
    (import.meta.env.VITE_API_URL as string | undefined) || ''

  // Static GitHub Pages demo mode never calls the FastAPI backend.
  if (DEMO_MODE) {
    return (await getDemoData(path, params)) as T
  }

  let targetUrl: string

  if (configuredApiBase.startsWith('http')) {
    const cleanPath = path.startsWith(API_BASE)
      ? path.slice(API_BASE.length)
      : path

    const base = configuredApiBase.replace(/\/$/, '')
    const url = new URL(`${base}${API_BASE}${cleanPath}`)

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.set(key, value)
        }
      })
    }

    targetUrl = url.toString()
  } else {
    const url = new URL(path, window.location.origin)

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          url.searchParams.set(key, value)
        }
      })
    }

    targetUrl = url.toString()
  }

  try {
    const response = await fetch(targetUrl)

    if (!response.ok) {
      throw new Error(
        `API Error: ${response.status} ${response.statusText}`,
      )
    }

    return (await response.json()) as T
  } catch (error) {
    const fallback = getFallbackData(path, params)

    if (fallback !== undefined) {
      return fallback as T
    }

    throw error
  }
}

// ─── API Functions ──────────────────────────────────────────────────────────

export async function fetchNodes(): Promise<NodeData[]> {
  return apiFetch<NodeData[]>(`${API_BASE}/nodes`)
}

export async function fetchNodeForecast(
  nodeId: string,
): Promise<ForecastData> {
  return apiFetch<ForecastData>(
    `${API_BASE}/node-forecast`,
    { node_id: nodeId },
  )
}

export async function fetchActiveAlerts(): Promise<AlertListData> {
  return apiFetch<AlertListData>(`${API_BASE}/alerts/active`)
}

export async function fetchDashboardSummary(): Promise<DashboardSummaryData> {
  return apiFetch<DashboardSummaryData>(
    `${API_BASE}/dashboard/summary`,
  )
}

export async function fetchContourTimesteps(): Promise<string[]> {
  return apiFetch<string[]>(`${API_BASE}/contours/timesteps`)
}

export async function fetchContourGeoJSON(
  timestamp: string,
): Promise<ContourGeoJSON> {
  return apiFetch<ContourGeoJSON>(
    `${API_BASE}/contours/${timestamp}`,
  )
}

export async function fetchContourMetadata(): Promise<{
  frames: ContourFrameMeta[]
}> {
  return apiFetch<{ frames: ContourFrameMeta[] }>(
    `${API_BASE}/contours/metadata`,
  )
}

export async function checkHasMaxima(): Promise<{
  available: boolean
  timestep: string | null
  filename: string | null
}> {
  return apiFetch(`${API_BASE}/contours/has-maxima`)
}

// ─── Polling Composable ─────────────────────────────────────────────────────

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  intervalMs: number = 60000,
) {
  const data: Ref<T | null> = ref(null)
  const loading = ref(true)
  const error = ref<string | null>(null)

  let timer: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    try {
      error.value = null
      data.value = await fetchFn()
    } catch (caughtError: unknown) {
      error.value =
        caughtError instanceof Error
          ? caughtError.message
          : 'Unknown error'

      console.error('Polling error:', caughtError)
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void refresh()
    timer = setInterval(() => {
      void refresh()
    }, intervalMs)
  })

  onUnmounted(() => {
    if (timer !== null) {
      clearInterval(timer)
    }
  })

  return {
    data,
    loading,
    error,
    refresh,
  }
}
