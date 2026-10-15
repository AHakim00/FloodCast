<script setup lang="ts">
import { ref } from 'vue'
import DashboardView from '@/views/DashboardView.vue'

const sidebarOpen = ref(true)
const logoLoaded = ref(true)
const baseUrl = import.meta.env.BASE_URL
const apiBaseUrl = (import.meta.env.VITE_API_URL as string | undefined) || ''
const isProduction = import.meta.env.PROD
const docsUrl = apiBaseUrl ? `${apiBaseUrl.replace(/\/$/, '')}/docs` : `${baseUrl}docs/`
const healthUrl = apiBaseUrl ? `${apiBaseUrl.replace(/\/$/, '')}/health` : `${baseUrl}health/`
const geoJsonViewerUrl = apiBaseUrl
  ? `${apiBaseUrl.replace(/\/$/, '')}/api/v1/flood-depth/view`
  : (isProduction ? `${baseUrl}flood-depth/` : '/api/v1/flood-depth/view')
</script>

<template>
  <div class="shell" :class="{ collapsed: !sidebarOpen }">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-head">
        <div class="brand-badge" title="Bimage Consulting">
          <template v-if="logoLoaded">
            <img
              :src="`${baseUrl}Bimage.png`"
              alt="Bimage Consulting"
              class="brand-logo brand-logo-full"
              @error="logoLoaded = false"
            />
            <img
              :src="`${baseUrl}Bimage-mark.png`"
              alt="Bimage Consulting"
              class="brand-logo brand-logo-mark"
            />
          </template>
          <svg
            v-else
            class="logo-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
          </svg>
        </div>
      </div>

      <nav class="sidebar-nav">
        <a class="nav-link active" href="#">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          <span v-show="sidebarOpen">Dashboard</span>
        </a>
        <a class="nav-link" :href="geoJsonViewerUrl" target="_blank">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>
          <span v-show="sidebarOpen">GeoJSON API</span>
        </a>
        <a class="nav-link" :href="docsUrl" target="_blank">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>
          <span v-show="sidebarOpen">API Docs</span>
        </a>
        <a class="nav-link" :href="healthUrl" target="_blank">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          <span v-show="sidebarOpen">Health</span>
        </a>
      </nav>

      <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <polyline v-if="sidebarOpen" points="15 18 9 12 15 6"/>
          <polyline v-else points="9 18 15 12 9 6"/>
        </svg>
      </button>
    </aside>

    <!-- Main -->
    <main class="main">
      <header class="topbar">
        <div>
          <h1 class="topbar-title">Flood Live Forecast</h1>

          <!-- Change from harcoded location to dynamic -->
          <p class="topbar-sub">Kuching, Sarawak &mdash; Real-time Monitoring</p>
        </div>
      </header>
      <div class="content">
        <DashboardView />
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
.sidebar {
  width: 220px;
  background: var(--color-bg-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.2s ease;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
}
.collapsed .sidebar { width: 56px; }

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 14px 12px;
  border-bottom: 1px solid var(--color-border-subtle);
  min-height: 64px;
}

.brand-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 8px 12px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
  transition: all 0.2s ease;
}

.brand-logo {
  object-fit: contain;
  display: block;
}

.brand-logo-full {
  width: 100%;
  height: 38px;
  max-width: 175px;
}

.brand-logo-mark {
  display: none;
  width: 28px;
  height: 28px;
}

.collapsed .sidebar-head {
  padding: 12px 6px;
}

.collapsed .brand-badge {
  width: 40px;
  height: 40px;
  padding: 5px;
  border-radius: 8px;
  overflow: hidden;
}

.collapsed .brand-logo-full {
  display: none;
}

.collapsed .brand-logo-mark {
  display: block;
}

.logo-icon {
  width: 24px;
  height: 24px;
  color: #0a0e1a;
  flex-shrink: 0;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.12s ease;
}

.nav-link svg { width: 18px; height: 18px; flex-shrink: 0; }
.nav-link:hover { color: var(--color-text); background: var(--color-bg-raised); }
.nav-link.active {
  color: var(--color-accent);
  background: rgba(74, 124, 255, 0.08);
}

.sidebar-toggle {
  margin: 8px;
  padding: 6px;
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.12s;
}
.sidebar-toggle svg { width: 16px; height: 16px; }
.sidebar-toggle:hover { color: var(--color-text); border-color: var(--color-border-focus); }

/* ── Main ────────────────────────────────────────────────────────────────── */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow-y: auto;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-root);
  position: sticky;
  top: 0;
  z-index: 5;
}

.topbar-title {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.topbar-sub {
  font-size: 0.78rem;
  color: var(--color-text-dim);
  margin-top: 1px;
}

.content {
  flex: 1;
  padding: 20px 24px 32px;
}

@media (max-width: 768px) {
  .sidebar { position: fixed; left: 0; top: 0; bottom: 0; z-index: 50; }
  .collapsed .sidebar { width: 0; border: none; }
  .content { padding: 14px; }
  .topbar { padding: 14px 16px; }
}
</style>
