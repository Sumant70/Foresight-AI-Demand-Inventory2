/**
 * FORESIGHT AI — Demand & Inventory Intelligence Platform
 * Production Enterprise SaaS Client Controller (Pure Vanilla JS, Zero SVG, Zero External CDN)
 */

const Foresight = {
  currentTab: "overview",
  overviewData: null,
  productsData: [],
  inventoryData: null,
  stockoutData: null,
  reorderData: null,
  analyticsData: null,
  qualityData: null,
  modelsData: null,
  dailySalesData: null,
  demandPeriod: "ALL", // '7D', '30D', '90D', 'ALL'
  forecastState: {
    sku: "SKU001",
    horizon: 14,
  },
  abcFilter: null,
  selectedStockoutSku: null,
  currentUser: null,
  csrfToken: null,
  usersList: [],
};

// Application Bootstrapper with Security Check
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupOverviewControls();
  setupForecastControls();
  setupInventoryControls();
  setupProductControls();
  setupReorderControls();
  checkAuthAndInit();
});

// -----------------------------------------------------------------
// 1. Navigation Controller
// -----------------------------------------------------------------
function setupNavigation() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  Foresight.currentTab = tabId;

  // Update Nav Buttons
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
  });

  // Update Panes
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === `tab-${tabId}`);
  });

  // Update Top Breadcrumb & Titles
  const tabTitles = {
    overview: { bc: "PLATFORM / OVERVIEW", title: "Executive Overview", desc: "Centralized visibility into sales demand velocity, warehouse inventory, and replenishment urgency." },
    forecast: { bc: "PLATFORM / DEMAND FORECAST", title: "Demand Forecasting", desc: "Understand expected future demand using historical sales patterns." },
    inventory: { bc: "PLATFORM / INVENTORY", title: "Inventory Health & Coverage", desc: "Real physical warehouse balances, daily demand burn velocity, and coverage run-out." },
    stockout: { bc: "OPERATIONS / STOCKOUT RISK", title: "Stockout Risk Assessment", desc: "Identify products requiring immediate replenishment attention before stockouts occur." },
    reorder: { bc: "OPERATIONS / REORDER", title: "Reorder Recommendations", desc: "Calculated replenishment quantities, safety stock buffers, and purchase schedules." },
    products: { bc: "PORTFOLIO / PRODUCTS", title: "Product Analytics & ABC/XYZ", desc: "Commercial SKU performance, Pareto revenue contribution, and 9-box inventory strategy." },
    quality: { bc: "AUDIT / DATA QUALITY", title: "Data Quality & Profiling", desc: "Comprehensive audit of ingested raw datasets, missing values, and field mappings." },
    models: { bc: "BENCHMARK / MODEL PERFORMANCE", title: "Model Performance & Benchmarks", desc: "Temporal holdout validation results, algorithm leaderboard, and residual accuracy metrics." },
    users: { bc: "ADMINISTRATION / USERS", title: "Team Accounts & Access Control", desc: "Provision corporate users, manage RBAC privileges, inspect lockouts, and reset credentials." },
    security: { bc: "GOVERNANCE / SECURITY", title: "Platform Security & Audit Trail", desc: "Real-time session metrics, cryptographic configuration verification, and tamper-evident authentication ledger." },
  };

  const info = tabTitles[tabId] || { bc: "PLATFORM", title: "Foresight AI", desc: "Demand & Inventory Intelligence" };
  const bcEl = document.getElementById("hdr-breadcrumb");
  const titleEl = document.getElementById("page-title");
  const descEl = document.getElementById("page-desc");

  if (bcEl) bcEl.textContent = info.bc;
  if (titleEl) titleEl.textContent = info.title;
  if (descEl) descEl.textContent = info.desc;

  // Lazy load tab data
  if (tabId === "forecast") loadForecastTab();
  if (tabId === "inventory" && !Foresight.inventoryData) loadInventoryTab();
  if (tabId === "stockout" && !Foresight.stockoutData) loadStockoutTab();
  if (tabId === "reorder" && !Foresight.reorderData) loadReorderTab();
  if (tabId === "products" && !Foresight.analyticsData) loadProductsTab();
  if (tabId === "quality" && !Foresight.qualityData) loadQualityTab();
  if (tabId === "models" && !Foresight.modelsData) loadModelsTab();
  if (tabId === "users") loadUsersTab();
  if (tabId === "security") fetchSecurityStatus();
}


// -----------------------------------------------------------------
// 2. Overview Tab Data Loading & Visualizations
// -----------------------------------------------------------------
async function loadInitialData() {
  try {
    const res = await fetch("/api/overview");
    const data = await res.json();
    Foresight.overviewData = data;
    renderOverviewTab(data);
  } catch (err) {
    console.error("Failed to load initial overview:", err);
  }
}

function setupOverviewControls() {
  // Period filter buttons: 7D, 30D, 90D, ALL
  document.querySelectorAll(".time-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      document.querySelectorAll(".time-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const period = btn.getAttribute("data-period");
      Foresight.demandPeriod = period;
      await updateDemandTrendChart(period);
    });
  });
}

function renderOverviewTab(data) {
  const kpi = data.kpis;
  document.getElementById("ov-total-products").textContent = kpi.total_products || "50";
  document.getElementById("ov-total-units").textContent = Number(kpi.total_units_sold).toLocaleString();
  document.getElementById("ov-total-revenue").textContent = "$" + (kpi.total_sales_revenue / 1e9).toFixed(2) + "B";
  document.getElementById("ov-inventory-value").textContent = "$" + (kpi.current_inventory_value / 1e6).toFixed(1) + "M";
  document.getElementById("ov-inventory-units").textContent = Number(kpi.current_inventory_units).toLocaleString();
  document.getElementById("ov-daily-demand").textContent = Number(kpi.avg_daily_demand).toFixed(1);
  document.getElementById("ov-stockout-risk").textContent = kpi.high_stockout_risk_count;

  // Segmented Inventory Health Bar
  const counts = data.stock_health_distribution || {};
  const totalTracked = (counts.Healthy || 0) + (counts["Low Stock"] || 0) + (counts.Critical || 0) + (counts.Overstock || 0) + (counts["Out of Stock"] || 0);
  if (totalTracked > 0) {
    const hPct = ((counts.Healthy || 0) / totalTracked * 100).toFixed(1);
    const lPct = ((counts["Low Stock"] || 0) / totalTracked * 100).toFixed(1);
    const cPct = ((counts.Critical || 0) / totalTracked * 100).toFixed(1);
    const oPct = ((counts.Overstock || 0) / totalTracked * 100).toFixed(1);

    const segContainer = document.getElementById("ov-segmented-health");
    if (segContainer) {
      segContainer.innerHTML = `
        <div class="segment segment-healthy" style="width: ${hPct}%" title="Healthy: ${counts.Healthy || 0} SKUs (${hPct}%)"></div>
        <div class="segment segment-low" style="width: ${lPct}%" title="Low Stock: ${counts['Low Stock'] || 0} SKUs (${lPct}%)"></div>
        <div class="segment segment-critical" style="width: ${cPct}%" title="Critical: ${counts.Critical || 0} SKUs (${cPct}%)"></div>
        <div class="segment segment-overstock" style="width: ${oPct}%" title="Overstock: ${counts.Overstock || 0} SKUs (${oPct}%)"></div>
      `;
    }

    document.getElementById("ov-count-healthy").textContent = `${counts.Healthy || 0} SKUs (${hPct}%)`;
    document.getElementById("ov-count-low").textContent = `${counts["Low Stock"] || 0} SKUs (${lPct}%)`;
    document.getElementById("ov-count-critical").textContent = `${counts.Critical || 0} SKUs (${cPct}%)`;
    document.getElementById("ov-count-overstock").textContent = `${counts.Overstock || 0} SKUs (${oPct}%)`;
    document.getElementById("ov-count-out").textContent = `${counts["Out of Stock"] || 0} SKUs`;
  }

  // Render Deterministic AI Insights
  renderInsights(data.insights);

  // Render Demand Trend Canvas (Initial: ALL 24 months)
  renderMonthlyDemandCanvas(data.monthly_sales);

  // Render Top Products Table (Overview)
  renderOverviewTopProducts(data.top_products);

  // Render Stockout Panel (Overview)
  renderOverviewStockoutPanel(data.top_products);
}

function renderInsights(insights) {
  const container = document.getElementById("ov-insights-container");
  if (!container || !insights) return;

  container.innerHTML = insights.map((ins) => `
    <div class="insight-item severity-${ins.severity}">
      <div class="insight-top-row">
        <span class="insight-cat">${escapeHtml(ins.category)}</span>
        <span class="insight-pill">${escapeHtml(ins.metric)}</span>
      </div>
      <div class="insight-heading">${escapeHtml(ins.headline)}</div>
      <div class="insight-desc">${escapeHtml(ins.detail)}</div>
    </div>
  `).join("");
}

function renderOverviewTopProducts(products) {
  const tbody = document.getElementById("ov-top-products-tbody");
  if (!tbody || !products) return;

  tbody.innerHTML = products.slice(0, 5).map((p, idx) => `
    <tr>
      <td><span class="text-muted">#${idx + 1}</span></td>
      <td><strong>${escapeHtml(p.product_name)}</strong></td>
      <td><span class="sku-badge" onclick="openSkuModal('${p.sku}')">${p.sku}</span></td>
      <td class="text-right">${Number(p.total_units_sold).toLocaleString()}</td>
      <td class="text-right">${Number(p.current_stock).toLocaleString()}</td>
      <td><span class="badge-status ${getStatusClass(p.stock_status)}"><span class="badge-status-dot"></span>${escapeHtml(p.stock_status)}</span></td>
    </tr>
  `).join("");
}

async function renderOverviewStockoutPanel(products) {
  const tbody = document.getElementById("ov-stockout-panel-tbody");
  if (!tbody) return;

  // Pull stockout risks if not already cached
  if (!Foresight.stockoutData) {
    const res = await fetch("/api/stockout");
    Foresight.stockoutData = await res.json();
  }

  const criticals = Foresight.stockoutData.risks.slice(0, 5);
  tbody.innerHTML = criticals.map((r) => `
    <tr>
      <td><span class="sku-badge" onclick="openSkuModal('${r.sku}')">${r.sku}</span></td>
      <td><strong>${escapeHtml(r.product_name)}</strong></td>
      <td class="text-right">${r.current_stock}</td>
      <td class="text-right"><strong>${r.days_until_stockout} d</strong></td>
      <td><span class="badge-status ${getRiskClass(r.risk_level)}"><span class="badge-status-dot"></span>${r.risk_level}</span></td>
    </tr>
  `).join("");
}

// -----------------------------------------------------------------
// 3. HTML5 Canvas Chart Renderers (Zero Libraries, Zero SVG)
// -----------------------------------------------------------------
async function updateDemandTrendChart(period) {
  if (period === "ALL") {
    if (Foresight.overviewData) {
      renderMonthlyDemandCanvas(Foresight.overviewData.monthly_sales);
    }
  } else {
    // Fetch daily sales if not already loaded
    if (!Foresight.dailySalesData) {
      const res = await fetch("/api/sales?period=daily");
      Foresight.dailySalesData = await res.json();
    }
    const days = period === "7D" ? 7 : (period === "30D" ? 30 : 90);
    const slice = Foresight.dailySalesData.slice(-days);
    renderDailyDemandCanvas(slice, period);
  }
}

function renderMonthlyDemandCanvas(monthlyData) {
  const canvas = document.getElementById("monthlyDemandCanvas");
  if (!canvas || !monthlyData || monthlyData.length === 0) return;
  const ctx = canvas.getContext("2d");
  const tooltip = document.getElementById("demandTooltip");

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = rect.width > 0 ? rect.width : 720;
  const height = 260;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 20, right: 20, bottom: 35, left: 55 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const maxVal = Math.max(...monthlyData.map((d) => d.units)) * 1.15;

  // Grid Lines
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "10px -apple-system, sans-serif";
  ctx.textAlign = "right";

  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (chartH / 4) * i;
    const val = Math.round(maxVal - (maxVal / 4) * i);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartW, y);
    ctx.stroke();
    ctx.fillText(Number(val).toLocaleString(), padding.left - 8, y + 3);
  }

  // Bars
  const barWidth = (chartW / monthlyData.length) * 0.65;
  const stepX = chartW / monthlyData.length;
  const barCoords = [];

  monthlyData.forEach((d, idx) => {
    const x = padding.left + idx * stepX + (stepX - barWidth) / 2;
    const barH = (d.units / maxVal) * chartH;
    const y = padding.top + chartH - barH;

    // Solid deep blue fill
    ctx.fillStyle = "#2563eb";
    ctx.fillRect(x, y, barWidth, barH);

    barCoords.push({ x, y, width: barWidth, height: barH, data: d });

    // X-axis month label every 3 months
    if (idx % 3 === 0 || idx === monthlyData.length - 1) {
      ctx.fillStyle = "#64748b";
      ctx.textAlign = "center";
      ctx.fillText(d.month.slice(2), x + barWidth / 2, padding.top + chartH + 16);
    }
  });

  // Attach mouse hover tooltip
  canvas.onmousemove = (e) => {
    const cRect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - cRect.left;
    const mouseY = e.clientY - cRect.top;

    const hit = barCoords.find((b) =>
      mouseX >= b.x && mouseX <= b.x + b.width && mouseY >= b.y && mouseY <= b.y + b.height
    );

    if (hit && tooltip) {
      tooltip.style.display = "block";
      tooltip.style.left = `${hit.x + hit.width / 2}px`;
      tooltip.style.top = `${hit.y - 32}px`;
      tooltip.innerHTML = `<strong>${hit.data.month}</strong>: ${Number(hit.data.units).toLocaleString()} units ($${(hit.data.revenue / 1e6).toFixed(1)}M)`;
    } else if (tooltip) {
      tooltip.style.display = "none";
    }
  };

  canvas.onmouseleave = () => {
    if (tooltip) tooltip.style.display = "none";
  };
}

function renderDailyDemandCanvas(dailyData, periodLabel) {
  const canvas = document.getElementById("monthlyDemandCanvas");
  if (!canvas || !dailyData || dailyData.length === 0) return;
  const ctx = canvas.getContext("2d");
  const tooltip = document.getElementById("demandTooltip");

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = rect.width > 0 ? rect.width : 720;
  const height = 260;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 20, right: 20, bottom: 35, left: 55 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const maxVal = Math.max(...dailyData.map((d) => d.units)) * 1.2;

  // Grid
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "10px -apple-system, sans-serif";
  ctx.textAlign = "right";

  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (chartH / 4) * i;
    const val = Math.round(maxVal - (maxVal / 4) * i);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartW, y);
    ctx.stroke();
    ctx.fillText(Number(val).toLocaleString(), padding.left - 8, y + 3);
  }

  // Draw Line
  const stepX = chartW / (dailyData.length - 1);
  const pointCoords = [];

  ctx.beginPath();
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2;

  dailyData.forEach((d, idx) => {
    const x = padding.left + idx * stepX;
    const y = padding.top + chartH - (d.units / maxVal) * chartH;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
    pointCoords.push({ x, y, data: d });
  });
  ctx.stroke();

  // X-axis labels
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  const interval = Math.max(1, Math.floor(dailyData.length / 7));
  for (let idx = 0; idx < dailyData.length; idx += interval) {
    const pt = pointCoords[idx];
    ctx.fillText(pt.data.date.slice(5), pt.x, padding.top + chartH + 16);
  }

  // Tooltip
  canvas.onmousemove = (e) => {
    const cRect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - cRect.left;

    // Find closest x
    let closest = pointCoords[0];
    let minDiff = Math.abs(mouseX - closest.x);
    for (const pt of pointCoords) {
      const diff = Math.abs(mouseX - pt.x);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }

    if (closest && minDiff < 20 && tooltip) {
      tooltip.style.display = "block";
      tooltip.style.left = `${closest.x}px`;
      tooltip.style.top = `${closest.y - 32}px`;
      tooltip.innerHTML = `<strong>${closest.data.date}</strong>: ${closest.data.units} units sold`;
    } else if (tooltip) {
      tooltip.style.display = "none";
    }
  };

  canvas.onmouseleave = () => {
    if (tooltip) tooltip.style.display = "none";
  };
}

function renderForecastCanvas(historyPoints, forecastPoints) {
  const canvas = document.getElementById("forecastCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const tooltip = document.getElementById("forecastTooltip");

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = rect.width > 0 ? rect.width : 920;
  const height = 300;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const padding = { top: 25, right: 25, bottom: 40, left: 50 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const allVals = [
    ...historyPoints.map((h) => h.actual),
    ...forecastPoints.map((f) => f.upper_bound),
    ...forecastPoints.map((f) => f.forecast),
  ];
  const maxVal = Math.max(...allVals, 10) * 1.2;

  const totalPoints = historyPoints.length + forecastPoints.length;
  const stepX = chartW / (totalPoints - 1);

  // Background Grid Lines
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "10px -apple-system, sans-serif";
  ctx.textAlign = "right";

  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (chartH / 4) * i;
    const val = Math.round(maxVal - (maxVal / 4) * i);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartW, y);
    ctx.stroke();
    ctx.fillText(val, padding.left - 8, y + 3);
  }

  // 1. Draw Confidence Interval Band
  ctx.beginPath();
  const forecastStartIndex = historyPoints.length - 1;

  for (let i = 0; i < forecastPoints.length; i++) {
    const idx = forecastStartIndex + i;
    const x = padding.left + idx * stepX;
    const val = forecastPoints[i].upper_bound;
    const y = padding.top + chartH - (val / maxVal) * chartH;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }

  for (let i = forecastPoints.length - 1; i >= 0; i--) {
    const idx = forecastStartIndex + i;
    const x = padding.left + idx * stepX;
    const val = Math.max(0, forecastPoints[i].lower_bound);
    const y = padding.top + chartH - (val / maxVal) * chartH;
    ctx.lineTo(x, y);
  }

  ctx.closePath();
  ctx.fillStyle = "rgba(16, 185, 129, 0.12)";
  ctx.fill();

  // 2. Draw Historical Actuals (Solid Blue Line)
  ctx.beginPath();
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2;
  const allCoords = [];

  historyPoints.forEach((pt, idx) => {
    const x = padding.left + idx * stepX;
    const y = padding.top + chartH - (pt.actual / maxVal) * chartH;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
    allCoords.push({ x, y, type: "actual", date: pt.date, val: pt.actual });
  });
  ctx.stroke();

  // 3. Draw Forecast Line (Dashed Green Line)
  ctx.beginPath();
  ctx.setLineDash([5, 4]);
  ctx.strokeStyle = "#059669";
  ctx.lineWidth = 2.5;

  const lastHist = historyPoints[historyPoints.length - 1];
  const lastX = padding.left + (historyPoints.length - 1) * stepX;
  const lastY = padding.top + chartH - (lastHist.actual / maxVal) * chartH;
  ctx.moveTo(lastX, lastY);

  forecastPoints.forEach((pt, i) => {
    const idx = forecastStartIndex + i;
    const x = padding.left + idx * stepX;
    const y = padding.top + chartH - (pt.forecast / maxVal) * chartH;
    ctx.lineTo(x, y);
    allCoords.push({ x, y, type: "forecast", date: pt.date, val: pt.forecast, lower: pt.lower_bound, upper: pt.upper_bound });
  });
  ctx.stroke();
  ctx.setLineDash([]);

  // X-axis Dates
  ctx.fillStyle = "#64748b";
  ctx.textAlign = "center";
  const interval = Math.max(1, Math.floor(totalPoints / 8));
  for (let idx = 0; idx < totalPoints; idx += interval) {
    const pt = allCoords[idx];
    if (pt) {
      ctx.fillText(pt.date.slice(5), pt.x, padding.top + chartH + 16);
    }
  }

  // Interactive Hover Tooltip
  canvas.onmousemove = (e) => {
    const cRect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - cRect.left;

    let closest = allCoords[0];
    let minDiff = Math.abs(mouseX - closest.x);
    for (const pt of allCoords) {
      const diff = Math.abs(mouseX - pt.x);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }

    if (closest && minDiff < 15 && tooltip) {
      tooltip.style.display = "block";
      tooltip.style.left = `${closest.x}px`;
      tooltip.style.top = `${closest.y - 36}px`;

      if (closest.type === "actual") {
        tooltip.innerHTML = `<strong>${closest.date}</strong> (Actual): ${closest.val} units`;
      } else {
        tooltip.innerHTML = `<strong>${closest.date}</strong> (Forecast): ${closest.val} units [${closest.lower} - ${closest.upper}]`;
      }
    } else if (tooltip) {
      tooltip.style.display = "none";
    }
  };

  canvas.onmouseleave = () => {
    if (tooltip) tooltip.style.display = "none";
  };
}

// -----------------------------------------------------------------
// 4. Demand Forecasting Tab
// -----------------------------------------------------------------
function setupForecastControls() {
  const skuSelect = document.getElementById("fc-sku-select");
  const catSelect = document.getElementById("fc-category-filter");

  if (skuSelect) {
    skuSelect.addEventListener("change", (e) => {
      Foresight.forecastState.sku = e.target.value;
      loadForecastTab();
    });
  }

  if (catSelect) {
    catSelect.addEventListener("change", (e) => {
      filterForecastSkuDropdown(e.target.value);
    });
  }

  document.querySelectorAll(".hz-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".hz-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      Foresight.forecastState.horizon = parseInt(btn.getAttribute("data-horizon"), 10);
      loadForecastTab();
    });
  });
}

function filterForecastSkuDropdown(category) {
  const select = document.getElementById("fc-sku-select");
  if (!select || !Foresight.productsData) return;

  select.innerHTML = "";
  const filtered = category === "ALL"
    ? Foresight.productsData
    : Foresight.productsData.filter((p) => p.category.toLowerCase() === category.toLowerCase());

  filtered.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.sku;
    opt.textContent = `${p.sku} — ${p.product_name} (${p.category})`;
    if (p.sku === Foresight.forecastState.sku) opt.selected = true;
    select.appendChild(opt);
  });

  if (filtered.length > 0 && !filtered.some((p) => p.sku === Foresight.forecastState.sku)) {
    Foresight.forecastState.sku = filtered[0].sku;
    loadForecastTab();
  }
}

async function loadForecastTab() {
  if (Foresight.productsData.length === 0) {
    const pRes = await fetch("/api/products");
    Foresight.productsData = await pRes.json();
    populateCategoryDropdowns();
    filterForecastSkuDropdown("ALL");
  }

  const { sku, horizon } = Foresight.forecastState;
  try {
    const res = await fetch(`/api/forecast?sku=${sku}&horizon=${horizon}`);
    const data = await res.json();
    renderForecastView(data);
  } catch (err) {
    console.error("Forecast error:", err);
  }
}

function renderForecastView(data) {
  if (!data || data.error) return;

  document.getElementById("fc-kpi-total-expected").textContent = `${Number(data.forecast.total_expected_demand).toLocaleString()} Units`;
  document.getElementById("fc-kpi-horizon-text").textContent = `${data.forecast.horizon_days} Days`;
  document.getElementById("fc-kpi-model").textContent = data.best_model;
  document.getElementById("fc-kpi-wape").textContent = `${data.metrics.wape || 0}%`;

  // Render Dual-series Canvas
  renderForecastCanvas(data.recent_history, data.forecast.points);

  // Render Day-by-Day Table
  const tbody = document.getElementById("fc-daily-tbody");
  let cumulative = 0;
  tbody.innerHTML = data.forecast.points.map((pt) => {
    cumulative += pt.forecast;
    const dateObj = new Date(pt.date);
    const dayName = dateObj.toLocaleDateString("en-US", { weekday: "short" });
    return `
      <tr>
        <td><strong>${pt.date}</strong></td>
        <td><span class="text-muted">${dayName}</span></td>
        <td class="text-right"><strong>${pt.forecast}</strong></td>
        <td class="text-right text-muted">${pt.lower_bound}</td>
        <td class="text-right text-muted">${pt.upper_bound}</td>
        <td class="text-right font-mono">${cumulative.toFixed(1)}</td>
      </tr>
    `;
  }).join("");
}

// -----------------------------------------------------------------
// 5. Inventory Intelligence Tab
// -----------------------------------------------------------------
function setupInventoryControls() {
  const search = document.getElementById("inv-search-input");
  const filter = document.getElementById("inv-status-filter");

  if (search) search.addEventListener("input", filterInventoryTable);
  if (filter) filter.addEventListener("change", filterInventoryTable);
}

async function loadInventoryTab() {
  try {
    const res = await fetch("/api/inventory");
    const data = await res.json();
    Foresight.inventoryData = data;
    renderInventoryTab(data);
  } catch (err) {
    console.error("Failed to load inventory:", err);
  }
}

function renderInventoryTab(data) {
  const kpi = data.summary;
  document.getElementById("inv-kpi-stock").textContent = Number(kpi.total_current_stock).toLocaleString();
  document.getElementById("inv-kpi-value").textContent = "$" + (kpi.total_inventory_value / 1e6).toFixed(1) + "M";
  document.getElementById("inv-kpi-critical").textContent = kpi.status_counts.Critical || 0;
  document.getElementById("inv-kpi-low").textContent = kpi.status_counts["Low Stock"] || 0;
  document.getElementById("inv-kpi-overstock").textContent = kpi.status_counts.Overstock || 0;

  filterInventoryTable();
}

function filterInventoryTable() {
  if (!Foresight.inventoryData) return;
  const search = (document.getElementById("inv-search-input").value || "").toLowerCase().trim();
  const statusFilter = document.getElementById("inv-status-filter").value;

  const items = Foresight.inventoryData.matrix.filter((item) => {
    const matchSearch = item.sku.toLowerCase().includes(search) ||
      item.product_name.toLowerCase().includes(search) ||
      item.category.toLowerCase().includes(search);
    const matchStatus = statusFilter === "ALL" || item.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const tbody = document.getElementById("inv-matrix-tbody");
  tbody.innerHTML = items.map((item) => `
    <tr>
      <td><strong>${escapeHtml(item.product_name)}</strong></td>
      <td><span class="sku-badge" onclick="openSkuModal('${item.sku}')">${item.sku}</span></td>
      <td class="text-right"><strong>${Number(item.current_stock).toLocaleString()}</strong></td>
      <td class="text-right">${item.avg_daily_demand}</td>
      <td class="text-right"><strong>${item.days_of_inventory} d</strong></td>
      <td><span class="badge-status ${getStatusClass(item.status)}"><span class="badge-status-dot"></span>${escapeHtml(item.status)}</span></td>
      <td class="text-right">${item.reorder_point}</td>
      <td class="text-right">${item.lead_time_days} d</td>
    </tr>
  `).join("");
}

// -----------------------------------------------------------------
// 6. Stockout Risk Tab & Split View Detail Panel
// -----------------------------------------------------------------
async function loadStockoutTab() {
  try {
    const res = await fetch("/api/stockout");
    const data = await res.json();
    Foresight.stockoutData = data;
    renderStockoutTab(data);
  } catch (err) {
    console.error("Failed to load stockout:", err);
  }
}

function renderStockoutTab(data) {
  const s = data.summary;
  document.getElementById("so-kpi-high").textContent = s.high_risk_count;
  document.getElementById("so-kpi-medium").textContent = s.medium_risk_count;
  document.getElementById("so-kpi-low").textContent = s.low_risk_count;

  const tbody = document.getElementById("so-table-tbody");
  tbody.innerHTML = data.risks.map((r, idx) => `
    <tr onclick="selectStockoutProduct('${r.sku}')" style="cursor: pointer;">
      <td><span class="sku-badge">${r.sku}</span></td>
      <td><strong>${escapeHtml(r.product_name)}</strong></td>
      <td class="text-right">${r.current_stock}</td>
      <td class="text-right"><strong>${r.days_until_stockout} d</strong></td>
      <td><span class="badge-status ${getRiskClass(r.risk_level)}"><span class="badge-status-dot"></span>${r.risk_level}</span></td>
    </tr>
  `).join("");

  // Auto select first high-risk SKU in detail view
  if (data.risks.length > 0) {
    selectStockoutProduct(data.risks[0].sku);
  }
}

function selectStockoutProduct(skuId) {
  if (!Foresight.stockoutData) return;
  const p = Foresight.stockoutData.risks.find((x) => x.sku === skuId);
  if (!p) return;

  Foresight.selectedStockoutSku = skuId;

  document.getElementById("so-det-title").textContent = `${p.sku} — ${p.product_name}`;
  document.getElementById("so-det-sub").textContent = `Category: ${p.category} | Lead Time: ${p.lead_time_days} Days`;

  const body = document.getElementById("so-det-body");
  body.innerHTML = `
    <div class="kpi-grid mb-4">
      <div class="kpi-card">
        <div class="kpi-label">CURRENT STOCK</div>
        <div class="kpi-metric">${p.current_stock}</div>
        <div class="kpi-context">Units on hand</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">14D FORECAST</div>
        <div class="kpi-metric">${p.forecast_demand_14d}</div>
        <div class="kpi-context">Expected run rate</div>
      </div>
      <div class="kpi-card ${p.risk_level === 'High' ? 'kpi-card-danger' : ''}">
        <div class="kpi-label">DAYS TO STOCKOUT</div>
        <div class="kpi-metric ${p.risk_level === 'High' ? 'text-danger' : ''}">${p.days_until_stockout} d</div>
        <div class="kpi-context">Coverage duration</div>
      </div>
    </div>

    <div class="card p-4 mb-4">
      <div class="callout-title">Risk Assessment &amp; Operational Cause</div>
      <p class="text-main mt-1 font-medium">${escapeHtml(p.explanation)}</p>
      <div class="chart-footer-meta mt-2">
        <span>Estimated Stockout Date: <strong>${p.estimated_stockout_date}</strong></span>
        <span>Lead Time Buffer: <strong>${p.lead_time_days} Days</strong></span>
      </div>
    </div>

    <button class="btn btn-secondary" onclick="openSkuModal('${p.sku}')">Inspect Complete SKU Analytics &rarr;</button>
  `;
}

// -----------------------------------------------------------------
// 7. Reorder Recommendations Tab
// -----------------------------------------------------------------
function setupReorderControls() {
  const override = document.getElementById("ro-lead-override");
  if (override) {
    override.addEventListener("change", (e) => {
      const val = e.target.value;
      const url = val === "ACTUAL" ? "/api/reorder" : `/api/reorder?lead_time=${val}`;
      fetchReorders(url);
    });
  }
}

async function loadReorderTab() {
  fetchReorders("/api/reorder");
}

async function fetchReorders(url) {
  try {
    const res = await fetch(url);
    const data = await res.json();
    Foresight.reorderData = data;
    renderReorderTab(data);
  } catch (err) {
    console.error("Failed to load reorders:", err);
  }
}

function renderReorderTab(data) {
  const s = data.summary;
  document.getElementById("ro-kpi-count").textContent = `${s.reorder_needed_count} SKUs`;
  document.getElementById("ro-kpi-units").textContent = Number(s.total_recommended_units).toLocaleString();
  document.getElementById("ro-kpi-cost").textContent = "$" + (s.total_reorder_cost / 1e6).toFixed(2) + "M";

  const tbody = document.getElementById("ro-table-tbody");
  tbody.innerHTML = data.recommendations.map((item) => `
    <tr>
      <td><span class="badge-status ${getUrgencyClass(item.urgency)}"><span class="badge-status-dot"></span>${item.urgency}</span></td>
      <td><strong>${escapeHtml(item.product_name)}</strong></td>
      <td><span class="sku-badge" onclick="openSkuModal('${item.sku}')">${item.sku}</span></td>
      <td class="text-right">${item.current_stock}</td>
      <td class="text-right">${item.calculated_reorder_point}</td>
      <td class="text-right"><strong>${item.recommended_quantity > 0 ? Number(item.recommended_quantity).toLocaleString() : "-"}</strong></td>
      <td>${item.suggested_reorder_date}</td>
      <td>${item.reorder_needed ? '<span class="text-danger font-bold">Action Needed</span>' : '<span class="text-muted">Adequate</span>'}</td>
    </tr>
  `).join("");
}

// -----------------------------------------------------------------
// 8. Product Analytics & ABC/XYZ Tab
// -----------------------------------------------------------------
function setupProductControls() {
  const search = document.getElementById("prod-search-input");
  const cat = document.getElementById("prod-cat-filter");
  if (search) search.addEventListener("input", filterProductCatalog);
  if (cat) cat.addEventListener("change", filterProductCatalog);
}

async function loadProductsTab() {
  try {
    const [anaRes, prodRes] = await Promise.all([
      fetch("/api/analytics"),
      fetch("/api/products"),
    ]);
    Foresight.analyticsData = await anaRes.json();
    Foresight.productsData = await prodRes.json();
    populateCategoryDropdowns();
    render9BoxMatrix(Foresight.analyticsData.matrix_9box);
    filterProductCatalog();
  } catch (err) {
    console.error("Failed to load products/analytics:", err);
  }
}

function render9BoxMatrix(matrix) {
  if (!matrix) return;
  Object.keys(matrix).forEach((cellKey) => {
    const lowerKey = cellKey.toLowerCase();
    const countEl = document.getElementById(`cell-${lowerKey}-count`);
    const revEl = document.getElementById(`cell-${lowerKey}-rev`);
    if (countEl) countEl.textContent = `${matrix[cellKey].count} SKUs`;
    if (revEl) revEl.textContent = "$" + (matrix[cellKey].revenue / 1e6).toFixed(1) + "M";
  });
}

function filterByAbcXyz(cellCode) {
  if (Foresight.abcFilter === cellCode) {
    clearAbcFilter();
    return;
  }
  Foresight.abcFilter = cellCode;

  // Highlight active box
  document.querySelectorAll(".matrix-box").forEach((b) => b.classList.remove("active"));
  const activeBox = document.getElementById(`box-${cellCode.toLowerCase()}`);
  if (activeBox) activeBox.classList.add("active");

  const chip = document.getElementById("active-abc-filter-chip");
  const name = document.getElementById("active-abc-name");
  if (chip && name) {
    name.textContent = cellCode;
    chip.style.display = "inline-flex";
  }

  filterProductCatalog();
}

function clearAbcFilter() {
  Foresight.abcFilter = null;
  document.querySelectorAll(".matrix-box").forEach((b) => b.classList.remove("active"));
  const chip = document.getElementById("active-abc-filter-chip");
  if (chip) chip.style.display = "none";
  filterProductCatalog();
}

function filterProductCatalog() {
  if (!Foresight.productsData) return;
  const search = (document.getElementById("prod-search-input").value || "").toLowerCase().trim();
  const catFilter = document.getElementById("prod-cat-filter").value;

  const items = Foresight.productsData.filter((p) => {
    const matchSearch = p.sku.toLowerCase().includes(search) || p.product_name.toLowerCase().includes(search);
    const matchCat = catFilter === "ALL" || p.category.toLowerCase() === catFilter.toLowerCase();
    const matchAbc = !Foresight.abcFilter || p.abc_xyz_class === Foresight.abcFilter;
    return matchSearch && matchCat && matchAbc;
  });

  const tbody = document.getElementById("prod-table-tbody");
  tbody.innerHTML = items.map((p) => `
    <tr>
      <td><span class="sku-badge" onclick="openSkuModal('${p.sku}')">${p.sku}</span></td>
      <td><strong>${escapeHtml(p.product_name)}</strong></td>
      <td>${escapeHtml(p.category)}</td>
      <td class="text-right">$${Number(p.cost_price).toFixed(2)}</td>
      <td class="text-right">$${Number(p.selling_price).toFixed(2)}</td>
      <td class="text-right">${Number(p.total_units_sold).toLocaleString()}</td>
      <td class="text-right font-mono"><strong>$${(p.total_revenue / 1e6).toFixed(1)}M</strong></td>
      <td class="text-right">${p.current_stock}</td>
      <td><span class="badge-status ${getStatusClass(p.stock_status)}"><span class="badge-status-dot"></span>${escapeHtml(p.stock_status)}</span></td>
      <td><span class="pill-badge">${p.abc_xyz_class}</span></td>
      <td><button class="text-link-btn" onclick="openSkuModal('${p.sku}')">Inspect</button></td>
    </tr>
  `).join("");
}

// -----------------------------------------------------------------
// 9. Data Quality & Model Performance Tabs
// -----------------------------------------------------------------
async function loadQualityTab() {
  try {
    const res = await fetch("/api/quality");
    const data = await res.json();
    Foresight.qualityData = data;
    renderQualityTab(data);
  } catch (err) {
    console.error("Failed to load quality:", err);
  }
}

function renderQualityTab(data) {
  // Raw profiles table
  const tbody = document.getElementById("dq-audit-tbody");
  const profiles = data.profiles || {};

  tbody.innerHTML = Object.keys(profiles).map((fname) => {
    const p = profiles[fname];
    const totalNulls = Object.values(p.null_counts || {}).reduce((a, b) => a + b, 0);
    const coverage = p.date_summary ? `${p.date_summary.min_date} to ${p.date_summary.max_date}` : "Full 50 Catalog";
    return `
      <tr>
        <td><code>${escapeHtml(fname)}</code></td>
        <td class="text-right"><strong>${Number(p.row_count).toLocaleString()}</strong></td>
        <td class="text-right">${p.column_count}</td>
        <td class="text-right">${totalNulls === 0 ? '<span class="text-success">0 Clean</span>' : totalNulls}</td>
        <td class="text-right">${p.duplicate_rows === 0 ? '<span class="text-success">0 Clean</span>' : p.duplicate_rows}</td>
        <td>${coverage}</td>
        <td><span class="badge-status status-healthy"><span class="badge-status-dot"></span>Verified Ingestion</span></td>
      </tr>
    `;
  }).join("");

  // Semantic field dictionary table
  const mapTbody = document.getElementById("dq-mapping-tbody");
  const fieldDefs = [
    { concept: "Date", file: "sales_daily.csv", col: "Date", type: "date", miss: "0%", status: "Verified" },
    { concept: "SKU Identifier", file: "sku_master.csv", col: "SKU", type: "string", miss: "0%", status: "Verified" },
    { concept: "Product Name", file: "sku_master.csv", col: "Product_Name", type: "string", miss: "0%", status: "Verified" },
    { concept: "Category", file: "sku_master.csv", col: "Category", type: "string", miss: "0%", status: "Verified" },
    { concept: "Subcategory", file: "sku_master.csv", col: "Subcategory", type: "string", miss: "0%", status: "Verified" },
    { concept: "Units Sold (Demand)", file: "sales_daily.csv", col: "Units_Sold", type: "integer", miss: "0%", status: "Verified" },
    { concept: "Gross Revenue", file: "sales_daily.csv", col: "Revenue", type: "float", miss: "0%", status: "Verified" },
    { concept: "Selling Price", file: "sales_daily.csv", col: "Price", type: "float", miss: "0%", status: "Verified" },
    { concept: "Cost Price", file: "sku_master.csv", col: "Cost_Price", type: "float", miss: "0%", status: "Verified" },
    { concept: "Current Stock", file: "inventory_snapshots.csv", col: "Current_Stock", type: "integer", miss: "0%", status: "Verified" },
    { concept: "On Order", file: "inventory_snapshots.csv", col: "On_Order", type: "integer", miss: "0%", status: "Verified" },
    { concept: "Lead Time (Days)", file: "inventory_snapshots.csv", col: "Lead_Time_Days", type: "integer", miss: "0%", status: "Verified" },
    { concept: "Safety Stock", file: "inventory_snapshots.csv", col: "Safety_Stock", type: "integer", miss: "0%", status: "Verified" },
    { concept: "Reorder Point", file: "inventory_snapshots.csv", col: "Reorder_Point", type: "integer", miss: "0%", status: "Verified" },
    { concept: "Location / Warehouse", file: "-", col: "-", type: "N/A", miss: "100%", status: "Data not available in source dataset" },
    { concept: "Supplier / Vendor", file: "-", col: "-", type: "N/A", miss: "100%", status: "Data not available in source dataset" },
  ];

  mapTbody.innerHTML = fieldDefs.map((fd) => `
    <tr>
      <td><strong>${fd.concept}</strong></td>
      <td><code>${fd.file}</code></td>
      <td><code>${fd.col}</code></td>
      <td><code>${fd.type}</code></td>
      <td>${fd.miss}</td>
      <td><span class="badge-status ${fd.status === 'Verified' ? 'status-healthy' : 'status-low'}"><span class="badge-status-dot"></span>${fd.status}</span></td>
    </tr>
  `).join("");
}

async function loadModelsTab() {
  try {
    const res = await fetch("/api/models");
    const data = await res.json();
    Foresight.modelsData = data;
    renderModelsTab(data);
  } catch (err) {
    console.error("Failed to load models:", err);
  }
}

function renderModelsTab(data) {
  if (!data || !data.leaderboard) return;
  document.getElementById("mp-top-model-tag").textContent = `Winner: ${data.overall_best_model}`;

  const tbody = document.getElementById("mp-leaderboard-tbody");
  tbody.innerHTML = data.leaderboard.map((m, idx) => `
    <tr>
      <td><span class="text-muted">#${idx + 1}</span></td>
      <td><strong>${escapeHtml(m.model_name)}</strong></td>
      <td class="text-right"><span class="badge-status status-healthy"><span class="badge-status-dot"></span>${m.avg_wape}%</span></td>
      <td class="text-right font-mono">${m.avg_mae}</td>
      <td class="text-right font-mono">${m.avg_rmse}</td>
      <td class="text-right">${m.evaluated_skus}</td>
      <td class="text-muted text-sm">${getModelDesc(m.model_name)}</td>
    </tr>
  `).join("");
}

function getModelDesc(name) {
  if (name.includes("SMA-7")) return "7-day sliding window rolling average capturing weekly velocity.";
  if (name.includes("Seasonal Naive")) return "7-day seasonal lag repeating identical day-of-week pattern.";
  if (name.includes("SES")) return "Exponentially weighted historical sequence with optimal alpha decay.";
  if (name.includes("Holt")) return "Double exponential smoothing with level and linear trend trajectory.";
  if (name.includes("SMA-14")) return "14-day rolling average for smoothed medium-term run rate.";
  if (name.includes("SMA-30")) return "30-day baseline average smoothing high volatility noise.";
  return "Persistence baseline projecting most recent daily observation.";
}

// -----------------------------------------------------------------
// 10. SKU Deep-Dive Modal Drawer
// -----------------------------------------------------------------
function openSkuModal(skuId) {
  const p = Foresight.productsData.find((x) => x.sku === skuId);
  if (!p) return;

  document.getElementById("modal-sku-title").textContent = `${p.sku} — ${p.product_name}`;
  document.getElementById("modal-sku-sub").textContent = `Category: ${p.category} • Subcategory: ${p.subcategory} • Launch: ${p.launch_date}`;

  const body = document.getElementById("modal-sku-body");
  body.innerHTML = `
    <div class="kpi-grid mb-4">
      <div class="kpi-card">
        <div class="kpi-label">SELLING PRICE</div>
        <div class="kpi-metric">$${Number(p.selling_price).toFixed(2)}</div>
        <div class="kpi-context">Cost: $${Number(p.cost_price).toFixed(2)} (Margin: $${Number(p.gross_margin).toFixed(2)})</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">TOTAL REVENUE</div>
        <div class="kpi-metric">$${(p.total_revenue / 1e6).toFixed(1)}M</div>
        <div class="kpi-context">${Number(p.total_units_sold).toLocaleString()} Units Sold</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">CURRENT STOCK</div>
        <div class="kpi-metric">${p.current_stock}</div>
        <div class="kpi-context">On Order: ${p.on_order} | Days Left: ${p.days_of_inventory}d</div>
      </div>
      <div class="kpi-card ${p.stockout_risk === 'High' ? 'kpi-card-danger' : ''}">
        <div class="kpi-label">STOCKOUT RISK</div>
        <div class="kpi-metric ${p.stockout_risk === 'High' ? 'text-danger' : ''}">${p.stockout_risk}</div>
        <div class="kpi-context">Projected Run-out: ${p.estimated_stockout_date}</div>
      </div>
    </div>

    <div class="card p-0 mb-4">
      <table class="saas-table">
        <tbody>
          <tr><td style="width: 220px;"><strong>Portfolio Segment (ABC-XYZ)</strong></td><td><span class="pill-badge">${p.abc_xyz_class}</span> (Demand CV: ${p.cv})</td></tr>
          <tr><td><strong>Daily Sales Run-Rate</strong></td><td>${p.avg_daily_demand} units/day (${p.avg_weekly_demand} weekly)</td></tr>
          <tr><td><strong>Supplier Lead Time</strong></td><td>${p.lead_time_days} days</td></tr>
          <tr><td><strong>Safety Stock Buffer</strong></td><td>${p.safety_stock} units</td></tr>
          <tr><td><strong>Reorder Point (ROP)</strong></td><td>${p.reorder_point} units</td></tr>
          <tr><td><strong>Reorder Trigger</strong></td><td>${p.reorder_needed ? '<strong class="text-danger">REORDER REQUIRED (' + p.recommended_order_quantity + ' units)</strong>' : '<span class="text-success">Adequate stock balance</span>'}</td></tr>
          <tr><td><strong>Suggested Order Date</strong></td><td>${p.suggested_reorder_date}</td></tr>
          <tr><td><strong>Store / Warehouse</strong></td><td><em class="text-muted">Data not available in source dataset</em></td></tr>
          <tr><td><strong>Supplier Entity</strong></td><td><em class="text-muted">Data not available in source dataset</em></td></tr>
        </tbody>
      </table>
    </div>

    <div style="display: flex; justify-content: space-between; align-items: center;">
      <button class="btn btn-secondary" onclick="inspectForecastFromModal('${p.sku}')">Inspect Demand Forecast &rarr;</button>
      <button class="btn btn-secondary" onclick="closeModal()">Close</button>
    </div>
  `;

  document.getElementById("sku-modal").classList.add("active");
}

function inspectForecastFromModal(skuId) {
  closeModal();
  Foresight.forecastState.sku = skuId;
  const select = document.getElementById("fc-sku-select");
  if (select) select.value = skuId;
  switchTab("forecast");
}

function closeModal() {
  document.getElementById("sku-modal").classList.remove("active");
}

function closeModalOnOutside(event) {
  if (event.target.id === "sku-modal") closeModal();
}

function populateCategoryDropdowns() {
  const cats = Array.from(new Set(Foresight.productsData.map((p) => p.category))).sort();
  ["fc-category-filter", "prod-cat-filter"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '<option value="ALL">All Categories</option>' +
      cats.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  });
}

function exportData(type) {
  window.location.href = `/api/export/${type}`;
}

// -----------------------------------------------------------------
// Helpers & CSS Badge Classes
// -----------------------------------------------------------------
function getStatusClass(status) {
  if (status === "Healthy") return "status-healthy";
  if (status === "Low Stock") return "status-low";
  if (status === "Critical") return "status-critical";
  if (status === "Overstock") return "status-overstock";
  if (status === "Out of Stock") return "status-out";
  return "status-overstock";
}

function getRiskClass(risk) {
  if (risk === "High") return "status-critical";
  if (risk === "Medium") return "status-low";
  return "status-healthy";
}

function getUrgencyClass(urgency) {
  if (urgency === "High") return "status-critical";
  if (urgency === "Medium") return "status-low";
  return "status-healthy";
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// -----------------------------------------------------------------
// 10. Security & Authentication Client Controller
// -----------------------------------------------------------------

async function checkAuthAndInit() {
  try {
    const res = await fetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      if (data && data.user) {
        Foresight.currentUser = data.user;
        Foresight.csrfToken = data.csrf_token;
        updateUserInterfaceForRole(data.user);
      }
    }
  } catch (err) {
    console.warn("Auth initialization bypassed:", err);
  }
  // Immediately load core analytics dashboard
  await loadInitialData();
}

function updateUserInterfaceForRole(user) {
  const username = user.username || "Operations Lead";
  const initials = username.substring(0, 2).toUpperCase();
  const role = (user.role || "ADMIN").toUpperCase();

  const initialsEl = document.getElementById("hdr-user-initials");
  const nameEl = document.getElementById("hdr-user-name");
  const roleEl = document.getElementById("hdr-user-role");
  const dropNameEl = document.getElementById("drop-user-name");
  const dropEmailEl = document.getElementById("drop-user-email");

  if (initialsEl) initialsEl.textContent = initials;
  if (nameEl) nameEl.textContent = username;
  if (roleEl) {
    roleEl.textContent = role;
    roleEl.className = `user-role-tag role-badge-${role.toLowerCase()}`;
  }
  if (dropNameEl) dropNameEl.textContent = username;
  if (dropEmailEl) dropEmailEl.textContent = user.email || `${username.toLowerCase()}@foresight.ai`;

  // Ensure all analytical and admin sections are visible
  const adminGroup = document.getElementById("nav-group-admin");
  const adminUsersBtn = document.getElementById("nav-item-users");
  const adminSecBtn = document.getElementById("nav-item-security");
  if (adminGroup) adminGroup.style.display = "block";
  if (adminUsersBtn) adminUsersBtn.style.display = "flex";
  if (adminSecBtn) adminSecBtn.style.display = "flex";
}

// Global click handler to close dropdown when clicking outside
document.addEventListener("click", (e) => {
  const widget = document.getElementById("user-profile-widget");
  const menu = document.getElementById("user-dropdown-menu");
  if (widget && menu && !widget.contains(e.target)) {
    menu.classList.remove("show");
    const btn = document.getElementById("user-menu-btn");
    if (btn) btn.setAttribute("aria-expanded", "false");
  }
});

function toggleUserDropdown(event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById("user-dropdown-menu");
  const btn = document.getElementById("user-menu-btn");
  if (!menu) return;
  const isExpanded = menu.classList.toggle("show");
  if (btn) btn.setAttribute("aria-expanded", isExpanded ? "true" : "false");
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": Foresight.csrfToken || ""
      }
    });
  } catch (err) {
    console.error("Logout error:", err);
  } finally {
    window.location.href = "/";
  }
}

// Password Management
function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "Hide";
  } else {
    input.type = "password";
    btn.textContent = "Show";
  }
}

function openChangePasswordModal() {
  const menu = document.getElementById("user-dropdown-menu");
  if (menu) menu.classList.remove("show");
  const modal = document.getElementById("change-password-modal");
  const alertBox = document.getElementById("cp-alert");
  if (alertBox) alertBox.style.display = "none";
  document.getElementById("cp-current").value = "";
  document.getElementById("cp-new").value = "";
  document.getElementById("cp-confirm").value = "";
  if (modal) modal.style.display = "flex";
}

function closeChangePasswordModal() {
  const modal = document.getElementById("change-password-modal");
  if (modal) modal.style.display = "none";
}

async function handleChangePasswordSubmit(event) {
  event.preventDefault();
  const current = document.getElementById("cp-current").value;
  const newPass = document.getElementById("cp-new").value;
  const confirmPass = document.getElementById("cp-confirm").value;
  const alertBox = document.getElementById("cp-alert");
  const alertMsg = document.getElementById("cp-alert-msg");
  const btn = document.getElementById("btn-save-password");

  if (newPass !== confirmPass) {
    alertMsg.textContent = "New password and confirmation do not match.";
    alertBox.className = "auth-alert alert-danger";
    alertBox.style.display = "flex";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Updating...";

  try {
    const res = await fetch("/api/auth/change-password", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": Foresight.csrfToken || ""
      },
      body: JSON.stringify({
        current_password: current,
        new_password: newPass
      })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alertMsg.textContent = "Password updated successfully! Closing dialog...";
      alertBox.className = "auth-alert alert-success";
      alertBox.style.display = "flex";
      setTimeout(() => {
        closeChangePasswordModal();
        btn.disabled = false;
        btn.textContent = "Update Password";
      }, 1200);
    } else {
      alertMsg.textContent = data.error || "Failed to change password.";
      alertBox.className = "auth-alert alert-danger";
      alertBox.style.display = "flex";
      btn.disabled = false;
      btn.textContent = "Update Password";
    }
  } catch (err) {
    alertMsg.textContent = "Network error updating password.";
    alertBox.className = "auth-alert alert-danger";
    alertBox.style.display = "flex";
    btn.disabled = false;
    btn.textContent = "Update Password";
  }
}

// -----------------------------------------------------------------
// 11. Admin User Management Operations
// -----------------------------------------------------------------
async function loadUsersTab() {
  try {
    const res = await fetch("/api/admin/users");
    if (!res.ok) {
      if (res.status === 403) {
        alert("Administrator privileges required to view User Management.");
        switchTab("overview");
      }
      return;
    }
    const data = await res.json();
    Foresight.usersList = data.users || [];

    // Update KPI Cards
    const total = Foresight.usersList.length;
    const active = Foresight.usersList.filter((u) => u.is_active === 1).length;
    const locked = Foresight.usersList.filter((u) => {
      if (!u.locked_until) return false;
      return new Date(u.locked_until) > new Date();
    }).length;

    const totalEl = document.getElementById("um-total-users");
    const activeEl = document.getElementById("um-active-users");
    const lockedEl = document.getElementById("um-locked-users");

    if (totalEl) totalEl.textContent = total;
    if (activeEl) activeEl.textContent = active;
    if (lockedEl) lockedEl.textContent = locked;

    filterUsersTable();
  } catch (err) {
    console.error("Error loading users:", err);
  }
}

function filterUsersTable() {
  const roleFilter = document.getElementById("um-role-filter") ? document.getElementById("um-role-filter").value : "ALL";
  let list = Foresight.usersList;
  if (roleFilter !== "ALL") {
    list = list.filter((u) => u.role === roleFilter);
  }
  renderUsersTable(list);
}

function renderUsersTable(users) {
  const tbody = document.getElementById("um-users-tbody");
  if (!tbody) return;

  if (!users || users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted p-4">No team accounts match this filter.</td></tr>';
    return;
  }

  const now = new Date();

  tbody.innerHTML = users.map((u) => {
    const isLocked = u.locked_until && new Date(u.locked_until) > now;
    let statusPill = "";
    if (isLocked) {
      statusPill = '<span class="status-pill status-pill-locked">● Locked</span>';
    } else if (u.is_active === 1) {
      statusPill = '<span class="status-pill status-pill-active">● Active</span>';
    } else {
      statusPill = '<span class="status-pill status-pill-inactive">● Deactivated</span>';
    }

    const roleBadge = `<span class="user-role-tag role-badge-${u.role.toLowerCase()}">${escapeHtml(u.role)}</span>`;
    const isSelf = Foresight.currentUser && Foresight.currentUser.id === u.id;

    // Action buttons
    let actionButtons = `<div style="display:flex; gap:6px; justify-content:flex-end; align-items:center;">`;

    if (isLocked) {
      actionButtons += `<button class="btn btn-secondary btn-sm" onclick="unlockUser(${u.id})" title="Unlock Account">Unlock</button>`;
    }

    if (!isSelf) {
      if (u.is_active === 1) {
        actionButtons += `<button class="btn btn-secondary btn-sm text-danger" onclick="toggleUserActive(${u.id}, true)" title="Deactivate user">Deactivate</button>`;
      } else {
        actionButtons += `<button class="btn btn-secondary btn-sm text-success" onclick="toggleUserActive(${u.id}, false)" title="Activate user">Activate</button>`;
      }

      actionButtons += `
        <select class="form-select" style="padding: 2px 6px; font-size: 11px;" onchange="changeUserRole(${u.id}, this.value)" title="Change role">
          <option value="ANALYST" ${u.role === "ANALYST" ? "selected" : ""}>Analyst</option>
          <option value="VIEWER" ${u.role === "VIEWER" ? "selected" : ""}>Viewer</option>
          <option value="ADMIN" ${u.role === "ADMIN" ? "selected" : ""}>Admin</option>
        </select>
      `;

      actionButtons += `<button class="btn btn-secondary btn-sm" onclick="openAdminResetModal(${u.id}, '${escapeHtml(u.username)}')" title="Reset user password">Reset PW</button>`;
    } else {
      actionButtons += `<span class="text-muted text-xs" style="font-style:italic;">(Current Admin)</span>`;
    }

    actionButtons += `</div>`;

    return `
      <tr>
        <td class="font-mono">${u.id}</td>
        <td>
          <div style="font-weight:600; color:var(--text-main);">${escapeHtml(u.username)}</div>
          <div class="text-muted text-xs">${escapeHtml(u.email)}</div>
        </td>
        <td>${roleBadge}</td>
        <td>${statusPill}</td>
        <td class="text-center font-mono ${u.failed_login_attempts > 0 ? "text-warning" : ""}">${u.failed_login_attempts}</td>
        <td class="text-muted text-xs font-mono">${(u.created_at || "").substring(0, 10)}</td>
        <td class="text-muted text-xs font-mono">${u.last_login_at ? u.last_login_at.substring(0, 16).replace("T", " ") : "Never"}</td>
        <td class="text-right">${actionButtons}</td>
      </tr>
    `;
  }).join("");
}

function openCreateUserModal() {
  const modal = document.getElementById("create-user-modal");
  const alertBox = document.getElementById("cu-alert");
  if (alertBox) alertBox.style.display = "none";
  document.getElementById("cu-username").value = "";
  document.getElementById("cu-email").value = "";
  document.getElementById("cu-password").value = "";
  document.getElementById("cu-role").value = "ANALYST";
  if (modal) modal.style.display = "flex";
}

function closeCreateUserModal() {
  const modal = document.getElementById("create-user-modal");
  if (modal) modal.style.display = "none";
}

async function handleCreateUserSubmit(event) {
  event.preventDefault();
  const username = document.getElementById("cu-username").value.trim();
  const email = document.getElementById("cu-email").value.trim();
  const role = document.getElementById("cu-role").value;
  const password = document.getElementById("cu-password").value;
  const alertBox = document.getElementById("cu-alert");
  const alertMsg = document.getElementById("cu-alert-msg");
  const btn = document.getElementById("btn-submit-create-user");

  btn.disabled = true;
  btn.textContent = "Creating Account...";

  try {
    const res = await fetch("/api/admin/users/create", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": Foresight.csrfToken || ""
      },
      body: JSON.stringify({ username, email, role, password })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alertMsg.textContent = `User ${username} provisioned successfully!`;
      alertBox.className = "auth-alert alert-success";
      alertBox.style.display = "flex";
      setTimeout(() => {
        closeCreateUserModal();
        btn.disabled = false;
        btn.textContent = "Create Account";
        loadUsersTab();
      }, 1000);
    } else {
      alertMsg.textContent = data.error || "Failed to create user account.";
      alertBox.className = "auth-alert alert-danger";
      alertBox.style.display = "flex";
      btn.disabled = false;
      btn.textContent = "Create Account";
    }
  } catch (err) {
    alertMsg.textContent = "Network error creating user.";
    alertBox.className = "auth-alert alert-danger";
    alertBox.style.display = "flex";
    btn.disabled = false;
    btn.textContent = "Create Account";
  }
}

async function toggleUserActive(userId, currentActive) {
  const newActive = !currentActive;
  const actionName = newActive ? "activate" : "deactivate";
  if (!confirm(`Are you sure you want to ${actionName} this user account?`)) return;

  try {
    const res = await fetch("/api/admin/users/status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": Foresight.csrfToken || ""
      },
      body: JSON.stringify({ user_id: userId, is_active: newActive })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadUsersTab();
    } else {
      alert(data.error || "Failed to update user status.");
    }
  } catch (err) {
    alert("Network error updating status.");
  }
}

async function unlockUser(userId) {
  try {
    const res = await fetch("/api/admin/users/status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": Foresight.csrfToken || ""
      },
      body: JSON.stringify({ user_id: userId, is_active: true, unlock: true })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadUsersTab();
    } else {
      alert(data.error || "Failed to unlock user.");
    }
  } catch (err) {
    alert("Network error unlocking user.");
  }
}

async function changeUserRole(userId, newRole) {
  try {
    const res = await fetch("/api/admin/users/role", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": Foresight.csrfToken || ""
      },
      body: JSON.stringify({ user_id: userId, role: newRole })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      await loadUsersTab();
    } else {
      alert(data.error || "Failed to change user role.");
      await loadUsersTab();
    }
  } catch (err) {
    alert("Network error updating user role.");
  }
}

function openAdminResetModal(userId, username) {
  const modal = document.getElementById("admin-reset-pw-modal");
  const sub = document.getElementById("admin-reset-sub");
  const alertBox = document.getElementById("ar-alert");
  if (alertBox) alertBox.style.display = "none";
  document.getElementById("ar-user-id").value = userId;
  document.getElementById("ar-new-password").value = "";
  if (sub) sub.textContent = `Overriding master credentials for: ${username}`;
  if (modal) modal.style.display = "flex";
}

function closeAdminResetModal() {
  const modal = document.getElementById("admin-reset-pw-modal");
  if (modal) modal.style.display = "none";
}

async function handleAdminResetSubmit(event) {
  event.preventDefault();
  const userId = document.getElementById("ar-user-id").value;
  const newPass = document.getElementById("ar-new-password").value;
  const alertBox = document.getElementById("ar-alert");
  const alertMsg = document.getElementById("ar-alert-msg");
  const btn = document.getElementById("btn-admin-reset-submit");

  btn.disabled = true;
  btn.textContent = "Applying Reset...";

  try {
    const res = await fetch("/api/admin/users/reset-password", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": Foresight.csrfToken || ""
      },
      body: JSON.stringify({ user_id: userId, new_password: newPass })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alertMsg.textContent = "Password reset successfully! User sessions revoked.";
      alertBox.className = "auth-alert alert-success";
      alertBox.style.display = "flex";
      setTimeout(() => {
        closeAdminResetModal();
        btn.disabled = false;
        btn.textContent = "Set New Password";
        loadUsersTab();
      }, 1100);
    } else {
      alertMsg.textContent = data.error || "Failed to reset password.";
      alertBox.className = "auth-alert alert-danger";
      alertBox.style.display = "flex";
      btn.disabled = false;
      btn.textContent = "Set New Password";
    }
  } catch (err) {
    alertMsg.textContent = "Network error resetting password.";
    alertBox.className = "auth-alert alert-danger";
    alertBox.style.display = "flex";
    btn.disabled = false;
    btn.textContent = "Set New Password";
  }
}

// -----------------------------------------------------------------
// 12. Security Posture & Audit Trail Ledger
// -----------------------------------------------------------------
async function fetchSecurityStatus() {
  try {
    const res = await fetch("/api/admin/security-status");
    if (!res.ok) {
      if (res.status === 403) {
        alert("Administrator privileges required to view Security Audit Trail.");
        switchTab("overview");
      }
      return;
    }
    const data = await res.json();
    const metrics = data.metrics || {};
    const logs = data.audit_logs || [];

    const sessEl = document.getElementById("sec-active-sessions");
    const failEl = document.getElementById("sec-failed-24h");
    const statusEl = document.getElementById("sec-status-badge");

    if (sessEl) sessEl.textContent = metrics.active_sessions || 0;
    if (failEl) failEl.textContent = metrics.recent_login_failures_24h || 0;
    if (statusEl) statusEl.textContent = metrics.system_status || "SECURE";

    renderAuditLogs(logs);
  } catch (err) {
    console.error("Error fetching security status:", err);
  }
}

function renderAuditLogs(logs) {
  const tbody = document.getElementById("sec-audit-tbody");
  if (!tbody) return;

  if (!logs || logs.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted p-4">No audit events recorded yet.</td></tr>';
    return;
  }

  const getActionTagClass = (evt) => {
    if (evt.includes("SUCCESS")) return "tag-login-success";
    if (evt.includes("FAILURE") || evt.includes("REJECT") || evt.includes("DENIED") || evt.includes("LOCKOUT")) return "tag-login-fail";
    if (evt.includes("CREATE")) return "tag-user-create";
    if (evt.includes("STATUS") || evt.includes("ROLE")) return "tag-user-update";
    if (evt.includes("PASSWORD")) return "tag-password-change";
    return "tag-logout";
  };

  tbody.innerHTML = logs.map((l) => {
    const timeFormatted = (l.timestamp || "").replace("T", " ").substring(0, 19);
    const userDisplay = l.username ? `${escapeHtml(l.username)} (${escapeHtml(l.role || "USER")})` : (l.user_id ? `User #${l.user_id}` : "System / Anonymous");
    const tagClass = getActionTagClass(l.event);

    return `
      <tr>
        <td class="text-muted font-mono" style="white-space: nowrap;">${timeFormatted}</td>
        <td><strong>${userDisplay}</strong></td>
        <td><span class="audit-action-tag ${tagClass}">${escapeHtml(l.event)}</span></td>
        <td class="font-mono text-muted text-xs">${escapeHtml(l.ip_address || "127.0.0.1")}</td>
        <td class="text-secondary text-xs">${escapeHtml(l.details || "-")}</td>
      </tr>
    `;
  }).join("");
}

