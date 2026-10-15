/**
 * Helpers that tie node markers to the map timeline.
 *
 * The contour frames are named by time (e.g. "1400") and the forecast readings
 * carry full timestamps, so each frame is matched to the node reading at that
 * time. Pure functions only (no Vue) so they are easy to test.
 */
import type { NodeData, WaterLevelReading } from '@/composables/useApi'

/** A node as displayed for the selected frame (level, status and time follow the timeline). */
export interface ShownNode extends NodeData {
  shown_at: string | null   // timestamp of the reading being shown (null = latest value)
  level_label: string       // 'Level' or 'Peak level'
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Severity order: normal < alert < warning < danger (same rule as the backend). */
export function computeNodeStatus(
  level: number | null,
  n: Pick<NodeData, 'alert_threshold' | 'warning_threshold' | 'danger_threshold'>,
): NodeData['status'] {
  if (level === null) return 'normal'
  if (level >= n.danger_threshold) return 'danger'
  if (level >= n.warning_threshold) return 'warning'
  if (level >= n.alert_threshold) return 'alert'
  return 'normal'
}

/** '260826' -> '2026-08-26', '20260911' -> '2026-09-11', anything else -> null */
export function normaliseFrameDate(raw: string | null | undefined): string | null {
  if (!raw) return null
  if (/^\d{6}$/.test(raw)) return `20${raw.slice(0, 2)}-${raw.slice(2, 4)}-${raw.slice(4, 6)}`
  if (/^\d{8}$/.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
  return null
}

// Timestamps are naive local times ("2026-10-12T14:00:00"); slice them as text
// so no time-zone conversion can shift the hour.
function minutesOfDay(ts: string): number {
  return Number(ts.slice(11, 13)) * 60 + Number(ts.slice(14, 16))
}

/** Reading closest in time-of-day to `target` minutes (max 30 min away). Later dates win ties. */
function nearest(readings: WaterLevelReading[], target: number): WaterLevelReading | null {
  let best: WaterLevelReading | null = null
  let bestDiff = 31
  for (const r of readings) {
    const diff = Math.abs(minutesOfDay(r.timestamp) - target)
    if (diff <= bestDiff) {
      best = r
      bestDiff = diff
    }
  }
  return best
}

/**
 * Reading that matches a timeline frame such as "1400".
 * Prefers the same calendar date as the contour file; if the forecast covers a
 * different date (e.g. demo data), falls back to the same time of day.
 */
export function readingForFrame(
  readings: WaterLevelReading[],
  frameKey: string,
  frameDate: string | null,
): WaterLevelReading | null {
  if (!/^\d{4}$/.test(frameKey) || readings.length === 0) return null
  const target = Number(frameKey.slice(0, 2)) * 60 + Number(frameKey.slice(2))
  if (frameDate) {
    const sameDay = nearest(readings.filter((r) => r.timestamp.slice(0, 10) === frameDate), target)
    if (sameDay) return sameDay
  }
  return nearest(readings, target)
}

/** Highest reading in the forecast (used for the Maxima / peak envelope view). */
export function peakReading(readings: WaterLevelReading[]): WaterLevelReading | null {
  let peak: WaterLevelReading | null = null
  for (const r of readings) {
    if (peak === null || r.water_level > peak.water_level) peak = r
  }
  return peak
}

/** '2026-10-12T14:00:00' -> '12 Oct 14:00' */
export function formatShownAt(ts: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(ts)
  if (!m) return ts
  return `${m[3]} ${MONTHS[Number(m[2]) - 1] ?? ''} ${m[4]}:${m[5]}`
}