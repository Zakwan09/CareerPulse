requireAuth();
let trendChart = null;

async function loadSkillOptions() {
  const sel = document.getElementById("skill-select");
  try {
    const data = await apiFetch("/api/skills?limit=30");
    data.skills.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.skill; opt.textContent = s.skill;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => {
      if (sel.value) loadForecast(sel.value);
    });
    if (data.skills.length) {
      sel.value = data.skills[0].skill;
      loadForecast(sel.value);
    }
  } catch (err) {
    document.getElementById("forecast-note").textContent = err.message;
  }
}

async function loadForecast(skillName) {
  const note = document.getElementById("forecast-note");
  note.textContent = "Loading...";
  try {
    const data = await apiFetch(`/api/forecast/${encodeURIComponent(skillName)}`);

    const historyLabels = data.history.map((h) => h.month);
    const historyValues = data.history.map((h) => h.count);

    let forecastLabels = [];
    let forecastValues = [];
    if (data.status === "ok") {
      forecastLabels = data.forecast.map((f) => f.month);
      forecastValues = data.forecast.map((f) => f.predicted_count);
      note.innerHTML = `Model: <strong>${data.model}</strong> &nbsp;|&nbsp; Linear-trend MAE: ${data.evaluation.linear_trend_mae}, RMSE: ${data.evaluation.linear_trend_rmse}`;
    } else {
      note.innerHTML = `<span style="color:var(--cp-warn);">${data.message}</span>`;
    }

    const allLabels = [...historyLabels, ...forecastLabels];
    const historyData = [...historyValues, ...Array(forecastLabels.length).fill(null)];
    const forecastData = [...Array(historyValues.length - 1).fill(null), historyValues[historyValues.length - 1] ?? null, ...forecastValues];

    if (trendChart) trendChart.destroy();
    trendChart = new Chart(document.getElementById("trend-chart"), {
      type: "line",
      data: {
        labels: allLabels,
        datasets: [
          { label: "Actual postings", data: historyData, borderColor: "#6c8dff", backgroundColor: "transparent", tension: 0.3 },
          { label: "Forecast", data: forecastData, borderColor: "#f2a93b", borderDash: [6, 4], backgroundColor: "transparent", tension: 0.3 },
        ],
      },
      options: {
        plugins: { legend: { labels: { color: "#9aa4c4" } } },
        scales: { x: { ticks: { color: "#9aa4c4" } }, y: { ticks: { color: "#9aa4c4" }, beginAtZero: true } },
      },
    });
  } catch (err) {
    note.textContent = err.message;
  }
}

loadSkillOptions();
