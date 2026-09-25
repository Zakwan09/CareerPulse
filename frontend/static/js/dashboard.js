requireAuth();

function kpiCard(value, label) {
  return `<div class="card kpi"><div class="value">${value}</div><div class="label">${label}</div></div>`;
}

function barRow(label, value, max) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return `<div class="bar-row">
    <div class="label">${label}</div>
    <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
    <div class="bar-value">${value}</div>
  </div>`;
}

async function loadDashboard() {
  try {
    const data = await apiFetch("/api/dashboard/summary");

    document.getElementById("kpi-grid").innerHTML = [
      kpiCard(data.total_jobs ?? "—", "Total Jobs"),
      kpiCard(data.total_skills ?? "—", "Total Skills"),
      kpiCard(data.top_role ?? "—", "Top Role"),
      kpiCard(data.median_salary_lpa != null ? data.median_salary_lpa + " LPA" : "—", "Median Salary"),
    ].join("");

    // Jobs by role
    new Chart(document.getElementById("chart-role"), {
      type: "bar",
      data: {
        labels: data.jobs_by_role.map((r) => r.label),
        datasets: [{ data: data.jobs_by_role.map((r) => r.count), backgroundColor: "#6c8dff" }],
      },
      options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#9aa4c4" } }, y: { ticks: { color: "#9aa4c4" } } } },
    });

    // Jobs by location
    new Chart(document.getElementById("chart-location"), {
      type: "doughnut",
      data: {
        labels: data.jobs_by_location.map((r) => r.label),
        datasets: [{ data: data.jobs_by_location.map((r) => r.count),
          backgroundColor: ["#6c8dff","#35d0ba","#f2a93b","#ef5a6f","#8b7cf6","#4c67d6","#2fb89f","#d98f2b","#c94d61","#6f5fd4"] }],
      },
      options: { plugins: { legend: { position: "right", labels: { color: "#9aa4c4", boxWidth: 10 } } } },
    });

    // Salary distribution buckets
    const buckets = data.salary_distribution.buckets || [];
    new Chart(document.getElementById("chart-salary"), {
      type: "bar",
      data: {
        labels: buckets.map((b) => b[0]),
        datasets: [{ data: buckets.map((b) => b[1]), backgroundColor: "#35d0ba" }],
      },
      options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#9aa4c4" } }, y: { ticks: { color: "#9aa4c4" } } } },
    });

    // Top skills bars
    const maxFreq = Math.max(...data.top_skills.map((s) => s.frequency), 1);
    document.getElementById("top-skills").innerHTML = data.top_skills
      .map((s) => barRow(s.skill, s.demand_pct + "%", 100))
      .join("");
  } catch (err) {
    document.getElementById("kpi-grid").innerHTML = `<div class="empty-state">Could not load dashboard: ${err.message}</div>`;
  }
}

loadDashboard();
