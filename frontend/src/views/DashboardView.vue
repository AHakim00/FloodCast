<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { fetchNodes, usePolling, type NodeData } from '@/composables/useApi'
import StatsBar from '@/components/StatsBar.vue'
import FloodMap from '@/components/FloodMap.vue'
import HydrographChart from '@/components/HydrographChart.vue'
import AlertFeed from '@/components/AlertFeed.vue'

const { data: nodes, loading: nodesLoading } = usePolling<NodeData[]>(fetchNodes, 30000)

const selectedNodeId = ref<string>('')
const showAll = ref(false)

const nodeList = computed<NodeData[]>(() => nodes.value || [])
const allNodeIds = computed<string[]>(() => nodeList.value.map((n: NodeData) => n.id))

const activeNode = computed<NodeData | null>(() => {
  return nodeList.value.find((n: NodeData) => n.id === selectedNodeId.value) || nodeList.value[0] || null
})

watch(nodeList, (newNodes) => {
  if (newNodes.length > 0 && !selectedNodeId.value && newNodes[0]) {
    selectedNodeId.value = newNodes[0].id
  }
}, { immediate: true })

function handleSelectNode(nodeId: string) {
  selectedNodeId.value = nodeId
  const chartEl = document.getElementById('hydrograph-section')
  if (chartEl) {
    chartEl.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}
</script>

<template>
  <div class="dashboard-root">
    <!-- Top KPI Row -->
    <section class="section-kpi">
      <StatsBar />
    </section>

    <!-- Map & Alert Stream Grid -->
    <section class="section-geospatial">
      <div class="map-column">
        <FloodMap
          :nodes="nodeList"
          @select-node="handleSelectNode"
        />
      </div>
      <div class="alert-column">
        <AlertFeed />
      </div>
    </section>

    <!-- Hydrograph & Telemetry Section -->
    <section id="hydrograph-section" class="section-hydrograph">
      <!-- Control Toolbar -->
      <div class="toolbar card">
        <div class="toolbar-left">
          <div class="control-group">
            <span class="control-label">Monitoring Node</span>
            <div class="select-wrapper">
              <select
                id="node-select"
                v-model="selectedNodeId"
                class="node-select"
                :disabled="showAll"
              >
                <option value="" disabled>Select target node...</option>
                <option
                  v-for="node in nodeList"
                  :key="node.id"
                  :value="node.id"
                >
                  {{ node.name }} [{{ node.id }}]
                </option>
              </select>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="select-chevron">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </div>
          </div>

          <div v-if="activeNode && !showAll" class="node-meta-pills">
            <span class="meta-tag">
              <span class="meta-dot" :class="`dot--${activeNode.status}`"></span>
              {{ activeNode.status.toUpperCase() }}
            </span>
            <span class="meta-coords">
              {{ activeNode.latitude.toFixed(4) }}°N, {{ activeNode.longitude.toFixed(4) }}°E
            </span>
          </div>
        </div>

        <div class="toolbar-right">
          <label class="toggle-control" title="Overlay hydrographs of all nodes on a single chart">
            <input
              type="checkbox"
              v-model="showAll"
              class="toggle-checkbox"
            />
            <span class="toggle-label">Multi-Node Overlay Mode</span>
          </label>
        </div>
      </div>

      <!-- Hydrograph Chart Component -->
      <HydrographChart
        v-if="selectedNodeId || showAll"
        :node-id="selectedNodeId || (nodeList[0]?.id ?? '')"
        :all-node-ids="showAll ? allNodeIds : undefined"
      />
    </section>
  </div>
</template>

<style scoped>
.dashboard-root {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── KPI Row ── */
.section-kpi {
  width: 100%;
}

/* ── Geospatial Grid: Map 65% + Alerts 35% ── */
.section-geospatial {
  display: grid;
  grid-template-columns: 1.8fr 1fr;
  gap: 16px;
}

@media (max-width: 1100px) {
  .section-geospatial {
    grid-template-columns: 1fr;
  }
}

.map-column {
  min-width: 0;
}

.alert-column {
  display: flex;
  align-items: flex-start;
  min-width: 0;
  min-height: 0;
}

/* ── Hydrograph Section ── */
.section-hydrograph {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ── Toolbar ── */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: var(--color-bg-surface);
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-dim);
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.select-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.node-select {
  appearance: none;
  background: var(--color-bg-input);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 6px 32px 6px 12px;
  font-size: 0.8rem;
  font-family: var(--font-sans);
  font-weight: 500;
  cursor: pointer;
  min-width: 260px;
  transition: all 0.15s ease;
}

.node-select:hover:not(:disabled) {
  border-color: var(--color-border-focus);
}

.node-select:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px rgba(74, 124, 255, 0.15);
}

.node-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.select-chevron {
  position: absolute;
  right: 10px;
  width: 14px;
  height: 14px;
  color: var(--color-text-dim);
  pointer-events: none;
}

.node-meta-pills {
  display: flex;
  align-items: center;
  gap: 8px;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  background: var(--color-bg-raised);
  border: 1px solid var(--color-border-subtle);
  color: var(--color-text-secondary);
}

.meta-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.meta-coords {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--color-text-dim);
}

/* ── Toggle Control ── */
.toolbar-right {
  display: flex;
  align-items: center;
}

.toggle-control {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}

.toggle-checkbox {
  width: 15px;
  height: 15px;
  accent-color: var(--color-accent);
  cursor: pointer;
}

.toggle-label {
  font-size: 0.78rem;
  color: var(--color-text-secondary);
  font-weight: 500;
}
</style>
