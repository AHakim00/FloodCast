<script setup lang="ts">
import { computed } from 'vue'
import { fetchDashboardSummary, usePolling, type DashboardSummaryData } from '@/composables/useApi'

const { data: summary, loading } = usePolling<DashboardSummaryData>(fetchDashboardSummary, 30000)

const alertPriority = computed(() => {
  if (!summary.value) return 'normal'
  if (summary.value.nodes_in_danger > 0) return 'danger'
  if (summary.value.nodes_in_warning > 0) return 'warning'
  if (summary.value.nodes_in_alert > 0) return 'alert'
  return summary.value.active_alerts > 0 ? 'alert' : 'normal'
})

const alertPriorityLabel = computed(() => {
  if (!summary.value) return ''
  if (summary.value.nodes_in_danger > 0) return `${summary.value.nodes_in_danger} node in danger`
  if (summary.value.nodes_in_warning > 0) return `${summary.value.nodes_in_warning} node in warning`
  if (summary.value.nodes_in_alert > 0) return `${summary.value.nodes_in_alert} node in alert`
  return summary.value.active_alerts > 0 ? 'Active alert targets' : 'No active alerts'
})

// Computed property to format the latest update timestamp for display
const formattedUpdate = computed(() => {
  // If there's no latest update timestamp, return a placeholder
  if (!summary.value?.latest_update) return 'Awaiting data'
  const d = new Date(summary.value.latest_update)
  return d.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
})
</script>


<template>
  <div class="kpi-row">
    <div v-if="loading" v-for="i in 4" :key="i" class="kpi skeleton"></div>
    <template v-else-if="summary">
      <!-- Nodes -->
      <div class="kpi card">
        <div class="kpi-icon kpi-icon--blue">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        </div>
        <div class="kpi-body">
          <span class="kpi-label">Monitoring Nodes</span>
          <span class="kpi-value">{{ summary.total_nodes }}</span>
        </div>
      </div>

      <!-- Alerts -->
      <div class="kpi card">
        <div class="kpi-icon" :class="`kpi-icon--${alertPriority}`">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div class="kpi-body">
          <span class="kpi-label">Active Alerts</span>
          <span class="kpi-value" :class="`text-${alertPriority}`">{{ summary.active_alerts }}</span>
          <span class="kpi-sub">{{ alertPriorityLabel }}</span>
        </div>
      </div>

      <!-- Max Level -->
      <div class="kpi card">
        <div class="kpi-icon kpi-icon--cyan">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
        </div>
        <div class="kpi-body">
          <span class="kpi-label">Peak Level</span>
          <span class="kpi-value">
            <template v-if="summary.max_water_level !== null">{{ summary.max_water_level.toFixed(2) }}<small class="unit">m</small></template>
            <template v-else>&mdash;</template>
          </span>
          <span v-if="summary.max_water_level_node" class="kpi-sub">{{ summary.max_water_level_node }}</span>
        </div>
      </div>

      <!-- Updated -->
      <div class="kpi card">
        <div class="kpi-icon kpi-icon--muted">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        </div>
        <div class="kpi-body">
          <span class="kpi-label">Last Updated</span>
          <span class="kpi-value kpi-value--sm">{{ formattedUpdate }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 1100px) { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px)  { .kpi-row { grid-template-columns: 1fr; } }

.kpi {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
}

.skeleton {
  height: 72px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.kpi-icon {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.kpi-icon svg { width: 18px; height: 18px; }

.kpi-icon--blue  { background: rgba(74, 124, 255, 0.10); color: #4a7cff; }
.kpi-icon--normal { background: var(--color-ok-dim); color: var(--color-ok); }
.kpi-icon--danger { background: var(--color-danger-dim); color: var(--color-danger); }
.kpi-icon--warning { background: rgba(253, 126, 20, 0.12); color: var(--color-warn); }
.kpi-icon--alert { background: rgba(255, 193, 7, 0.12); color: var(--color-alert); }
.kpi-icon--cyan  { background: rgba(56, 189, 210, 0.10);  color: #38bdd2; }
.kpi-icon--muted { background: var(--color-bg-overlay);   color: var(--color-text-dim); }

.kpi-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.kpi-label {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.kpi-value {
  font-size: 1.3rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
}
.kpi-value--sm { font-size: 0.9rem; font-weight: 600; }

.kpi-sub {
  font-size: 0.68rem;
  color: var(--color-text-dim);
  font-family: var(--font-mono);
  margin-top: 1px;
}

.text-danger { color: var(--color-danger); }
.text-warning { color: var(--color-warn); }
.text-alert { color: var(--color-alert); }

.unit {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-dim);
  margin-left: 2px;
}
</style>
