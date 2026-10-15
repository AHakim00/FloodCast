<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkLineComponent,
  DataZoomComponent,
  ToolboxComponent,
} from 'echarts/components'
import { fetchNodeForecast, type ForecastData } from '@/composables/useApi'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkLineComponent,
  DataZoomComponent,
  ToolboxComponent,
])

const props = defineProps<{
  nodeId: string
  allNodeIds?: string[]
}>()

const loading = ref(true)
const forecasts = ref<Map<string, ForecastData>>(new Map())

async function loadData() {
  loading.value = true
  const nodeIds = props.allNodeIds && props.allNodeIds.length > 0
    ? props.allNodeIds
    : [props.nodeId]

  const newForecasts = new Map<string, ForecastData>()

  for (const id of nodeIds) {
    if (!id) continue
    try {
      const data = await fetchNodeForecast(id)
      newForecasts.set(id, data)
    } catch (e) {
      console.error(`Failed to fetch telemetry for node ${id}:`, e)
    }
  }

  forecasts.value = newForecasts
  loading.value = false
}

// Total readings count across loaded forecasts
const hasReadings = computed(() => {
  if (forecasts.value.size === 0) return false
  for (const f of forecasts.value.values()) {
    if (f.readings && f.readings.length > 0) return true
  }
  return false
})

// Current active single node forecast
const activeForecast = computed(() => {
  if (props.allNodeIds && props.allNodeIds.length > 0) return null
  return forecasts.value.get(props.nodeId) || null
})

// Metrics for single node view
const metrics = computed(() => {
  const f = activeForecast.value
  if (!f || f.readings.length === 0) return null
  const levels = f.readings.map(r => r.water_level)
  const max = Math.max(...levels)
  const min = Math.min(...levels)
  const latest = levels[levels.length - 1]
  return {
    latest,
    max,
    min,
    alert: f.alert_threshold,
    warning: f.warning_threshold,
    danger: f.danger_threshold,
    count: f.readings.length
  }
})

const chartOption = computed(() => {
  if (forecasts.value.size === 0) return {}

  // const colorPalette = ['#28A745', '#FFC107', '#FD7E14', '#DC3545', '#4a7cff']
  const colorPalette = ['#4a7cff', '#38bdd2', '#a855f7', '#f59e0b', '#10b981']
  const series: any[] = []
  let alertVal = 2.0
  let warningVal = 3.0
  let dangerVal = 4.0
  let idx = 0

  forecasts.value.forEach((forecast, nodeId) => {
    alertVal = forecast.alert_threshold
    warningVal = forecast.warning_threshold
    dangerVal = forecast.danger_threshold
    const c = colorPalette[idx % colorPalette.length]

    series.push({
      name: forecast.node_name || nodeId,
      type: 'line',
      smooth: true,
      showSymbol: false,
      symbolSize: 6,
      data: forecast.readings.map((r) => [r.timestamp, r.water_level]),
      lineStyle: { width: 2, color: c },
      itemStyle: { color: c },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: c + '28' },
            { offset: 1, color: c + '02' },
          ],
        },
      },
      markLine: idx === 0 ? {
        silent: false,
        symbol: 'none',
        lineStyle: { width: 1.5 },
        data: [
          {
            yAxis: alertVal,
            name: 'Alert Level',
            label: {
              formatter: `Alert (${alertVal.toFixed(1)}m)`,
              position: 'insideEndTop',
              color: '#f2ff39',
              fontSize: 11,
              fontFamily: 'JetBrains Mono',
              fontWeight: 400,
            },
            lineStyle: { color: '#f2ff39', type: 'dashed' },
          },
          {
            yAxis: warningVal,
            name: 'Warning Level',
            label: {
              formatter: `Warning (${warningVal.toFixed(1)}m)`,
              position: 'insideEndTop',
              color: '#FD7E14',
              fontSize: 11,
              fontFamily: 'JetBrains Mono',
              fontWeight: 500,
            },
            lineStyle: { color: '#FD7E14', type: 'dashed' },
          },
          {
            yAxis: dangerVal,
            name: 'Danger Level',
            label: {
              formatter: `Danger (${dangerVal.toFixed(1)}m)`,
              position: 'insideEndTop',
              color: '#DC3545',
              fontSize: 11,
              fontFamily: 'JetBrains Mono',
              fontWeight: 600,
            },
            lineStyle: { color: '#DC3545', type: 'dashed' },
          },
        ],
      } : undefined,
    })
    idx++
  })

  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'Inter, -apple-system, sans-serif' },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1c1f2b',
      borderColor: '#2a2e3a',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: '#e2e4ea', fontSize: 12 },
      formatter: (params: any) => {
        if (!Array.isArray(params) || params.length === 0) return ''
        const d = new Date(params[0].value[0])
        const timeStr = d.toLocaleString('en-GB', {
          day: '2-digit', month: 'short', year: 'numeric',
          hour: '2-digit', minute: '2-digit'
        })
        let html = `<div style="font-family:'JetBrains Mono';font-size:11px;color:#8b8fa3;margin-bottom:8px;border-bottom:1px solid #2a2e3a;padding-bottom:4px;">${timeStr}</div>`
        params.forEach((p: any) => {
          html += `
            <div style="display:flex;align-items:center;justify-content:space-between;gap:16px;margin:4px 0;">
              <span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#8b8fa3;">
                <span style="width:7px;height:7px;border-radius:50%;background:${p.color};"></span>
                ${p.seriesName}
              </span>
              <span style="font-family:'JetBrains Mono';font-weight:600;color:#e2e4ea;font-size:12px;">
                ${p.value[1].toFixed(3)} m
              </span>
            </div>
          `
        })
        return html
      },
    },
    legend: {
      top: 0,
      right: 120,
      textStyle: { color: '#8b8fa3', fontSize: 12 },
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
    },
    grid: {
      left: 54,
      right: 60,
      top: 36,
      bottom: 60,
      containLabel: false,
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#2a2e3a' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#5c6178',
        fontSize: 11,
        fontFamily: 'JetBrains Mono',
        formatter: (val: string) => {
          const d = new Date(val)
          return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}\n${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
        },
      },
      splitLine: {
        show: true,
        lineStyle: { color: '#1c1f2b', type: 'dashed' },
      },
    },
    yAxis: {
      type: 'value',
      name: 'Stage Height (m)',
      nameTextStyle: { color: '#5c6178', fontSize: 11, padding: [0, 0, 6, 0] },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#5c6178',
        fontSize: 11,
        fontFamily: 'JetBrains Mono',
        formatter: '{value} m',
      },
      splitLine: {
        show: true,
        lineStyle: { color: '#1c1f2b' },
      },
    },
    dataZoom: [
      {
        type: 'slider',
        bottom: 8,
        height: 24,
        backgroundColor: '#161921',
        borderColor: '#2a2e3a',
        fillerColor: 'rgba(74, 124, 255, 0.12)',
        handleStyle: { color: '#4a7cff', borderColor: '#4a7cff' },
        textStyle: { color: '#5c6178', fontFamily: 'JetBrains Mono', fontSize: 10 },
        dataBackground: {
          lineStyle: { color: '#2a2e3a' },
          areaStyle: { color: '#1c1f2b' },
        },
      },
      { type: 'inside' },
    ],
    toolbox: {
      right: 10,
      top: 0,
      iconStyle: { borderColor: '#5c6178' },
      emphasis: { iconStyle: { borderColor: '#e2e4ea' } },
      feature: {
        restore: { title: 'Reset Zoom' },
        saveAsImage: { title: 'Export PNG', name: 'hydrograph_telemetry' },
      },
    },
    series,
  }
})

onMounted(loadData)
watch(() => props.nodeId, loadData)
watch(() => props.allNodeIds, loadData, { deep: true })
</script>

<template>
  <div class="chart-panel card">
    <!-- Telemetry Status Bar for Active Node -->
    <div class="chart-panel-header">
      <div class="telemetry-info">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="chart-header-icon">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span class="chart-heading">Hydrograph Telemetry & Stage Forecast</span>
      </div>

      <div v-if="metrics" class="quick-metrics">
        <div class="metric-item">
          <span class="m-label">Peak</span>
          <span class="m-val">{{ metrics.max.toFixed(2) }}m</span>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <span class="m-label">Min</span>
          <span class="m-val">{{ metrics.min.toFixed(2) }}m</span>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <span class="m-label">Alert Thresh</span>
          <span class="m-val text-alert">{{ metrics.alert.toFixed(1) }}m</span>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <span class="m-label">Warning Thresh</span>
          <span class="m-val text-warn">{{ metrics.warning.toFixed(1) }}m</span>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <span class="m-label">Danger Thresh</span>
          <span class="m-val text-danger">{{ metrics.danger.toFixed(1) }}m</span>
        </div>
      </div>
    </div>

    <div class="chart-body">
      <div v-if="loading" class="chart-loading">
        <div class="loading-pulse">Loading simulation data...</div>
      </div>

      <!-- No Data / Standby State -->
      <div v-else-if="!hasReadings" class="chart-standby">
        <div class="standby-box">
          <div class="standby-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" class="icon-svg">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <line x1="3" y1="9" x2="21" y2="9"/>
              <line x1="9" y1="21" x2="9" y2="9"/>
            </svg>
          </div>
          <div class="standby-title">Hydrograph Standby Mode</div>
          <p class="standby-text">
            Simulation records have not yet been imported. Ingest hourly forecast CSV exports into
            <code>./data/exports/</code> to plot simulated water surface elevations.
          </p>
        </div>
      </div>

      <v-chart
        v-else
        :option="chartOption"
        :autoresize="true"
        class="echarts-view"
      />
    </div>
  </div>
</template>

<style scoped>
.chart-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
  flex-wrap: wrap;
  gap: 10px;
}

.telemetry-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-header-icon {
  width: 16px;
  height: 16px;
  color: var(--color-accent);
}

.chart-heading {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-text);
}

.quick-metrics {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--color-bg-raised);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  padding: 4px 12px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.m-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  color: var(--color-text-dim);
  letter-spacing: 0.04em;
}

.m-val {
  font-family: var(--font-mono);
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--color-text);
}

.metric-divider {
  width: 1px;
  height: 12px;
  background: var(--color-border);
}


.text-alert { color: var(--color-alert); }
.text-warn { color: var(--color-warn); }
.text-danger { color: var(--color-danger); }

.chart-body {
  padding: 16px;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.echarts-view {
  width: 100%;
  height: 400px;
}

.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 380px;
  width: 100%;
  color: var(--color-text-dim);
  font-size: 0.85rem;
}

.loading-pulse {
  animation: blink 1.5s infinite ease-in-out;
}

.chart-standby {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 380px;
}

.standby-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 440px;
}

.standby-icon {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  background: var(--color-bg-raised);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.icon-svg {
  width: 20px;
  height: 20px;
  color: var(--color-text-dim);
}

.standby-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
}

.standby-text {
  font-size: 0.78rem;
  color: var(--color-text-dim);
  line-height: 1.5;
}

.standby-text code {
  font-family: var(--font-mono);
  background: var(--color-bg-raised);
  border: 1px solid var(--color-border);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--color-text-secondary);
}
</style>
