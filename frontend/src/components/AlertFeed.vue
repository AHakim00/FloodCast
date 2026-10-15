// ─── Active Alert Feed Component ──────────────────────────────────────────────
<script setup lang="ts">

// Importing Vue's reactive and computed functions
import { computed } from 'vue'

// Importing composables for fetching active alerts and polling
import { fetchActiveAlerts, fetchNodes, usePolling, type AlertListData, type AlertData, type NodeData } from '@/composables/useApi'

// Edit this config to control which nodes and node details appear in the feed.
const displayConfig = {
  nodeIds: [] as string[],
  fields: {
    level: true,
    status: true,
    thresholds: true,
  },
}

// Polling for active alerts every 30 seconds
const { data: alertData, loading } = usePolling<AlertListData>(fetchActiveAlerts, 30000)
const { data: nodeData, loading: nodesLoading } = usePolling<NodeData[]>(fetchNodes, 30000)

const PRIORITY_ORDER: Record<string, number> = {
  danger: 0,
  critical: 0,
  severe: 0,
  warning: 1,
  moderate: 1,
  alert: 2,
  watch: 2,
  info: 3,
  normal: 4,
}

// Computed properties for alerts and total active count
const alerts = computed(() => {
  const availableAlerts = alertData.value?.alerts || []
  const filteredAlerts = displayConfig.nodeIds.length === 0
    ? availableAlerts
    : availableAlerts.filter(
      (alert) => !alert.target_id || displayConfig.nodeIds.includes(alert.target_id),
    )

  return [...filteredAlerts].sort((a, b) => {
    const priorityDifference = (PRIORITY_ORDER[(a.priority || '').toLowerCase()] ?? 99)
      - (PRIORITY_ORDER[(b.priority || '').toLowerCase()] ?? 99)
    if (priorityDifference !== 0) return priorityDifference

    const onsetA = a.onset_time ? Date.parse(a.onset_time) || 0 : 0
    const onsetB = b.onset_time ? Date.parse(b.onset_time) || 0 : 0
    return onsetB - onsetA
  })
})
const nodes = computed(() => {
  const availableNodes = nodeData.value || []
  if (displayConfig.nodeIds.length === 0) return availableNodes
  return availableNodes.filter((node) => displayConfig.nodeIds.includes(node.id))
})

// Computed property for total active alerts
const totalActive = computed(() => alerts.value.length)
const highestAlertPriority = computed(() =>
  alerts.value.length > 0 ? alerts.value[0]?.priority || 'info' : null,
)
const highestNodeStatus = computed(() =>
  [...nodes.value]
    .map((node) => node.status)
    .sort((a, b) => (PRIORITY_ORDER[a] ?? 99) - (PRIORITY_ORDER[b] ?? 99))[0] ?? null,
)
const headerPriority = computed(() => highestAlertPriority.value || highestNodeStatus.value)
const headerPriorityType = computed(() => {
  if (!headerPriority.value || headerPriority.value === 'normal') return 'ok'
  return getPriorityType(headerPriority.value)
})
const headerStatusText = computed(() => {
  if (highestAlertPriority.value) {
    return `${highestAlertPriority.value.toUpperCase()} · ${totalActive.value} Active`
  }
  if (highestNodeStatus.value && highestNodeStatus.value !== 'normal') {
    return `${highestNodeStatus.value.toUpperCase()} Node Status`
  }
  return highestNodeStatus.value ? 'Normal Status' : 'No Status Data'
})

function getNodeName(targetId: string | null): string {
  if (!targetId) return 'System-wide'
  return nodes.value.find((node) => node.id === targetId)?.name || targetId
}

// Function to format ISO timestamp strings into a human-readable format
function formatTime(isoStr: string | null): string {
  if (!isoStr) return '—'
  const d = new Date(isoStr)

  // Formatting the date to a more readable format (e.g., "01 Jan, 12:00")
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// NEED TO ADD ALERT PRIORITY COLOR CODING FOR THE ALERT FEED PANEL
// Function to determine the priority type for styling based on the alert's priority
/*function getPriorityType(priority: string | null): 'danger' | 'warn' | 'muted' {
  const p = (priority || '').toLowerCase()
  if (p === 'critical' || p === 'alert' || p === 'severe') return 'danger'
  if (p === 'warning' || p === 'moderate' || p === 'watch') return 'warn'
  return 'muted'
}*/

function getPriorityType(priority: string | null): 'danger' | 'warn' | 'alert' | 'muted' {
  const p = (priority || '').toLowerCase()
  if (p === 'danger' || p === 'critical' || p === 'severe') return 'danger'
  if (p === 'warning' || p === 'moderate') return 'warn'
  if (p === 'alert' || p === 'watch') return 'alert'
  return 'muted'
}
</script>

<template>
  <div class="alert-panel card">
    <div class="panel-header">
      <div class="panel-title-wrap">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="panel-icon">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <span class="panel-title">Active Alert Stream</span>
      </div>
      <div class="header-status">
        <span class="tag" :class="`tag--${headerPriorityType}`">
          <span class="dot" :class="`dot--${headerPriorityType}`"></span>
          {{ headerStatusText }}
        </span>
      </div>
    </div>

    <div class="panel-body">
      <!-- Loading Skeleton -->
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 3" :key="i" class="alert-skeleton"></div>
      </div>

      <!-- Empty State: Operational Normal -->
      <!--
      <div v-else-if="alerts.length === 0" class="all-clear-state">
        <div class="shield-icon-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" class="shield-icon">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <polyline points="9 12 11 14 15 10"/>
          </svg>
        </div>
        <div class="all-clear-title">Zero Active Alert Thresholds</div>
        <p class="all-clear-desc">
          No active alert definitions. Current readings and threshold status are shown below.
        </p>
      </div> -->

      <!-- Alert List -->
      <div v-else class="alert-items">
        <div
          v-for="alert in alerts"
          :key="alert.alert_definition_id"
          class="alert-entry"
          :class="`alert-entry--${getPriorityType(alert.priority)}`"
        >
          <div class="entry-top">
            <span class="tag" :class="`tag--${getPriorityType(alert.priority)}`">
              {{ alert.priority || 'ADVISORY' }}
            </span>
            <span v-if="alert.category" class="entry-category">{{ alert.category }}</span>
            <span class="entry-id">{{ alert.alert_definition_id }}</span>
          </div>

          <div class="entry-details">
            <div class="target-row">
              <span class="field-label">Target:</span>
              <span class="target-id">{{ getNodeName(alert.target_id) }}</span>
              <span v-if="alert.target_id" class="target-type">({{ alert.target_id }})</span>
              <span v-if="alert.target_type" class="target-type">({{ alert.target_type }})</span>
            </div>

            <div class="time-window">
              <div class="time-block">
                <span class="time-label">Onset</span>
                <span class="time-val">{{ formatTime(alert.onset_time) }}</span>
              </div>
              <span class="time-divider">&rarr;</span>
              <div class="time-block">
                <span class="time-label">End</span>
                <span class="time-val">{{ formatTime(alert.end_time) }}</span>
              </div>
            </div>

            <div v-if="alert.peak_value !== null" class="peak-block">
              <span class="field-label">Forecast Peak:</span>
              <span class="peak-val">
                {{ alert.peak_value.toFixed(3) }}
                <span class="peak-unit">{{ alert.peak_value_units || 'm' }}</span>
              </span>
              <span v-if="alert.peak_time" class="peak-timestamp">
                at {{ formatTime(alert.peak_time) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Monitored Nodes  -->
      <section class="node-status-section" aria-label="Monitored node status">
        <div class="node-status-heading">
          <span>Monitored Nodes</span>
          <span class="node-count">{{ nodes.length }}</span>
        </div>

        <div v-if="nodesLoading && nodes.length === 0" class="node-status-empty">
          Loading node readings...
        </div>
        <div v-else-if="nodes.length === 0" class="node-status-empty">
          No node readings are available.
        </div>
        <div v-else class="node-status-list">
          <div v-for="node in nodes" :key="node.id" class="node-status-row">
            <div class="node-status-top">
              <span v-if="displayConfig.fields.status" class="node-status-dot" :class="`node-status-dot--${node.status}`"></span>
              <span class="node-name">{{ node.name }}</span>
              <span v-if="displayConfig.fields.status" class="node-status-tag" :class="`node-status-tag--${node.status}`">
                {{ node.status }}
              </span>
            </div>
            <div class="node-status-details">
              <span class="node-id">{{ node.id }}</span>
              <span v-if="displayConfig.fields.level" class="node-level">
                {{ node.current_water_level === null ? 'No current reading' : `${node.current_water_level.toFixed(2)} m` }}
              </span>
              <span v-if="displayConfig.fields.thresholds" class="node-thresholds">
                Alert {{ node.alert_threshold.toFixed(1) }} / Warning {{ node.warning_threshold.toFixed(1) }} / Danger {{ node.danger_threshold.toFixed(1) }} m
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.alert-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: auto;
  max-height: 600px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
}

.panel-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-icon {
  width: 16px;
  height: 16px;
  color: var(--color-text-secondary);
}

.panel-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.01em;
}

.panel-body {
  flex: 0 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: 14px;
}

/* ── All Clear Empty State ── */
.all-clear-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 150px;
  text-align: center;
  padding: 24px 16px;
}

.shield-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-ok-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.shield-icon {
  width: 22px;
  height: 22px;
  color: var(--color-ok);
}

.all-clear-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
}

.all-clear-desc {
  font-size: 0.78rem;
  color: var(--color-text-dim);
  max-width: 280px;
  line-height: 1.5;
}

/* ── Alert Items ── */
.alert-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-entry {
  background: var(--color-bg-raised);
  border: 1px solid var(--color-border);
  border-left-width: 3px;
  border-radius: var(--radius-sm);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert-entry--danger { border-left-color: var(--color-danger); }
.alert-entry--alert { border-left-color: var(--color-alert); }
.alert-entry--warn { border-left-color: var(--color-warn); }
.alert-entry--muted { border-left-color: var(--color-accent); }

/*
.alert-entry--danger { border-left-color: var(--color-danger); }
.alert-entry--warn { border-left-color: var(--color-warn); }
.alert-entry--muted { border-left-color: var(--color-accent); }
*/

.entry-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.entry-category {
  font-size: 0.72rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.entry-id {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--color-text-dim);
}

.entry-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.78rem;
}

.target-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.field-label {
  color: var(--color-text-dim);
  font-size: 0.72rem;
}

.target-id {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--color-text);
}

.target-type {
  font-size: 0.7rem;
  color: var(--color-text-dim);
}

.time-window {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
}

.time-block {
  display: flex;
  flex-direction: column;
}

.time-label {
  font-size: 0.62rem;
  text-transform: uppercase;
  color: var(--color-text-dim);
  letter-spacing: 0.05em;
}

.time-val {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--color-text-secondary);
}

.time-divider {
  color: var(--color-text-dim);
  font-size: 0.8rem;
}

.peak-block {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding-top: 4px;
  border-top: 1px dashed var(--color-border-subtle);
}

.peak-val {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--color-danger);
}

.peak-unit {
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--color-text-dim);
}

.peak-timestamp {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-text-dim);
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-skeleton {
  height: 90px;
  background: var(--color-bg-raised);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
}

.node-status-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-subtle);
}

.node-status-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  color: var(--color-text-secondary);
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
}

.node-count,
.node-id,
.node-thresholds {
  color: var(--color-text-dim);
  font-family: var(--font-mono);
  font-size: 0.66rem;
  font-weight: 400;
  text-transform: none;
}

.node-status-empty {
  padding: 10px 0;
  color: var(--color-text-dim);
  font-size: 0.74rem;
}

.node-status-row {
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.node-status-top,
.node-status-details {
  display: flex;
  align-items: center;
  gap: 7px;
}

.node-status-top {
  min-width: 0;
}

.node-name {
  min-width: 0;
  overflow: hidden;
  color: var(--color-text);
  font-size: 0.75rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-status-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 50%;
}

.node-status-dot--normal { background: var(--color-ok); }
.node-status-dot--alert { background: var(--color-alert); }
.node-status-dot--warning { background: var(--color-warn); }
.node-status-dot--danger { background: var(--color-danger); }

.node-status-tag {
  margin-left: auto;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.62rem;
  font-weight: 600;
  text-transform: uppercase;
}

.node-status-tag--normal { color: var(--color-ok); background: var(--color-ok-dim); }
.node-status-tag--alert { color: var(--color-alert); background: rgba(242, 255, 57, 0.1); }
.node-status-tag--warning { color: var(--color-warn); background: rgba(230, 160, 32, 0.12); }
.node-status-tag--danger { color: var(--color-danger); background: rgba(220, 53, 69, 0.12); }

.node-status-details {
  flex-wrap: wrap;
  margin: 4px 0 0 14px;
}

.node-level {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: 0.68rem;
}
</style>
