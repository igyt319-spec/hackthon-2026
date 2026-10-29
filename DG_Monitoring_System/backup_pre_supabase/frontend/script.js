/**
 * GENIUS DG — INTELLIGENT GENERATOR MONITORING SYSTEM
 * Enterprise Frontend Application Controller
 * High-performance SPA routing, dynamic Chart.js visualizations,
 * REST API client, alert lifecycle manager, and telemetry drawers.
 */

// API Configuration
const API_BASE_URL = (window.location.protocol === 'file:' || !window.location.port || window.location.port === '5500')
  ? 'http://localhost:5000/api'
  : '/api';

// Enterprise Application State
const state = {
  activePage: 'overview',
  currency: '₹',
  dieselPrice: 94.50,
  emissionFactor: 2.68,
  delayThreshold: 10.0,
  contaminationRate: 0.08,
  filters: {
    dgId: 'ALL',
    startDate: '2026-05-01',
    endDate: '2026-10-31'
  },
  recordsPagination: {
    page: 1,
    perPage: 15,
    search: '',
    sortBy: 'date',
    sortOrder: 'desc'
  },
  alertsFilter: {
    status: 'ALL',
    severity: 'ALL',
    type: 'ALL'
  },
  charts: {},
  backendHealthy: false,
  cachedAlerts: [],
  cachedGenerators: []
};

// ============================================================================
// 1. INITIALIZATION & LIFECYCLE
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initNavigation();
  initFilterControls();
  initModalsAndDrawers();
  initSettingsForm();
  initAlertFilters();

  // Test backend connection and load initial data
  checkBackendHealth().then((isHealthy) => {
    if (isHealthy) {
      loadSystemSettings();
      loadAllActivePageData();
    }
  });

  // Health ping interval
  setInterval(checkBackendHealth, 25000);
});

// Live topbar clock
function initClock() {
  const clockEl = document.getElementById('clock-display');
  const update = () => {
    const now = new Date();
    if (clockEl) {
      clockEl.textContent = now.toTimeString().split(' ')[0];
    }
  };
  update();
  setInterval(update, 1000);
}

// ============================================================================
// 2. BACKEND HEALTH & REST CLIENT
// ============================================================================
async function checkBackendHealth() {
  const banner = document.getElementById('api-status-banner');
  const pill = document.getElementById('telemetry-status-pill');
  const pillText = document.getElementById('telemetry-pill-text');
  const systemDot = document.getElementById('system-pulse-dot');
  const systemLabel = document.getElementById('system-status-label');

  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    state.backendHealthy = true;
    if (banner) banner.classList.add('hidden');
    if (pill) pill.className = 'telemetry-pill';
    if (pillText) pillText.textContent = 'Live Connected';
    if (systemDot) systemDot.style.backgroundColor = 'var(--status-normal)';
    if (systemLabel) systemLabel.textContent = `Online (${data.system ? 'GENIUS DG' : 'Ready'})`;
    return true;
  } catch (err) {
    state.backendHealthy = false;
    if (banner) banner.classList.remove('hidden');
    if (pill) pill.className = 'telemetry-pill offline';
    if (pillText) pillText.textContent = 'Disconnected';
    if (systemDot) systemDot.style.backgroundColor = 'var(--status-danger)';
    if (systemLabel) systemLabel.textContent = 'Offline (Connection Error)';
    return false;
  }
}

async function apiFetch(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, options);
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({ message: res.statusText }));
      throw new Error(errBody.message || `Request failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

function getFilterQueryParams() {
  const params = new URLSearchParams();
  if (state.filters.dgId && state.filters.dgId !== 'ALL') {
    params.append('dg_id', state.filters.dgId);
  }
  if (state.filters.startDate) {
    params.append('start_date', state.filters.startDate);
  }
  if (state.filters.endDate) {
    params.append('end_date', state.filters.endDate);
  }
  return params.toString();
}

// ============================================================================
// 3. SPA ROUTING & NAVIGATION
// ============================================================================
function initNavigation() {
  const navLinks = document.querySelectorAll('.nav-item');
  const mobileBtn = document.getElementById('mobile-menu-btn');
  const closeSidebarBtn = document.getElementById('sidebar-close-btn');
  const sidebar = document.getElementById('sidebar');

  navLinks.forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const page = link.getAttribute('data-page');
      navigateToPage(page);
      if (window.innerWidth <= 950 && sidebar) {
        sidebar.classList.remove('open');
      }
    });
  });

  if (mobileBtn && closeSidebarBtn && sidebar) {
    mobileBtn.addEventListener('click', () => sidebar.classList.add('open'));
    closeSidebarBtn.addEventListener('click', () => sidebar.classList.remove('open'));
  }

  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '');
    if (hash) navigateToPage(hash);
  });

  const initialHash = window.location.hash.replace('#', '');
  if (initialHash) {
    navigateToPage(initialHash);
  }
}

function navigateToPage(pageId) {
  const targetSection = document.getElementById(`page-${pageId}`);
  if (!targetSection) return;

  state.activePage = pageId;

  // Update nav links active styling
  document.querySelectorAll('.nav-item').forEach((link) => {
    link.classList.toggle('active', link.getAttribute('data-page') === pageId);
  });

  // Toggle page visibility
  document.querySelectorAll('.page-section').forEach((sec) => {
    sec.classList.remove('active');
  });
  targetSection.classList.add('active');

  // Breadcrumb titles
  const titles = {
    overview: 'Overview',
    monitoring: 'Generator Monitoring',
    anomalies: 'AI Insights',
    camera: 'Camera Monitoring',
    alerts: 'Alerts & Notifications',
    'fuel-cost': 'Fuel & Cost Analytics',
    emissions: 'Carbon Emissions',
    maintenance: 'Maintenance',
    reports: 'Reports',
    'data-quality': 'Data Quality Monitor',
    settings: 'Settings'
  };

  const breadcrumb = document.getElementById('topbar-breadcrumb');
  if (breadcrumb) {
    breadcrumb.textContent = titles[pageId] || 'Overview';
  }

  // Load relevant view data
  loadAllActivePageData();
}

function loadAllActivePageData() {
  if (!state.backendHealthy) return;

  switch (state.activePage) {
    case 'overview':
      loadDashboardSummary();
      loadOverviewGeneratorsTable();
      break;
    case 'monitoring':
      loadGeneratorFleetCards();
      loadGeneratorRecords();
      loadShutdownDelayIntelligence();
      break;
    case 'anomalies':
      loadAnomalyAnalysis();
      break;
    case 'camera':
      loadCameraEvents();
      break;
    case 'alerts':
      loadAlertsMasterFeed();
      break;
    case 'fuel-cost':
      loadFuelCostAnalytics();
      loadFuelEfficiencyAnalysis();
      break;
    case 'emissions':
      loadEmissionsAnalysis();
      break;
    case 'maintenance':
      loadMaintenanceData();
      break;
    case 'reports':
      loadReportsData();
      break;
    case 'data-quality':
      loadDataQualityDashboard();
      break;
    case 'settings':
      loadSystemSettings();
      break;
  }
}

// ============================================================================
// 4. GLOBAL FILTER CONTROLS
// ============================================================================
function initFilterControls() {
  const genSelect = document.getElementById('filter-generator');
  const startInput = document.getElementById('filter-start-date');
  const endInput = document.getElementById('filter-end-date');
  const btnApply = document.getElementById('btn-apply-filters');
  const btnReset = document.getElementById('btn-reset-filters');
  const btnRefresh = document.getElementById('btn-refresh');
  const btnReconnect = document.getElementById('btn-reconnect');

  if (btnApply) {
    btnApply.addEventListener('click', () => {
      state.filters.dgId = genSelect.value;
      state.filters.startDate = startInput.value;
      state.filters.endDate = endInput.value;
      state.recordsPagination.page = 1;
      showToast('Filters synchronized across active views', 'info');
      loadAllActivePageData();
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      genSelect.value = 'ALL';
      startInput.value = '2026-05-01';
      endInput.value = '2026-10-31';
      state.filters.dgId = 'ALL';
      state.filters.startDate = '2026-05-01';
      state.filters.endDate = '2026-10-31';
      state.recordsPagination.page = 1;
      showToast('Filters reset to fleet defaults', 'info');
      loadAllActivePageData();
    });
  }

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      btnRefresh.querySelector('i').classList.add('fa-spin');
      showToast('Refreshing live telemetry...', 'info');
      loadAllActivePageData();
      setTimeout(() => {
        btnRefresh.querySelector('i').classList.remove('fa-spin');
      }, 600);
    });
  }

  if (btnReconnect) {
    btnReconnect.addEventListener('click', () => {
      checkBackendHealth().then((ok) => {
        if (ok) {
          loadSystemSettings();
          loadAllActivePageData();
          showToast('Backend reconnected successfully!', 'success');
        }
      });
    });
  }
}

// ============================================================================
// 5. VIEW 1: OVERVIEW DASHBOARD
// ============================================================================
async function loadDashboardSummary() {
  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/dashboard/summary?${q}`);
    if (data.status !== 'success') return;

    const { kpis, charts, recent_alerts } = data;
    state.cachedAlerts = recent_alerts || [];

    // Currency & Pricing state
    state.currency = kpis.currency || '₹';
    state.dieselPrice = kpis.diesel_price_per_litre || 94.50;
    state.emissionFactor = kpis.co2_emission_factor || 2.68;

    // KPI Card Population
    document.getElementById('kpi-generators').textContent = kpis.total_generators;
    document.getElementById('kpi-running-gens').textContent = kpis.running_generators || 2;
    document.getElementById('kpi-runtime').textContent = kpis.total_runtime_hours.toLocaleString();
    document.getElementById('kpi-fuel').textContent = kpis.total_diesel_litres.toLocaleString();
    document.getElementById('kpi-cost').textContent = `${state.currency} ${kpis.estimated_diesel_cost.toLocaleString()}`;
    document.getElementById('kpi-emissions').textContent = kpis.estimated_co2_kg.toLocaleString();
    document.getElementById('kpi-emissions-sub').textContent = `~${kpis.estimated_co2_tonnes} Metric Tonnes`;
    document.getElementById('kpi-anomalies').textContent = kpis.anomalies_detected_count;
    document.getElementById('kpi-delays-sub').textContent = `${kpis.shutdown_delays_count} delay alerts`;

    const costSub = document.getElementById('kpi-cost-sub');
    if (costSub) costSub.textContent = `Rate: ${state.currency}${state.dieselPrice.toFixed(2)} / Litre`;

    // Sidebar & Header Badges
    const sideBadge = document.getElementById('sidebar-anomaly-badge');
    if (sideBadge) sideBadge.textContent = kpis.anomalies_detected_count;

    const notifBadge = document.getElementById('notif-badge');
    const activeAlertsCount = kpis.active_alerts_count || kpis.anomalies_detected_count;
    if (notifBadge) {
      notifBadge.textContent = activeAlertsCount;
      notifBadge.style.display = activeAlertsCount > 0 ? 'inline-block' : 'none';
    }

    const sideAlertDot = document.getElementById('sidebar-alerts-badge');
    if (sideAlertDot) {
      sideAlertDot.classList.toggle('hidden', activeAlertsCount === 0);
    }

    const lastUp = document.getElementById('overview-last-updated');
    if (lastUp) {
      lastUp.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
    }

    // Chart.js Visualizations
    renderDailyRuntimeChart(charts.daily_runtime || []);
    renderFuelByGenChart(charts.diesel_by_generator || []);
    renderCostTrendChart(charts.fuel_cost_trend || []);
    renderCo2TrendChart(charts.co2_emission_trend || []);
    renderAnomalyDistributionChart(charts.normal_vs_anomalies || {});

    // Recent Alerts Table
    renderRecentAlertsTable(recent_alerts || []);
    renderNotificationsDropdown(recent_alerts || []);

  } catch (err) {
    showToast(`Failed loading overview: ${err.message}`, 'error');
  }
}

async function loadOverviewGeneratorsTable() {
  const tbody = document.getElementById('tbody-overview-generators');
  if (!tbody) return;

  try {
    const data = await apiFetch('/generators');
    if (data.status !== 'success') return;
    state.cachedGenerators = data.generators;

    tbody.innerHTML = data.generators.map((g) => {
      const isRunning = g.running_status === 'Running';
      const statusPill = isRunning
        ? '<span class="badge-status-running">Running</span>'
        : '<span class="badge-status-standby">Standby</span>';

      return `
        <tr>
          <td><span class="badge-dg">${escapeHtml(g.dg_id)}</span></td>
          <td>${escapeHtml(g.location || 'Campus Facility')}</td>
          <td><strong>${g.capacity_kva} kVA</strong></td>
          <td>${statusPill}</td>
          <td><span class="tabular-num">${g.load_percentage || 0}%</span></td>
          <td><span class="tabular-num">${g.fuel_level_percent || 80}%</span></td>
          <td><span class="tabular-num">${g.temperature_celsius || 28}°C</span></td>
          <td><span class="tabular-num">${g.vibration_mms || 0.0} mm/s</span></td>
          <td><span class="tabular-num">${g.total_runtime_hours} hrs</span></td>
          <td>
            <button class="btn-outline-sm btn-view-gen" data-dgid="${g.dg_id}">
              <i class="fa-solid fa-gauge"></i> Telemetry
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach drawer openers
    document.querySelectorAll('.btn-view-gen').forEach((b) => {
      b.addEventListener('click', () => {
        const dgid = b.getAttribute('data-dgid');
        openGeneratorDrawer(dgid);
      });
    });

  } catch (err) {
    console.error('Failed loading overview generators table', err);
  }
}

// Chart.js Implementations (Linear/Stripe Refined Styling)
function renderDailyRuntimeChart(data) {
  const ctx = document.getElementById('chart-daily-runtime');
  if (!ctx) return;

  const labels = data.map((d) => d.date);
  const runtimes = data.map((d) => d.runtime_hours);

  destroyChart('dailyRuntime');
  state.charts.dailyRuntime = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Operating Hours',
        data: runtimes,
        backgroundColor: '#2563eb',
        borderRadius: 3,
        hoverBackgroundColor: '#1d4ed8'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleFont: { family: 'Inter', size: 12 },
          bodyFont: { family: 'Inter', size: 12 },
          callbacks: {
            label: (ctx) => ` Runtime: ${ctx.parsed.y} hours`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: { font: { family: 'Inter', size: 11 } }
        },
        x: {
          ticks: { maxTicksLimit: 12, font: { family: 'Inter', size: 11 } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderFuelByGenChart(data) {
  const ctx = document.getElementById('chart-fuel-by-gen');
  if (!ctx) return;

  const labels = data.map((d) => `${d.dg_id} (${d.capacity_kva} kVA)`);
  const values = data.map((d) => d.fuel_litres);

  destroyChart('fuelByGen');
  state.charts.fuelByGen = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: ['#0d9488', '#2563eb', '#6366f1', '#f59e0b'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'right', labels: { boxWidth: 10, font: { family: 'Inter', size: 11 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${ctx.parsed.toLocaleString()} L`
          }
        }
      },
      cutout: '70%'
    }
  });
}

function renderCostTrendChart(data) {
  const ctx = document.getElementById('chart-cost-trend');
  if (!ctx) return;

  const labels = data.map((d) => d.date);
  const costs = data.map((d) => d.cost);

  destroyChart('costTrend');
  state.charts.costTrend = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: `Cost (${state.currency})`,
        data: costs,
        borderColor: '#0d9488',
        backgroundColor: 'rgba(13, 148, 136, 0.06)',
        fill: true,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: {
            callback: (v) => `${state.currency}${v}`,
            font: { family: 'Inter', size: 11 }
          }
        },
        x: {
          ticks: { maxTicksLimit: 8, font: { family: 'Inter', size: 11 } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderCo2TrendChart(data) {
  const ctx = document.getElementById('chart-co2-trend');
  if (!ctx) return;

  const labels = data.map((d) => d.date);
  const co2 = data.map((d) => d.co2_kg);

  destroyChart('co2Trend');
  state.charts.co2Trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'CO2 (kg)',
        data: co2,
        borderColor: '#059669',
        backgroundColor: 'rgba(5, 150, 105, 0.06)',
        fill: true,
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter', size: 11 } } },
        x: { ticks: { maxTicksLimit: 8, font: { family: 'Inter', size: 11 } }, grid: { display: false } }
      }
    }
  });
}

function renderAnomalyDistributionChart(data) {
  const ctx = document.getElementById('chart-anomaly-distribution');
  if (!ctx) return;

  const normal = data.normal_count || 0;
  const anomalies = data.anomalies_count || 0;
  const delays = data.shutdown_delays_count || 0;

  destroyChart('anomalyDist');
  state.charts.anomalyDist = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['Normal Runs', 'AI Anomalies', 'Shutdown Delays'],
      datasets: [{
        data: [normal, anomalies, delays],
        backgroundColor: ['#10b981', '#ef4444', '#f59e0b'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { family: 'Inter', size: 11 } } }
      }
    }
  });
}

function renderRecentAlertsTable(alerts) {
  const tbody = document.getElementById('tbody-recent-alerts');
  if (!tbody) return;

  if (!alerts || alerts.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No operational alerts active for the current filter criteria.</td></tr>';
    return;
  }

  tbody.innerHTML = alerts.map((a) => {
    const isAi = a.alert_type === 'AI_ANOMALY_DETECTION';
    const typeBadge = isAi
      ? '<span class="badge badge-info"><i class="fa-solid fa-brain"></i> AI Outlier</span>'
      : '<span class="badge badge-warning"><i class="fa-solid fa-stopwatch"></i> Delay Rule</span>';

    let sevBadge = '<span class="badge badge-info">Medium</span>';
    if (a.severity === 'CRITICAL') sevBadge = '<span class="badge badge-critical">Critical</span>';
    else if (a.severity === 'HIGH') sevBadge = '<span class="badge badge-warning">High</span>';

    const status = a.status || 'OPEN';
    let statusPill = `<span class="badge badge-critical">Open</span>`;
    if (status === 'ACKNOWLEDGED') statusPill = `<span class="badge badge-warning">Acknowledged</span>`;
    if (status === 'RESOLVED') statusPill = `<span class="badge badge-normal">Resolved</span>`;

    const isResolved = status === 'RESOLVED';

    return `
      <tr class="${isResolved ? 'text-muted' : ''}">
        <td><code>${escapeHtml(a.alert_id)}</code></td>
        <td><span class="badge-dg">${escapeHtml(a.dg_id)}</span></td>
        <td>${escapeHtml(a.date)} ${a.time ? escapeHtml(a.time) : ''}</td>
        <td>${typeBadge}</td>
        <td>${sevBadge}</td>
        <td style="max-width: 280px; font-size: 12px;">${escapeHtml(a.description)}</td>
        <td>${statusPill}</td>
        <td>
          <div style="display: flex; gap: 4px;">
            ${status === 'OPEN' ? `
              <button class="btn-outline-sm btn-alert-action" data-aid="${a.alert_id}" data-action="ACKNOWLEDGED" title="Acknowledge Incident">
                <i class="fa-solid fa-check"></i> Ack
              </button>
            ` : ''}
            ${status !== 'RESOLVED' ? `
              <button class="btn-outline-sm btn-alert-action" data-aid="${a.alert_id}" data-action="RESOLVED" title="Resolve Incident">
                <i class="fa-solid fa-circle-check text-teal"></i> Resolve
              </button>
            ` : '<span style="font-size: 11px; color: var(--text-light);">&mdash;</span>'}
          </div>
        </td>
      </tr>
    `;
  }).join('');

  // Attach action buttons
  document.querySelectorAll('.btn-alert-action').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const aid = btn.getAttribute('data-aid');
      const action = btn.getAttribute('data-action');
      await updateAlertStatus(aid, action);
    });
  });
}

function renderNotificationsDropdown(alerts) {
  const list = document.getElementById('notif-quick-list');
  if (!list) return;

  const openAlerts = alerts.filter((a) => a.status !== 'RESOLVED');
  if (openAlerts.length === 0) {
    list.innerHTML = '<div class="notif-empty">No active unresolved alerts</div>';
    return;
  }

  list.innerHTML = openAlerts.slice(0, 5).map((a) => `
    <div style="padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); font-size: 11.5px;">
      <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
        <strong>${escapeHtml(a.dg_id)}</strong>
        <span style="color: var(--text-muted);">${escapeHtml(a.date)}</span>
      </div>
      <div style="color: var(--text-secondary);">${escapeHtml(a.description)}</div>
    </div>
  `).join('');
}

// Toggle notifications dropdown
document.addEventListener('DOMContentLoaded', () => {
  const notifBtn = document.getElementById('btn-notifications-toggle');
  const notifDrop = document.getElementById('notifications-dropdown');

  if (notifBtn && notifDrop) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDrop.classList.toggle('hidden');
    });

    window.addEventListener('click', (e) => {
      if (!notifDrop.contains(e.target)) {
        notifDrop.classList.add('hidden');
      }
    });
  }
});

// ============================================================================
// 6. VIEW 2: GENERATOR MONITORING MODULE
// ============================================================================
async function loadGeneratorFleetCards() {
  const container = document.getElementById('fleet-overview-grid');
  if (!container) return;

  try {
    const data = await apiFetch('/generators');
    if (data.status !== 'success') return;
    state.cachedGenerators = data.generators;

    container.innerHTML = data.generators.map((g) => {
      const isRunning = g.running_status === 'Running';
      return `
        <div class="fleet-card-unit">
          <div class="fleet-card-top-row">
            <div>
              <div class="fleet-card-title">${escapeHtml(g.dg_id)}</div>
              <div class="fleet-card-loc">${escapeHtml(g.location || 'Facility Bay')}</div>
            </div>
            ${isRunning ? '<span class="badge-status-running">Running</span>' : '<span class="badge-status-standby">Standby</span>'}
          </div>
          <div class="fleet-metrics-stack">
            <div class="fleet-row-item"><span>Capacity:</span><span>${g.capacity_kva} kVA</span></div>
            <div class="fleet-row-item"><span>Electrical Load:</span><span>${g.load_percentage || 0}%</span></div>
            <div class="fleet-row-item"><span>Fuel Level:</span><span>${g.fuel_level_percent || 80}%</span></div>
            <div class="fleet-row-item"><span>Coolant Temp:</span><span>${g.temperature_celsius || 28}°C</span></div>
            <div class="fleet-row-item"><span>Vibration:</span><span>${g.vibration_mms || 0.0} mm/s</span></div>
            <div class="fleet-row-item"><span>Total Runtime:</span><span>${g.total_runtime_hours} hrs</span></div>
            <div class="fleet-row-item"><span>Fuel Consumed:</span><span>${g.total_fuel_litres.toLocaleString()} L</span></div>
          </div>
          <button class="btn-secondary-sm mt-3 btn-view-gen" data-dgid="${g.dg_id}" style="width: 100%; justify-content: center;">
            <i class="fa-solid fa-gauge"></i> Detailed Telemetry Drawer
          </button>
        </div>
      `;
    }).join('');

    // Reattach drawer openers
    document.querySelectorAll('.btn-view-gen').forEach((b) => {
      b.addEventListener('click', () => {
        openGeneratorDrawer(b.getAttribute('data-dgid'));
      });
    });

  } catch (err) {
    showToast(`Error loading fleet cards: ${err.message}`, 'error');
  }
}

async function loadGeneratorRecords() {
  const tbody = document.getElementById('tbody-generator-records');
  const pageInfo = document.getElementById('pagination-info');
  const pageCurrent = document.getElementById('pagination-current-page');
  const btnPrev = document.getElementById('btn-page-prev');
  const btnNext = document.getElementById('btn-page-next');
  if (!tbody) return;

  try {
    const q = new URLSearchParams();
    if (state.filters.dgId && state.filters.dgId !== 'ALL') q.append('dg_id', state.filters.dgId);
    if (state.filters.startDate) q.append('start_date', state.filters.startDate);
    if (state.filters.endDate) q.append('end_date', state.filters.endDate);
    if (state.recordsPagination.search) q.append('search', state.recordsPagination.search);

    q.append('sort_by', state.recordsPagination.sortBy);
    q.append('sort_order', state.recordsPagination.sortOrder);
    q.append('page', state.recordsPagination.page);
    q.append('per_page', state.recordsPagination.perPage);

    const res = await apiFetch(`/records?${q.toString()}`);
    const { records, pagination } = res;

    if (!records || records.length === 0) {
      tbody.innerHTML = '<tr><td colspan="13" class="text-center py-4 text-muted">No generator records matched current filters.</td></tr>';
      if (pageInfo) pageInfo.textContent = 'Showing 0 records';
      if (btnPrev) btnPrev.disabled = true;
      if (btnNext) btnNext.disabled = true;
      return;
    }

    tbody.innerHTML = records.map((r) => {
      let delayBadge = '<span>&mdash;</span>';
      if (r.shutdown_delay_min > 10) {
        delayBadge = `<span class="badge badge-warning">${r.shutdown_delay_min} min</span>`;
      } else if (r.shutdown_delay_min > 0) {
        delayBadge = `<span>${r.shutdown_delay_min} min</span>`;
      }

      let statusBadge = '<span class="badge badge-normal">Normal</span>';
      if (r.ground_truth_label === 'EXCESSIVE_FUEL') {
        statusBadge = '<span class="badge badge-critical">Fuel Spike</span>';
      } else if (r.ground_truth_label === 'OVERLOAD') {
        statusBadge = '<span class="badge badge-warning">Overload</span>';
      } else if (r.ground_truth_label === 'SHUTDOWN_DELAY') {
        statusBadge = '<span class="badge badge-warning">Delay</span>';
      }

      return `
        <tr>
          <td><code>${escapeHtml(r.record_id)}</code></td>
          <td><span class="badge-dg">${escapeHtml(r.dg_id)}</span></td>
          <td>${r.capacity_kva} kVA</td>
          <td>${escapeHtml(r.date)}</td>
          <td>${escapeHtml(r.start_time)}</td>
          <td>${escapeHtml(r.stop_time)}</td>
          <td>${r.mains_restored_time ? escapeHtml(r.mains_restored_time) : '&mdash;'}</td>
          <td><strong class="tabular-num">${r.load_kw}</strong></td>
          <td><strong class="tabular-num">${r.fuel_used_litres}</strong></td>
          <td><span class="tabular-num">${r.runtime_min}</span></td>
          <td>${delayBadge}</td>
          <td>${statusBadge}</td>
          <td>
            <button class="btn-outline-sm btn-inspect-record" data-record='${JSON.stringify(r).replace(/'/g, "&apos;")}'>
              <i class="fa-solid fa-eye"></i> View
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Pagination controls
    if (pageInfo) pageInfo.textContent = `Showing page ${pagination.current_page} of ${pagination.total_pages} (${pagination.total_records} records)`;
    if (pageCurrent) pageCurrent.textContent = `Page ${pagination.current_page}`;
    if (btnPrev) btnPrev.disabled = !pagination.has_prev;
    if (btnNext) btnNext.disabled = !pagination.has_next;

    // View Record Drawer
    document.querySelectorAll('.btn-inspect-record').forEach((btn) => {
      btn.addEventListener('click', () => {
        try {
          const rec = JSON.parse(btn.getAttribute('data-record'));
          openRecordDetailDrawer(rec);
        } catch (e) {
          console.error(e);
        }
      });
    });

  } catch (err) {
    showToast(`Failed loading records: ${err.message}`, 'error');
  }
}

// ============================================================================
// 7. VIEW 3: AI INSIGHTS MODULE
// ============================================================================
async function loadAnomalyAnalysis() {
  const tbodyAi = document.getElementById('tbody-ai-anomalies');
  const tbodyDelays = document.getElementById('tbody-delay-alerts');
  const tableCount = document.getElementById('ai-table-count');
  if (!tbodyAi) return;

  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/analysis/anomalies?${q}`);
    if (data.status !== 'success') return;

    const { ai_anomalies, model_evaluation, summary } = data;

    // Display Benchmark Evaluation
    if (model_evaluation && model_evaluation.evaluation && model_evaluation.evaluation.metrics) {
      const m = model_evaluation.evaluation.metrics;
      document.getElementById('metric-precision').textContent = `${(m.precision * 100).toFixed(1)}%`;
      document.getElementById('metric-recall').textContent = `${(m.recall * 100).toFixed(1)}%`;
      document.getElementById('metric-f1').textContent = `${(m.f1_score * 100).toFixed(1)}%`;
      document.getElementById('metric-detected-count').textContent = summary.anomalies;
    }

    if (model_evaluation && model_evaluation.engine) {
      const engineBadge = document.getElementById('active-ml-engine-badge');
      if (engineBadge) engineBadge.textContent = model_evaluation.engine;
    }

    if (tableCount) tableCount.textContent = `${summary.anomalies} Outliers Flagged`;

    // Render AI Anomalies Table
    if (!ai_anomalies || ai_anomalies.length === 0) {
      tbodyAi.innerHTML = '<tr><td colspan="11" class="text-center py-4 text-muted">No statistical multivariate anomalies detected in current filter range.</td></tr>';
    } else {
      tbodyAi.innerHTML = ai_anomalies.map((a) => {
        const triggers = (a.trigger_reasons && a.trigger_reasons.length > 0)
          ? a.trigger_reasons.map((t) => `<span class="badge badge-warning">${escapeHtml(t)}</span>`).join(' ')
          : '<span class="badge badge-info">Multivariate distribution shift</span>';

        const severity = a.anomaly_severity_percent > 65
          ? '<span class="badge badge-critical">High Deviation</span>'
          : '<span class="badge badge-warning">Moderate</span>';

        return `
          <tr>
            <td><code>${escapeHtml(a.record_id)}</code></td>
            <td><span class="badge-dg">${escapeHtml(a.dg_id)}</span></td>
            <td>${escapeHtml(a.date)}</td>
            <td><span class="tabular-num">${a.runtime_min}</span> min</td>
            <td><span class="tabular-num">${a.load_kw}</span> kW</td>
            <td><span class="tabular-num">${a.fuel_used_litres}</span> L</td>
            <td><strong>${a.fuel_per_hour} L/h</strong></td>
            <td><code>${a.anomaly_score}</code></td>
            <td>${severity} (${a.anomaly_severity_percent}%)</td>
            <td>${triggers}</td>
            <td>
              <button class="btn-primary-sm btn-explain-anomaly" data-recid="${escapeHtml(a.record_id)}">
                <i class="fa-solid fa-wand-magic-sparkles"></i> Explain
              </button>
            </td>
          </tr>
        `;
      }).join('');

      // Attach Explain Anomaly modal triggers
      document.querySelectorAll('.btn-explain-anomaly').forEach((btn) => {
        btn.addEventListener('click', () => {
          const recId = btn.getAttribute('data-recid');
          openAnomalyExplanationModal(recId);
        });
      });
    }

    // Load separate deterministic delay rules
    loadShutdownDelayRulesTable();

  } catch (err) {
    showToast(`Error loading AI insights: ${err.message}`, 'error');
  }
}

async function loadShutdownDelayRulesTable() {
  const tbody = document.getElementById('tbody-delay-alerts');
  const thresholdLabel = document.getElementById('lbl-delay-threshold');
  if (!tbody) return;

  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/alerts?type=RULE_BASED_SHUTDOWN_DELAY&${q}`);
    const alerts = data.alerts || [];

    if (thresholdLabel) thresholdLabel.textContent = state.delayThreshold;

    if (alerts.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted">No generator shutdown delays exceeding threshold detected in current filter range.</td></tr>';
      return;
    }

    tbody.innerHTML = alerts.map((d) => `
      <tr>
        <td><code>${escapeHtml(d.record_id)}</code></td>
        <td><span class="badge-dg">${escapeHtml(d.dg_id)}</span></td>
        <td>${escapeHtml(d.date)}</td>
        <td>${escapeHtml(d.time)}</td>
        <td>&mdash;</td>
        <td><strong class="text-amber tabular-num">${d.delay_minutes} min</strong></td>
        <td><span class="tabular-num">${d.estimated_avoidable_fuel_litres} L</span></td>
        <td><span class="tabular-num">${state.currency} ${d.estimated_avoidable_cost.toLocaleString()}</span></td>
        <td><span class="badge badge-critical">${d.severity}</span></td>
        <td class="text-muted" style="font-size: 11.5px; max-width: 260px;">${escapeHtml(d.recommended_action)}</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed loading delay alerts', err);
  }
}

// ============================================================================
// 8. VIEW 4: CAMERA MONITORING MODULE (NEW)
// ============================================================================
async function loadCameraEvents() {
  const tbody = document.getElementById('tbody-camera-events');
  if (!tbody) return;

  try {
    const data = await apiFetch('/camera/events');
    const events = data.events || [];

    tbody.innerHTML = events.map((e) => {
      let sevBadge = '<span class="badge badge-normal">Normal</span>';
      if (e.severity === 'CRITICAL') sevBadge = '<span class="badge badge-critical">Critical</span>';
      else if (e.severity === 'WARNING') sevBadge = '<span class="badge badge-warning">Warning</span>';

      return `
        <tr>
          <td><code>${escapeHtml(e.id)}</code></td>
          <td><strong>${escapeHtml(e.camera_id)}</strong></td>
          <td>${escapeHtml(e.bay_name)}</td>
          <td>${escapeHtml(e.timestamp)}</td>
          <td>${escapeHtml(e.event_type)}</td>
          <td><code>${escapeHtml(e.reading)}</code></td>
          <td>${sevBadge}</td>
          <td><span class="badge badge-info">${escapeHtml(e.status)}</span></td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    showToast(`Error loading camera telemetry: ${err.message}`, 'error');
  }
}

// Camera Simulation Button
document.addEventListener('DOMContentLoaded', () => {
  const btnSimCam = document.getElementById('btn-simulate-cam-event');
  if (btnSimCam) {
    btnSimCam.addEventListener('click', async () => {
      const types = ['EXHAUST_SMOKE_SPIKE', 'THERMAL_HOTSPOT', 'OIL_LEAK_PUDDLE', 'PERIMETER_ALERT'];
      const randomType = types[Math.floor(Math.random() * types.length)];
      const gens = ['DG-101', 'DG-102', 'DG-103', 'DG-104'];
      const randomGen = gens[Math.floor(Math.random() * gens.length)];

      try {
        const res = await apiFetch('/camera/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dg_id: randomGen, event_type: randomType })
        });

        showToast(`Simulated Visual Event: ${res.event.title} on ${randomGen}`, 'info');
        loadCameraEvents();
      } catch (e) {
        showToast(`Simulation error: ${e.message}`, 'error');
      }
    });
  }
});

// ============================================================================
// 9. VIEW 5: ALERTS & NOTIFICATIONS MODULE (ENHANCED LIFECYCLE)
// ============================================================================
async function loadAlertsMasterFeed() {
  const feed = document.getElementById('alerts-master-feed');
  const cntOpen = document.getElementById('cnt-open-alerts');
  const cntAck = document.getElementById('cnt-ack-alerts');
  const cntRes = document.getElementById('cnt-res-alerts');
  const tabOpenCount = document.getElementById('tab-open-count');
  if (!feed) return;

  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/alerts?${q}`);
    const alerts = data.alerts || [];

    // Count states
    let openCount = 0;
    let ackCount = 0;
    let resCount = 0;

    alerts.forEach((a) => {
      const s = a.status || 'OPEN';
      if (s === 'OPEN') openCount++;
      else if (s === 'ACKNOWLEDGED') ackCount++;
      else if (s === 'RESOLVED') resCount++;
    });

    if (cntOpen) cntOpen.textContent = openCount;
    if (cntAck) cntAck.textContent = ackCount;
    if (cntRes) cntRes.textContent = resCount;
    if (tabOpenCount) tabOpenCount.textContent = openCount;

    // Filter alerts by state filters
    let filtered = alerts;
    if (state.alertsFilter.status !== 'ALL') {
      filtered = filtered.filter((a) => (a.status || 'OPEN') === state.alertsFilter.status);
    }
    if (state.alertsFilter.severity !== 'ALL') {
      filtered = filtered.filter((a) => a.severity === state.alertsFilter.severity);
    }
    if (state.alertsFilter.type !== 'ALL') {
      filtered = filtered.filter((a) => a.alert_type === state.alertsFilter.type);
    }

    if (filtered.length === 0) {
      feed.innerHTML = '<div class="text-center py-4 text-muted">No operational alerts matching active filter tabs.</div>';
      return;
    }

    feed.innerHTML = filtered.map((a) => {
      const status = a.status || 'OPEN';
      const borderClass = a.severity === 'CRITICAL' ? 'border-critical' : (a.severity === 'HIGH' ? 'border-high' : 'border-medium');
      const isResolved = status === 'RESOLVED';

      return `
        <div class="alert-card-row ${borderClass} ${isResolved ? 'status-resolved' : ''}">
          <div class="alert-main-info">
            <div class="alert-top-meta">
              <span class="badge-dg">${escapeHtml(a.dg_id)}</span>
              <span>&bull;</span>
              <code>${escapeHtml(a.alert_id)}</code>
              <span>&bull;</span>
              <span><i class="fa-regular fa-clock"></i> ${escapeHtml(a.date)} ${a.time ? escapeHtml(a.time) : ''}</span>
              <span class="badge ${a.severity === 'CRITICAL' ? 'badge-critical' : (a.severity === 'HIGH' ? 'badge-warning' : 'badge-info')}">${a.severity}</span>
              ${status === 'ACKNOWLEDGED' ? '<span class="badge badge-warning">Acknowledged</span>' : ''}
              ${status === 'RESOLVED' ? '<span class="badge badge-normal">Resolved</span>' : ''}
            </div>
            <div class="alert-title-text">${escapeHtml(a.description)}</div>
            <div class="alert-action-guidance"><i class="fa-solid fa-screwdriver-wrench"></i> ${escapeHtml(a.recommended_action)}</div>
            ${a.resolution_note ? `<div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">Note: ${escapeHtml(a.resolution_note)}</div>` : ''}
          </div>
          <div class="alert-actions-group">
            ${status === 'OPEN' ? `
              <button class="btn-secondary-sm btn-feed-ack" data-aid="${a.alert_id}">
                <i class="fa-solid fa-check"></i> Acknowledge
              </button>
            ` : ''}
            ${status !== 'RESOLVED' ? `
              <button class="btn-primary-sm btn-feed-res" data-aid="${a.alert_id}">
                <i class="fa-solid fa-circle-check"></i> Resolve
              </button>
            ` : '<span class="badge badge-normal"><i class="fa-solid fa-check-double"></i> Closed</span>'}
          </div>
        </div>
      `;
    }).join('');

    // Attach lifecycle triggers
    document.querySelectorAll('.btn-feed-ack').forEach((btn) => {
      btn.addEventListener('click', () => {
        const aid = btn.getAttribute('data-aid');
        updateAlertStatus(aid, 'ACKNOWLEDGED');
      });
    });

    document.querySelectorAll('.btn-feed-res').forEach((btn) => {
      btn.addEventListener('click', () => {
        const aid = btn.getAttribute('data-aid');
        updateAlertStatus(aid, 'RESOLVED');
      });
    });

  } catch (err) {
    showToast(`Error loading alerts feed: ${err.message}`, 'error');
  }
}

async function updateAlertStatus(alertId, newStatus) {
  try {
    const res = await apiFetch(`/alerts/${alertId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus, notes: `Updated from Control Room at ${new Date().toLocaleTimeString()}` })
    });

    showToast(`Alert ${alertId} updated to ${newStatus}`, 'success');

    // Refresh active views
    if (state.activePage === 'alerts') {
      loadAlertsMasterFeed();
    } else if (state.activePage === 'overview') {
      loadDashboardSummary();
    }
  } catch (err) {
    showToast(`Failed updating alert: ${err.message}`, 'error');
  }
}

function initAlertFilters() {
  document.querySelectorAll('.filter-tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-tab-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.alertsFilter.status = btn.getAttribute('data-status-filter');
      loadAlertsMasterFeed();
    });
  });

  const sevSelect = document.getElementById('select-alert-severity');
  if (sevSelect) {
    sevSelect.addEventListener('change', (e) => {
      state.alertsFilter.severity = e.target.value;
      loadAlertsMasterFeed();
    });
  }

  const typeSelect = document.getElementById('select-alert-type');
  if (typeSelect) {
    typeSelect.addEventListener('change', (e) => {
      state.alertsFilter.type = e.target.value;
      loadAlertsMasterFeed();
    });
  }
}

// ============================================================================
// 10. VIEW 6: FUEL & COST ANALYTICS MODULE (UNIFIED)
// ============================================================================
async function loadFuelCostAnalytics() {
  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/analysis/fuel?${q}`);
    if (data.status !== 'success') return;

    const { analysis } = data;

    // Active price
    const priceEl = document.getElementById('fuel-cost-active-price');
    if (priceEl) priceEl.textContent = `${state.currency} ${state.dieselPrice.toFixed(2)} / Litre`;

    const quickInput = document.getElementById('quick-price-input');
    if (quickInput) quickInput.value = state.dieselPrice;

    // KPIs
    document.getElementById('fuel-total-litres').textContent = analysis.total_fuel_litres.toLocaleString();
    document.getElementById('cost-total-amount').textContent = `${state.currency} ${analysis.total_cost.toLocaleString()}`;
    document.getElementById('fuel-avg-hourly').textContent = analysis.avg_consumption_per_hour.toFixed(2);

    const delayWastage = analysis.illustrative_delay_wastage || {};
    document.getElementById('cost-delay-amount').textContent = `${state.currency} ${(delayWastage.estimated_avoidable_cost || 0).toLocaleString()}`;
    const delayLitresSub = document.getElementById('fuel-delay-litres-sub');
    if (delayLitresSub) delayLitresSub.textContent = `~${delayWastage.estimated_avoidable_fuel_litres || 0} L avoidable delay fuel`;

    // Charts
    renderFuelDailyBarChart(analysis.daily_trend || []);
    renderFuelRateBarChart(analysis.by_generator || []);

    // Table
    renderFuelByGenTable(analysis.by_generator || []);

  } catch (err) {
    showToast(`Error loading fuel & cost analytics: ${err.message}`, 'error');
  }
}

function renderFuelDailyBarChart(data) {
  const ctx = document.getElementById('chart-fuel-daily');
  if (!ctx) return;

  const labels = data.map((d) => d.date);
  const litres = data.map((d) => d.fuel_litres);

  destroyChart('fuelDaily');
  state.charts.fuelDaily = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Diesel Consumed (L)',
        data: litres,
        backgroundColor: '#f59e0b',
        borderRadius: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter', size: 11 } } },
        x: { ticks: { maxTicksLimit: 10, font: { family: 'Inter', size: 11 } }, grid: { display: false } }
      }
    }
  });
}

function renderFuelRateBarChart(data) {
  const ctx = document.getElementById('chart-fuel-rate-comparison');
  if (!ctx) return;

  const labels = data.map((d) => d.dg_id);
  const rates = data.map((d) => d.avg_litres_per_hour);

  destroyChart('fuelRateComp');
  state.charts.fuelRateComp = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Average L/hr',
        data: rates,
        backgroundColor: ['#0d9488', '#2563eb', '#6366f1', '#10b981'],
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter', size: 11 } } }
      }
    }
  });
}

function renderFuelByGenTable(generators) {
  const tbody = document.getElementById('tbody-fuel-by-gen');
  if (!tbody) return;

  tbody.innerHTML = generators.map((g) => `
    <tr>
      <td><span class="badge-dg">${escapeHtml(g.dg_id)}</span></td>
      <td>${g.capacity_kva} kVA</td>
      <td>${g.runs_count} cycles</td>
      <td><span class="tabular-num">${g.runtime_hours} hrs</span></td>
      <td><strong>${g.fuel_litres.toLocaleString()} L</strong></td>
      <td>${g.share_percentage}%</td>
      <td><strong>${g.avg_litres_per_hour} L/h</strong></td>
      <td><strong>${state.currency} ${g.cost.toLocaleString()}</strong></td>
    </tr>
  `).join('');
}

// Quick Price adjust button
document.addEventListener('DOMContentLoaded', () => {
  const btnQuickPrice = document.getElementById('btn-quick-price-save');
  const quickInput = document.getElementById('quick-price-input');

  if (btnQuickPrice && quickInput) {
    btnQuickPrice.addEventListener('click', async () => {
      const newPrice = parseFloat(quickInput.value);
      if (!newPrice || newPrice <= 0) {
        showToast('Please enter a valid positive price per litre', 'error');
        return;
      }

      try {
        await apiFetch('/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ diesel_price_per_litre: newPrice })
        });
        state.dieselPrice = newPrice;
        showToast(`Diesel price updated to ${state.currency} ${newPrice.toFixed(2)}`, 'success');
        loadFuelCostAnalytics();
      } catch (err) {
        showToast(`Failed updating price: ${err.message}`, 'error');
      }
    });
  }
});

// ============================================================================
// 11. VIEW 7: CARBON EMISSIONS MODULE
// ============================================================================
async function loadEmissionsAnalysis() {
  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/analysis/emissions?${q}`);
    if (data.status !== 'success') return;

    const { analysis } = data;

    document.getElementById('emissions-factor-val').textContent = `${analysis.emission_factor_used} kg CO2 / L`;
    document.getElementById('emissions-total-kg').textContent = analysis.total_co2_kg.toLocaleString();
    document.getElementById('emissions-total-tonnes').textContent = `${analysis.total_co2_tonnes} Metric Tonnes`;
    document.getElementById('emissions-diesel-total').textContent = analysis.total_diesel_litres.toLocaleString();

    const treeYrs = analysis.illustrative_equivalence?.tree_years_to_sequester || 0;
    document.getElementById('emissions-tree-years').textContent = treeYrs.toLocaleString();

    renderEmissionsDailyChart(analysis.daily_trend || []);
    renderEmissionsByGenChart(analysis.by_generator || []);
    renderEmissionsTable(analysis.by_generator || []);

  } catch (err) {
    showToast(`Error loading emissions: ${err.message}`, 'error');
  }
}

function renderEmissionsDailyChart(data) {
  const ctx = document.getElementById('chart-emissions-daily');
  if (!ctx) return;

  const labels = data.map((d) => d.date);
  const co2 = data.map((d) => d.co2_kg);

  destroyChart('emissionsDaily');
  state.charts.emissionsDaily = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'CO2 (kg)',
        data: co2,
        borderColor: '#059669',
        backgroundColor: 'rgba(5, 150, 105, 0.06)',
        fill: true,
        tension: 0.3,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter', size: 11 } } },
        x: { ticks: { maxTicksLimit: 10, font: { family: 'Inter', size: 11 } }, grid: { display: false } }
      }
    }
  });
}

function renderEmissionsByGenChart(data) {
  const ctx = document.getElementById('chart-emissions-by-gen');
  if (!ctx) return;

  const labels = data.map((d) => d.dg_id);
  const co2 = data.map((d) => d.co2_kg);

  destroyChart('emissionsByGen');
  state.charts.emissionsByGen = new Chart(ctx, {
    type: 'pie',
    data: {
      labels,
      datasets: [{
        data: co2,
        backgroundColor: ['#0d9488', '#2563eb', '#6366f1', '#10b981'],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

function renderEmissionsTable(generators) {
  const tbody = document.getElementById('tbody-emissions-by-gen');
  if (!tbody) return;

  tbody.innerHTML = generators.map((g) => `
    <tr>
      <td><span class="badge-dg">${escapeHtml(g.dg_id)}</span></td>
      <td>${g.capacity_kva} kVA</td>
      <td><span class="tabular-num">${g.fuel_litres.toLocaleString()} L</span></td>
      <td>${state.emissionFactor} kg/L</td>
      <td><strong>${g.co2_kg.toLocaleString()} kg</strong></td>
      <td><span class="tabular-num">${g.co2_tonnes} T</span></td>
      <td>${g.share_percentage}%</td>
    </tr>
  `).join('');
}

// ============================================================================
// 12. VIEW 8: MAINTENANCE MODULE (NEW)
// ============================================================================
async function loadMaintenanceData() {
  const grid = document.getElementById('maintenance-schedules-grid');
  const tbody = document.getElementById('tbody-maintenance-logs');
  if (!grid) return;

  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/maintenance?${q}`);
    const schedules = data.maintenance_schedules || [];

    grid.innerHTML = schedules.map((m) => {
      const isDueSoon = m.status === 'DUE_SOON';
      const pct = Math.min(100, Math.round(((m.interval_hours - m.hours_remaining) / m.interval_hours) * 100));

      return `
        <div class="maintenance-card">
          <div class="m-card-header">
            <span class="m-dg-tag">${escapeHtml(m.dg_id)}</span>
            <span class="badge ${isDueSoon ? 'badge-warning' : 'badge-normal'}">${m.status.replace('_', ' ')}</span>
          </div>
          <div class="m-service-name">${escapeHtml(m.service_type)}</div>
          <div class="m-progress-container">
            <div class="m-progress-bar">
              <div class="m-progress-fill" style="width: ${pct}%;"></div>
            </div>
            <div class="m-progress-meta">
              <span>${m.hours_remaining} hrs remaining</span>
              <span>${pct}% elapsed</span>
            </div>
          </div>
          <div class="m-tech-tag">
            <i class="fa-solid fa-user-gear"></i> ${escapeHtml(m.assigned_technician)}
          </div>
          <div style="font-size: 11px; color: var(--text-muted);">
            Target Due: ${escapeHtml(m.due_date)}
          </div>
        </div>
      `;
    }).join('');

    if (tbody) {
      tbody.innerHTML = schedules.map((m) => `
        <tr>
          <td><code>${escapeHtml(m.id)}</code></td>
          <td><span class="badge-dg">${escapeHtml(m.dg_id)}</span></td>
          <td><strong>${escapeHtml(m.service_type)}</strong></td>
          <td><span class="tabular-num">${m.current_hours} hrs</span></td>
          <td>${escapeHtml(m.due_date)}</td>
          <td>${escapeHtml(m.assigned_technician)}</td>
          <td><span class="badge ${m.status === 'COMPLETED' ? 'badge-normal' : (m.status === 'DUE_SOON' ? 'badge-warning' : 'badge-info')}">${m.status}</span></td>
          <td style="font-size: 11.5px; color: var(--text-secondary);">${escapeHtml(m.checklist ? m.checklist.join(', ') : 'Standard service')}</td>
        </tr>
      `).join('');
    }

  } catch (err) {
    showToast(`Error loading maintenance schedules: ${err.message}`, 'error');
  }
}

// ============================================================================
// 13. VIEW 9: REPORTS MODULE
// ============================================================================
async function loadReportsData() {
  try {
    const q = getFilterQueryParams();
    const data = await apiFetch(`/dashboard/summary?${q}`);
    if (data.status !== 'success') return;

    const { kpis, charts, recent_alerts } = data;

    document.getElementById('report-timestamp').textContent = new Date().toLocaleString();
    document.getElementById('report-period-text').textContent = `${state.filters.startDate} to ${state.filters.endDate}`;
    document.getElementById('report-filter-target').textContent = state.filters.dgId === 'ALL' ? 'Entire Fleet (All 4 Units)' : state.filters.dgId;

    document.getElementById('rep-runtime').textContent = `${kpis.total_runtime_hours.toLocaleString()} hrs`;
    document.getElementById('rep-fuel').textContent = `${kpis.total_diesel_litres.toLocaleString()} L`;
    document.getElementById('rep-cost').textContent = `${state.currency} ${kpis.estimated_diesel_cost.toLocaleString()}`;
    document.getElementById('rep-co2').textContent = `${kpis.estimated_co2_kg.toLocaleString()} kg (${kpis.estimated_co2_tonnes} T)`;
    document.getElementById('rep-anomalies').textContent = `${kpis.anomalies_detected_count} AI / ${kpis.shutdown_delays_count} delays`;

    const tbodyFleet = document.getElementById('tbody-report-fleet');
    if (tbodyFleet && charts.diesel_by_generator) {
      tbodyFleet.innerHTML = charts.diesel_by_generator.map((g) => {
        const co2Kg = (g.fuel_litres * state.emissionFactor).toFixed(1);
        return `
          <tr>
            <td><strong>${escapeHtml(g.dg_id)}</strong></td>
            <td>${g.capacity_kva} kVA</td>
            <td>${g.runs_count}</td>
            <td>${g.runtime_hours} hrs</td>
            <td>${g.fuel_litres.toLocaleString()} L</td>
            <td>${g.avg_litres_per_hour} L/h</td>
            <td>${state.currency} ${g.cost.toLocaleString()}</td>
            <td>${Number(co2Kg).toLocaleString()} kg</td>
          </tr>
        `;
      }).join('');
    }

    const tbodyIncidents = document.getElementById('tbody-report-incidents');
    if (tbodyIncidents) {
      if (!recent_alerts || recent_alerts.length === 0) {
        tbodyIncidents.innerHTML = '<tr><td colspan="7" class="text-center py-2 text-muted">No high-priority incidents reported during this operational period.</td></tr>';
      } else {
        tbodyIncidents.innerHTML = recent_alerts.map((a) => `
          <tr>
            <td><code>${escapeHtml(a.alert_id)}</code></td>
            <td>${escapeHtml(a.dg_id)}</td>
            <td>${escapeHtml(a.date)}</td>
            <td>${escapeHtml(a.alert_type)}</td>
            <td><strong>${escapeHtml(a.severity)}</strong></td>
            <td>${escapeHtml(a.description)}</td>
            <td>${escapeHtml(a.recommended_action)}</td>
          </tr>
        `).join('');
      }
    }

  } catch (err) {
    showToast(`Error generating audit report: ${err.message}`, 'error');
  }
}

// Print and CSV Export Handlers
document.addEventListener('DOMContentLoaded', () => {
  const btnPrint = document.getElementById('btn-print-report');
  const btnExport = document.getElementById('btn-export-csv');

  if (btnPrint) {
    btnPrint.addEventListener('click', () => {
      window.print();
    });
  }

  if (btnExport) {
    btnExport.addEventListener('click', async () => {
      try {
        const q = getFilterQueryParams();
        const res = await apiFetch(`/records?per_page=1000&${q}`);
        const records = res.records || [];

        if (records.length === 0) {
          showToast('No records available to export', 'error');
          return;
        }

        const headers = ['record_id', 'dg_id', 'capacity_kva', 'date', 'start_time', 'stop_time', 'mains_restored_time', 'load_kw', 'fuel_used_litres', 'runtime_min', 'shutdown_delay_min', 'ground_truth_label'];
        let csvContent = headers.join(',') + '\n';

        records.forEach((r) => {
          const row = headers.map((h) => `"${r[h] !== undefined ? r[h] : ''}"`).join(',');
          csvContent += row + '\n';
        });

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `genius_dg_audit_records_${state.filters.startDate}_to_${state.filters.endDate}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast('Filtered telemetry records exported as CSV successfully!', 'success');
      } catch (err) {
        showToast(`Failed exporting CSV: ${err.message}`, 'error');
      }
    });
  }
});

// ============================================================================
// 14. VIEW 10: SETTINGS MODULE
// ============================================================================
async function loadSystemSettings() {
  try {
    const data = await apiFetch('/settings');
    if (data.status !== 'success') return;

    const s = data.settings;
    state.dieselPrice = s.diesel_price_per_litre;
    state.currency = s.currency_symbol || '₹';
    state.emissionFactor = s.co2_emission_factor;
    state.delayThreshold = s.shutdown_delay_threshold_min;
    state.contaminationRate = s.ai_contamination_rate;

    const priceInput = document.getElementById('set-diesel-price');
    const curSelect = document.getElementById('set-currency-symbol');
    const co2Input = document.getElementById('set-co2-factor');
    const delayInput = document.getElementById('set-delay-threshold');
    const contamInput = document.getElementById('set-contamination');
    const addon = document.getElementById('currency-addon');

    if (priceInput) priceInput.value = s.diesel_price_per_litre;
    if (curSelect) curSelect.value = s.currency_symbol;
    if (co2Input) co2Input.value = s.co2_emission_factor;
    if (delayInput) delayInput.value = s.shutdown_delay_threshold_min;
    if (contamInput) contamInput.value = s.ai_contamination_rate;
    if (addon) addon.textContent = s.currency_symbol;

    const otInput = document.getElementById('set-overload-tolerance');
    const fstInput = document.getElementById('set-frozen-threshold');
    if (otInput && s.max_overload_tolerance_pct !== undefined) otInput.value = s.max_overload_tolerance_pct;
    if (fstInput && s.frozen_sensor_threshold !== undefined) fstInput.value = s.frozen_sensor_threshold;

  } catch (err) {
    console.error('Failed loading settings:', err);
  }
}

function initSettingsForm() {
  const form = document.getElementById('settings-form');
  const btnReset = document.getElementById('btn-reset-settings-defaults');
  const curSelect = document.getElementById('set-currency-symbol');
  const addon = document.getElementById('currency-addon');

  if (curSelect && addon) {
    curSelect.addEventListener('change', (e) => {
      addon.textContent = e.target.value;
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        diesel_price_per_litre: parseFloat(document.getElementById('set-diesel-price').value),
        currency_symbol: document.getElementById('set-currency-symbol').value,
        co2_emission_factor: parseFloat(document.getElementById('set-co2-factor').value),
        shutdown_delay_threshold_min: parseFloat(document.getElementById('set-delay-threshold').value),
        ai_contamination_rate: parseFloat(document.getElementById('set-contamination').value),
        max_overload_tolerance_pct: parseFloat(document.getElementById('set-overload-tolerance').value || 115),
        frozen_sensor_threshold: parseInt(document.getElementById('set-frozen-threshold').value || 4)
      };

      try {
        const res = await apiFetch('/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        showToast(res.message || 'System settings saved successfully!', 'success');
        loadSystemSettings();
      } catch (err) {
        showToast(`Failed saving settings: ${err.message}`, 'error');
      }
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      document.getElementById('set-diesel-price').value = 94.50;
      document.getElementById('set-currency-symbol').value = '₹';
      document.getElementById('set-co2-factor').value = 2.68;
      document.getElementById('set-delay-threshold').value = 10;
      document.getElementById('set-contamination').value = 0.08;
      const ot = document.getElementById('set-overload-tolerance');
      const fst = document.getElementById('set-frozen-threshold');
      if (ot) ot.value = 115;
      if (fst) fst.value = 4;
      if (addon) addon.textContent = '₹';
      showToast('Settings reset to defaults. Click Save to apply.', 'info');
    });
  }
}

// ============================================================================
// 15. MODALS & DRAWERS (LOG OPERATION, MAINTENANCE, TELEMETRY DRAWER)
// ============================================================================
function initModalsAndDrawers() {
  const modalLog = document.getElementById('modal-log-operation');
  const modalService = document.getElementById('modal-service-log');
  const drawerBackdrop = document.getElementById('drawer-backdrop');

  const btnOpenLog = document.getElementById('btn-open-log-modal');
  const btnCloseLog = document.getElementById('modal-close-btn');
  const btnCancelLog = document.getElementById('btn-cancel-log');
  const formLog = document.getElementById('form-log-operation');

  const btnOpenService = document.getElementById('btn-open-service-modal');
  const btnCloseService = document.getElementById('service-modal-close-btn');
  const btnCancelService = document.getElementById('btn-cancel-service');
  const formService = document.getElementById('form-service-log');

  const btnCloseDrawer = document.getElementById('drawer-close-btn');

  // Set default dates
  const logDateInput = document.getElementById('log-date');
  if (logDateInput) {
    logDateInput.value = new Date().toISOString().split('T')[0];
  }

  // Open Log Operation
  if (btnOpenLog && modalLog) {
    btnOpenLog.addEventListener('click', () => modalLog.classList.remove('hidden'));
  }
  const closeLog = () => { if (modalLog) modalLog.classList.add('hidden'); };
  if (btnCloseLog) btnCloseLog.addEventListener('click', closeLog);
  if (btnCancelLog) btnCancelLog.addEventListener('click', closeLog);

  // Open Service Modal
  if (btnOpenService && modalService) {
    btnOpenService.addEventListener('click', () => modalService.classList.remove('hidden'));
  }
  const closeService = () => { if (modalService) modalService.classList.add('hidden'); };
  if (btnCloseService) btnCloseService.addEventListener('click', closeService);
  if (btnCancelService) btnCancelService.addEventListener('click', closeService);

  const modalExplain = document.getElementById('modal-explain-anomaly');
  const btnCloseExplain = document.getElementById('explain-modal-close-btn');
  const closeExplain = () => { if (modalExplain) modalExplain.classList.add('hidden'); };
  if (btnCloseExplain) btnCloseExplain.addEventListener('click', closeExplain);

  // Close Drawer
  const closeDrawer = () => { if (drawerBackdrop) drawerBackdrop.classList.add('hidden'); };
  if (btnCloseDrawer) btnCloseDrawer.addEventListener('click', closeDrawer);

  window.addEventListener('click', (e) => {
    if (e.target === modalLog) closeLog();
    if (e.target === modalService) closeService();
    if (e.target === modalExplain) closeExplain();
    if (e.target === drawerBackdrop) closeDrawer();
  });

  // Data Quality filter listeners
  const sevSelectDq = document.getElementById('select-dq-severity');
  const unitSelectDq = document.getElementById('select-dq-unit');
  if (sevSelectDq) sevSelectDq.addEventListener('change', loadDataQualityDashboard);
  if (unitSelectDq) unitSelectDq.addEventListener('change', loadDataQualityDashboard);

  // Submit Log Operation
  if (formLog) {
    formLog.addEventListener('submit', async (e) => {
      e.preventDefault();

      const dgId = document.getElementById('log-dg-id').value;
      const capMap = { 'DG-101': 250, 'DG-102': 125, 'DG-103': 500, 'DG-104': 62.5 };

      const payload = {
        dg_id: dgId,
        capacity_kva: capMap[dgId] || 125,
        date: document.getElementById('log-date').value,
        start_time: document.getElementById('log-start-time').value,
        stop_time: document.getElementById('log-stop-time').value,
        mains_restored_time: document.getElementById('log-mains-time').value || '',
        load_kw: parseFloat(document.getElementById('log-load-kw').value),
        fuel_used_litres: parseFloat(document.getElementById('log-fuel-litres').value),
        notes: document.getElementById('log-notes').value || 'Operator logged operation'
      };

      try {
        const res = await apiFetch('/records', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        showToast(`Operation registered! Record ID: ${res.record.record_id}`, 'success');
        closeLog();
        formLog.reset();
        if (logDateInput) logDateInput.value = new Date().toISOString().split('T')[0];

        loadGeneratorRecords();
        loadGeneratorFleetCards();
      } catch (err) {
        showToast(`Validation error: ${err.message}`, 'error');
      }
    });
  }

  // Submit Service Log
  if (formService) {
    formService.addEventListener('submit', async (e) => {
      e.preventDefault();

      const payload = {
        dg_id: document.getElementById('service-dg-id').value,
        service_type: document.getElementById('service-type-input').value,
        technician: document.getElementById('service-technician').value,
        hours: parseFloat(document.getElementById('service-hours').value),
        notes: document.getElementById('service-notes').value
      };

      try {
        const res = await apiFetch('/maintenance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        showToast(res.message || 'Service log recorded successfully', 'success');
        closeService();
        formService.reset();
        loadMaintenanceData();
      } catch (err) {
        showToast(`Error saving service log: ${err.message}`, 'error');
      }
    });
  }
}

// Generator Drawer Telemetry Inspection
async function openGeneratorDrawer(dgId) {
  const drawer = document.getElementById('drawer-backdrop');
  const title = document.getElementById('drawer-title');
  const sub = document.getElementById('drawer-subtitle');
  const body = document.getElementById('drawer-content');
  if (!drawer || !body) return;

  try {
    const data = await apiFetch(`/generators/${dgId}`);
    if (data.status !== 'success') return;
    const g = data.generator;
    const t = g.telemetry || {};

    title.textContent = `Generator ${g.dg_id} Telemetry`;
    sub.textContent = `${g.capacity_kva} kVA Prime Rating &bull; ${t.running ? 'Running' : 'Standby'}`;

    body.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="background: #f8fafc; border: 1px solid var(--border-subtle); padding: 14px; border-radius: var(--radius-md);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 11px; text-transform: uppercase; font-weight: 600; color: var(--text-muted);">Current Operating State</span>
            ${t.running ? '<span class="badge-status-running">Running (On Load)</span>' : '<span class="badge-status-standby">Standby Ready</span>'}
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12.5px;">
            <div><strong>Electrical Load:</strong> ${t.load_pct || 0}%</div>
            <div><strong>Fuel Tank Level:</strong> ${t.fuel_pct || 80}%</div>
            <div><strong>Coolant Temp:</strong> ${t.temp_c || 28}°C</div>
            <div><strong>Bearing Vibration:</strong> ${t.vib_mms || 0.0} mm/s</div>
            <div><strong>Lube Oil Pressure:</strong> ${t.oil_pressure_bar || 0.0} bar</div>
            <div><strong>Rated Capacity:</strong> ${g.capacity_kva} kVA</div>
          </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 6px;">
          <h4 style="font-size: 13px; font-weight: 600;">Fleet Performance Aggregates</h4>
          <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-subtle);">
            <span style="color: var(--text-muted);">Total Operating Cycles:</span>
            <strong>${g.total_runs} runs</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-subtle);">
            <span style="color: var(--text-muted);">Cumulative Runtime Hours:</span>
            <strong>${g.total_runtime_hours} hrs</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-subtle);">
            <span style="color: var(--text-muted);">Cumulative Fuel Burned:</span>
            <strong>${g.total_fuel_litres.toLocaleString()} Litres</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-subtle);">
            <span style="color: var(--text-muted);">Average Fuel Consumption Rate:</span>
            <strong>${g.avg_fuel_per_hour} L/hour</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-subtle);">
            <span style="color: var(--text-muted);">AI Outliers Flagged:</span>
            <span class="badge ${g.anomalies_count > 0 ? 'badge-critical' : 'badge-normal'}">${g.anomalies_count} incidents</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0;">
            <span style="color: var(--text-muted);">Shutdown Delay Events:</span>
            <strong>${g.shutdown_delays_count} occurrences</strong>
          </div>
        </div>

        <div class="mt-2">
          <h4 style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Recent Operational Cycles</h4>
          <div style="display: flex; flex-direction: column; gap: 6px;">
            ${(g.recent_records || []).slice(0, 4).map((r) => `
              <div style="padding: 8px 10px; background: #ffffff; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); font-size: 11.5px;">
                <div style="display: flex; justify-content: space-between;">
                  <strong>${escapeHtml(r.date)} &bull; ${escapeHtml(r.start_time)}</strong>
                  <span>${r.runtime_min} min</span>
                </div>
                <div style="color: var(--text-muted); margin-top: 2px;">
                  Load: ${r.load_kw} kW &bull; Fuel: ${r.fuel_used_litres} L (${(r.fuel_used_litres / (r.runtime_min / 60)).toFixed(1)} L/h)
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    drawer.classList.remove('hidden');
  } catch (err) {
    showToast(`Failed loading generator telemetry: ${err.message}`, 'error');
  }
}

// Record Detail Drawer
function openRecordDetailDrawer(r) {
  const drawer = document.getElementById('drawer-backdrop');
  const title = document.getElementById('drawer-title');
  const sub = document.getElementById('drawer-subtitle');
  const body = document.getElementById('drawer-content');
  if (!drawer || !body) return;

  title.textContent = `Record ${r.record_id}`;
  sub.textContent = `${r.dg_id} &bull; ${r.date} &bull; ${r.runtime_min} Minutes`;

  const burnRate = (r.runtime_min > 0) ? ((r.fuel_used_litres / (r.runtime_min / 60)).toFixed(2)) : '0.00';
  const cost = (r.fuel_used_litres * state.dieselPrice).toFixed(2);
  const co2 = (r.fuel_used_litres * state.emissionFactor).toFixed(2);

  body.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 16px;">
      <div style="background: #f8fafc; border: 1px solid var(--border-subtle); padding: 14px; border-radius: var(--radius-md);">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12.5px;">
          <div><strong>Generator Unit:</strong> <span class="badge-dg">${escapeHtml(r.dg_id)}</span></div>
          <div><strong>Capacity:</strong> ${r.capacity_kva} kVA</div>
          <div><strong>Start Time:</strong> ${escapeHtml(r.start_time)}</div>
          <div><strong>Stop Time:</strong> ${escapeHtml(r.stop_time)}</div>
          <div><strong>Mains Restored:</strong> ${r.mains_restored_time ? escapeHtml(r.mains_restored_time) : 'N/A'}</div>
          <div><strong>Shutdown Delay:</strong> ${r.shutdown_delay_min > 0 ? `<strong class="text-amber">${r.shutdown_delay_min} min</strong>` : 'Prompt (0 min)'}</div>
          <div><strong>Electrical Load:</strong> ${r.load_kw} kW</div>
          <div><strong>Diesel Burned:</strong> <strong>${r.fuel_used_litres} L</strong></div>
          <div><strong>Specific Burn Rate:</strong> ${burnRate} L/h</div>
          <div><strong>Estimated Cost:</strong> ${state.currency} ${Number(cost).toLocaleString()}</div>
          <div><strong>CO2 Emissions:</strong> ${Number(co2).toLocaleString()} kg</div>
          <div><strong>Dataset Status:</strong> ${escapeHtml(r.ground_truth_label || 'NORMAL')}</div>
        </div>
      </div>

      <div>
        <h4 style="font-size: 13px; font-weight: 600; margin-bottom: 6px;">Telemetry Diagnostic Notes</h4>
        <div style="background: #ffffff; border: 1px solid var(--border-subtle); padding: 12px; border-radius: var(--radius-sm); font-size: 12px; color: var(--text-secondary);">
          ${escapeHtml(r.notes || 'Normal operating cycle within expected nominal parameters.')}
        </div>
      </div>

      <div style="font-size: 11px; color: var(--text-muted); border-top: 1px solid var(--border-subtle); padding-top: 10px;">
        <i class="fa-solid fa-tag"></i> Telemetry Classification: Synthetic demonstration log generated for academic mini-project.
      </div>
    </div>
  `;

  drawer.classList.remove('hidden');
}

// ============================================================================
// 16. UTILITY FUNCTIONS
// ============================================================================
function destroyChart(name) {
  if (state.charts[name]) {
    state.charts[name].destroy();
    delete state.charts[name];
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  let icon = 'fa-circle-info';
  if (type === 'success') icon = 'fa-circle-check';
  if (type === 'error') icon = 'fa-triangle-exclamation';

  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.22s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// ============================================================================
// PHASE 1 ADVANCED IMPROVEMENT FUNCTIONS
// ============================================================================

// --- 1. EXPLAINABLE AI ANOMALY INSPECTION MODAL ---
async function openAnomalyExplanationModal(recordId) {
  const modal = document.getElementById('modal-explain-anomaly');
  const body = document.getElementById('explain-modal-body');
  const subtitle = document.getElementById('explain-record-subtitle');
  if (!modal || !body) return;

  modal.classList.remove('hidden');
  body.innerHTML = '<div class="text-center py-4 text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Fetching Explainable AI diagnostics...</div>';
  if (subtitle) subtitle.textContent = `Analyzing Record ${recordId}`;

  try {
    const data = await apiFetch(`/analysis/anomalies/${recordId}`);
    if (data.status !== 'success') {
      body.innerHTML = `<div class="callout-note text-rose">${escapeHtml(data.message || 'Diagnostic unavailable')}</div>`;
      return;
    }

    const isAnom = data.ai_status === 'ANOMALY';
    const scorePill = isAnom
      ? `<span class="explain-score-pill"><i class="fa-solid fa-triangle-exclamation"></i> Outlier Score: ${data.anomaly_score} (${data.anomaly_severity_percent}% severity)</span>`
      : `<span class="explain-score-pill normal"><i class="fa-solid fa-circle-check"></i> Baseline Score: ${data.anomaly_score} (Normal)</span>`;

    const r = data.relevant_readings || {};
    const ctx = data.comparison_context || {};
    const indicators = data.supporting_indicators || [];
    const steps = data.suggested_inspection_steps || [];

    body.innerHTML = `
      <div class="explain-diag-header">
        <div>
          <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${escapeHtml(data.dg_id)} &bull; <code>${escapeHtml(data.record_id)}</code></div>
          <div style="font-size: 12px; color: var(--text-muted);"><i class="fa-regular fa-clock"></i> Timestamp: ${escapeHtml(data.timestamp)}</div>
        </div>
        <div>${scorePill}</div>
      </div>

      <div class="explain-grid-2col">
        <!-- Col 1: Measured Telemetry Readings -->
        <div class="explain-section-box">
          <div class="explain-sec-title"><i class="fa-solid fa-gauge-high text-blue"></i> Measured Telemetry Readings</div>
          <div class="explain-reading-list">
            <div class="explain-reading-row"><span>Operating Runtime:</span><strong>${r.runtime_min !== undefined ? r.runtime_min + ' min' : '&mdash;'}</strong></div>
            <div class="explain-reading-row"><span>Electrical Load:</span><strong>${r.load_kw !== undefined ? r.load_kw + ' kW' : '&mdash;'}</strong></div>
            <div class="explain-reading-row"><span>Load Percentage:</span><strong>${r.load_factor_pct !== undefined ? r.load_factor_pct + '%' : '&mdash;'}</strong></div>
            <div class="explain-reading-row"><span>Fuel Consumed:</span><strong>${r.fuel_used_litres !== undefined ? r.fuel_used_litres + ' L' : '&mdash;'}</strong></div>
            <div class="explain-reading-row"><span>Calculated Burn Rate:</span><strong>${r.fuel_rate_lph !== undefined ? r.fuel_rate_lph + ' L/h' : '&mdash;'}</strong></div>
            ${r.temperature_c !== null && r.temperature_c !== undefined ? `<div class="explain-reading-row"><span>Coolant Temp:</span><strong>${r.temperature_c} °C</strong></div>` : ''}
            ${r.vibration_mm_s !== null && r.vibration_mm_s !== undefined ? `<div class="explain-reading-row"><span>Vibration Level:</span><strong>${r.vibration_mm_s} mm/s</strong></div>` : ''}
          </div>
        </div>

        <!-- Col 2: Comparable-Load Baseline -->
        <div class="explain-section-box">
          <div class="explain-sec-title"><i class="fa-solid fa-chart-line text-teal"></i> Historical Comparison Context</div>
          <div class="explain-reading-list">
            <div class="explain-reading-row"><span>Operating Band:</span><strong>${escapeHtml(ctx.load_band || 'Standard Prime')}</strong></div>
            <div class="explain-reading-row"><span>Comparison Records:</span><strong>${ctx.comparison_records_count || 0} runs</strong></div>
            <div class="explain-reading-row"><span>Group Median Fuel Rate:</span><strong>${ctx.group_median_fuel_rate_lph ? ctx.group_median_fuel_rate_lph + ' L/h' : '&mdash;'}</strong></div>
            <div class="explain-reading-row"><span>Group Average Fuel Rate:</span><strong>${ctx.group_avg_fuel_rate_lph ? ctx.group_avg_fuel_rate_lph + ' L/h' : '&mdash;'}</strong></div>
            <div class="explain-reading-row"><span>Baseline Range:</span><strong>${ctx.group_min_fuel_rate_lph ? ctx.group_min_fuel_rate_lph + ' &ndash; ' + ctx.group_max_fuel_rate_lph + ' L/h' : '&mdash;'}</strong></div>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 8px;">
            <i class="fa-solid fa-circle-info"></i> ${escapeHtml(ctx.historical_comparison_note || '')}
          </div>
        </div>
      </div>

      <!-- Supporting Rule Indicators -->
      <div class="explain-section-box" style="margin-bottom: 16px;">
        <div class="explain-sec-title"><i class="fa-solid fa-clipboard-check text-amber"></i> Transparent Supporting Rule Checks</div>
        <ul class="explain-indicators-list">
          ${indicators.length > 0 ? indicators.map(ind => `<li class="explain-indicator-item"><i class="fa-solid fa-caret-right"></i> ${escapeHtml(ind)}</li>`).join('') : '<li class="text-muted">No deterministic rule boundary exceeded. Flagged purely by multivariate correlation.</li>'}
        </ul>
      </div>

      <!-- Suggested Investigation Steps -->
      <div class="explain-section-box">
        <div class="explain-sec-title"><i class="fa-solid fa-screwdriver-wrench text-blue"></i> Suggested Engineering Inspection Steps</div>
        <ul class="explain-indicators-list">
          ${steps.map(step => `<li class="explain-step-item"><i class="fa-solid fa-check"></i> ${escapeHtml(step)}</li>`).join('')}
        </ul>
      </div>

      <!-- Scientific Disclaimer -->
      <div class="explain-disclaimer-banner">
        <i class="fa-solid fa-triangle-exclamation text-amber" style="margin-top: 2px;"></i>
        <span>${escapeHtml(data.disclaimer)}</span>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div class="callout-note text-rose">Failed loading diagnostic: ${escapeHtml(err.message)}</div>`;
  }
}

// --- 2. MAINS RESTORATION & SHUTDOWN DELAY INTELLIGENCE ---
async function loadShutdownDelayIntelligence() {
  const tbody = document.getElementById('tbody-shutdown-delay-events');
  const countEl = document.getElementById('delay-kpi-count');
  const fuelEl = document.getElementById('delay-kpi-fuel');
  const costEl = document.getElementById('delay-kpi-cost');
  const thEl = document.getElementById('delay-kpi-threshold');
  const ongoingWrap = document.getElementById('ongoing-delays-banner-wrap');
  if (!tbody) return;

  try {
    const q = getFilterQueryParams();
    const res = await apiFetch(`/analysis/shutdown-delay?${q}`);
    if (res.status !== 'success') return;

    const { summary, events, ongoing_delays } = res.analysis;

    if (countEl) countEl.textContent = summary.excess_delay_events_count;
    if (fuelEl) fuelEl.textContent = `${summary.total_avoidable_fuel_litres} L`;
    if (costEl) costEl.textContent = `${state.currency} ${summary.total_avoidable_cost.toLocaleString()}`;
    if (thEl) thEl.textContent = `${summary.configured_threshold_min} min`;

    // Ongoing delays pills
    if (ongoingWrap) {
      if (ongoing_delays && ongoing_delays.length > 0) {
        ongoingWrap.innerHTML = ongoing_delays.map(od => `
          <span class="badge-status-ongoing">
            <i class="fa-solid fa-triangle-exclamation"></i> ${escapeHtml(od.dg_id)}: Ongoing post-mains run (${od.elapsed_delay_min} min elapsed)
          </span>
        `).join(' ');
      } else {
        ongoingWrap.innerHTML = '<span class="foot-pill pill-online"><i class="fa-solid fa-circle-check"></i> No ongoing post-mains delays</span>';
      }
    }

    if (!events || events.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4 text-muted">No shutdown delay records in selected period.</td></tr>';
      return;
    }

    tbody.innerHTML = events.slice(0, 15).map(e => {
      const delayBadge = e.exceeds_threshold
        ? `<span class="badge badge-critical">${e.shutdown_delay_min} min</span>`
        : (e.shutdown_delay_min !== null ? `<span>${e.shutdown_delay_min} min</span>` : `<span class="badge badge-warning">${escapeHtml(e.delay_status)}</span>`);

      const avoidableFuel = e.avoidable_fuel_litres > 0 ? `<strong class="text-rose tabular-num">${e.avoidable_fuel_litres} L</strong>` : `&mdash;`;
      const avoidableCost = e.avoidable_cost > 0 ? `<strong class="text-rose tabular-num">${state.currency} ${e.avoidable_cost.toLocaleString()}</strong>` : `&mdash;`;

      return `
        <tr>
          <td><code>${escapeHtml(e.record_id)}</code></td>
          <td><span class="badge-dg">${escapeHtml(e.dg_id)}</span></td>
          <td>${escapeHtml(e.date)}</td>
          <td>${escapeHtml(e.timeline.generator_started || e.start_time)}</td>
          <td><strong class="text-teal">${escapeHtml(e.mains_restored_time)}</strong></td>
          <td>${escapeHtml(e.stop_time)}</td>
          <td>${delayBadge}</td>
          <td>${avoidableFuel}</td>
          <td>${avoidableCost}</td>
          <td style="font-size: 11.5px; max-width: 280px;" class="text-muted">${escapeHtml(e.quality_note)}</td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    console.error('Failed loading shutdown delays:', err);
  }
}

// --- 3. FUEL EFFICIENCY ANALYSIS & BENCHMARKS ---
async function loadFuelEfficiencyAnalysis() {
  const bracketsWrap = document.getElementById('load-brackets-container');
  const tbodyUnusual = document.getElementById('tbody-unusual-fuel');
  const countBadge = document.getElementById('unusual-fuel-count-badge');
  if (!bracketsWrap && !tbodyUnusual) return;

  try {
    const q = getFilterQueryParams();
    const res = await apiFetch(`/analysis/fuel-efficiency?${q}`);
    if (res.status !== 'success') return;

    const { summary, load_bracket_baselines, unusual_consumption_records } = res.analysis;

    // 1. Render ISO 8528 Load Brackets
    if (bracketsWrap && load_bracket_baselines) {
      bracketsWrap.innerHTML = load_bracket_baselines.map(b => `
        <div class="load-bracket-card">
          <span class="bracket-card-tag">${escapeHtml(b.bracket_name.split(' (')[0])}</span>
          <div class="bracket-card-rate">${b.median_fuel_rate_lph > 0 ? b.median_fuel_rate_lph + ' L/h' : '&mdash;'}</div>
          <div style="font-size: 11px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
            ${b.records_count} runs &bull; ${b.avg_load_pct}% avg load
          </div>
          <span class="bracket-card-desc">${escapeHtml(b.efficiency_desc)}</span>
        </div>
      `).join('');
    }

    // 2. Render Statistical Unusual Fuel Consumption Table
    if (countBadge) countBadge.textContent = `${summary.unusual_fuel_records_count} Outliers Flagged`;

    if (tbodyUnusual) {
      if (!unusual_consumption_records || unusual_consumption_records.length === 0) {
        tbodyUnusual.innerHTML = '<tr><td colspan="11" class="text-center py-4 text-muted">No unusual fuel burn rates detected relative to comparable load brackets.</td></tr>';
      } else {
        tbodyUnusual.innerHTML = unusual_consumption_records.map(u => `
          <tr>
            <td><code>${escapeHtml(u.record_id)}</code></td>
            <td><span class="badge-dg">${escapeHtml(u.dg_id)}</span></td>
            <td>${escapeHtml(u.date)}</td>
            <td><span class="tabular-num">${u.load_kw}</span> kW</td>
            <td><strong>${u.load_pct}%</strong></td>
            <td><span class="tabular-num">${u.fuel_used_litres}</span> L</td>
            <td><strong class="text-rose tabular-num">${u.fuel_rate_lph} L/h</strong></td>
            <td>${escapeHtml(u.comparison_group.split(' (')[0])}</td>
            <td><span class="tabular-num">${u.group_median_rate_lph} L/h</span></td>
            <td><span class="badge badge-critical">${escapeHtml(u.deviation_percent)}</span></td>
            <td style="font-size: 11.5px; max-width: 280px;" class="text-muted">${escapeHtml(u.note)}</td>
          </tr>
        `).join('');
      }
    }
  } catch (err) {
    console.error('Failed loading fuel efficiency analysis:', err);
  }
}

// --- 4. DATA QUALITY MONITORING DASHBOARD ---
async function loadDataQualityDashboard() {
  const scoreNum = document.getElementById('dq-health-score');
  const scoreStatus = document.getElementById('dq-health-status');
  const totalChecked = document.getElementById('dq-total-checked');
  const validCount = document.getElementById('dq-valid-count');
  const warningsCount = document.getElementById('dq-warnings-count');
  const invalidCount = document.getElementById('dq-invalid-count');
  const tbodyIssues = document.getElementById('tbody-data-quality-issues');
  if (!scoreNum && !tbodyIssues) return;

  try {
    // 1. Fetch Summary
    const sumRes = await apiFetch('/data-quality/summary');
    if (sumRes.status === 'success') {
      const s = sumRes.data_quality_summary;
      if (scoreNum) scoreNum.textContent = `${s.data_health_score_pct}%`;
      if (scoreStatus) {
        scoreStatus.textContent = s.data_health_score_pct >= 90
          ? 'Sensor network integrity clean'
          : (s.data_health_score_pct >= 75 ? 'Moderate warnings observed' : 'Sensor attention required');
      }
      if (totalChecked) totalChecked.textContent = s.total_checked;
      if (validCount) validCount.textContent = s.valid_records;
      if (warningsCount) warningsCount.textContent = s.records_with_warnings;
      if (invalidCount) invalidCount.textContent = s.invalid_records;
    }

    // 2. Fetch Issues with filters
    const sevSelect = document.getElementById('select-dq-severity');
    const unitSelect = document.getElementById('select-dq-unit');
    const sev = sevSelect ? sevSelect.value : 'ALL';
    const unit = unitSelect ? unitSelect.value : 'ALL';

    const issuesRes = await apiFetch(`/data-quality/issues?dg_id=${unit}&severity=${sev}`);
    if (issuesRes.status === 'success' && tbodyIssues) {
      const issues = issuesRes.issues || [];
      if (issues.length === 0) {
        tbodyIssues.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No data quality issues match the selected filters.</td></tr>';
        return;
      }

      tbodyIssues.innerHTML = issues.map(i => {
        let pillClass = 'severity-pill-info';
        if (i.severity === 'CRITICAL') pillClass = 'severity-pill-critical';
        else if (i.severity === 'WARNING') pillClass = 'severity-pill-warning';

        return `
          <tr>
            <td><code>${escapeHtml(i.record_id)}</code></td>
            <td><span class="badge-dg">${escapeHtml(i.dg_id)}</span></td>
            <td>${escapeHtml(i.timestamp)}</td>
            <td><code>${escapeHtml(i.field_name)}</code></td>
            <td><span class="badge badge-info">${escapeHtml(i.issue_category)}</span></td>
            <td><span class="${pillClass}">${escapeHtml(i.severity)}</span></td>
            <td style="font-size: 11.5px; max-width: 320px;">${escapeHtml(i.explanation)}</td>
            <td>${i.excluded_from_analysis ? '<span class="badge badge-critical">Excluded</span>' : '<span class="badge badge-normal">Tolerated</span>'}</td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    showToast(`Error loading data quality dashboard: ${err.message}`, 'error');
  }
}
