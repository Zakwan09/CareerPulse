requireAuth();

async function loadFilterOptions() {
  try {
    const [roles, locations] = await Promise.all([
      apiFetch("/api/roles"),
      apiFetch("/api/locations"),
    ]);
    const roleSel = document.getElementById("f-role");
    roles.roles.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r; opt.textContent = r;
      roleSel.appendChild(opt);
    });
    const locSel = document.getElementById("f-location");
    locations.locations.forEach((l) => {
      const opt = document.createElement("option");
      opt.value = l; opt.textContent = l;
      locSel.appendChild(opt);
    });
  } catch (err) {
    console.error(err);
  }
}

function buildQuery() {
  const params = new URLSearchParams();
  const role = document.getElementById("f-role").value;
  const location = document.getElementById("f-location").value;
  const industry = document.getElementById("f-industry").value.trim();
  const workMode = document.getElementById("f-work-mode").value;
  const employmentType = document.getElementById("f-employment-type").value;
  if (role) params.set("role", role);
  if (location) params.set("location", location);
  if (industry) params.set("industry", industry);
  if (workMode) params.set("work_mode", workMode);
  if (employmentType) params.set("employment_type", employmentType);
  return params.toString();
}

function distRow(label, count) {
  return `<tr><td>${label}</td><td>${count}</td></tr>`;
}

async function loadMarket() {
  const resultsEl = document.getElementById("market-results");
  resultsEl.innerHTML = `<div class="loading">Loading...</div>`;
  try {
    const qs = buildQuery();
    const data = await apiFetch("/api/market/overview" + (qs ? "?" + qs : ""));

    if (!data.matching_jobs) {
      resultsEl.innerHTML = `<div class="empty-state">No jobs match these filters.</div>`;
      return;
    }

    const topSkillsRows = (data.top_skills || [])
      .map((s) => distRow(s.skill, s.count))
      .join("");
    const locRows = (data.location_distribution || [])
      .map(([label, count]) => distRow(label, count))
      .join("");
    const companyRows = (data.company_distribution || [])
      .map(([label, count]) => distRow(label, count))
      .join("");

    resultsEl.innerHTML = `
      <div class="grid grid-4" style="margin-bottom:16px;">
        <div class="card kpi"><div class="value">${data.matching_jobs}</div><div class="label">Matching Jobs</div></div>
        <div class="card kpi"><div class="value">${data.salary_stats.avg}</div><div class="label">Avg Salary (LPA)</div></div>
        <div class="card kpi"><div class="value">${data.salary_stats.min}–${data.salary_stats.max}</div><div class="label">Salary Range (LPA)</div></div>
        <div class="card kpi"><div class="value">${data.experience_stats.avg}</div><div class="label">Avg Experience (yrs)</div></div>
      </div>
      <div class="grid grid-2">
        <div class="card"><h3>Top Skills</h3><table><tbody>${topSkillsRows}</tbody></table></div>
        <div class="card"><h3>Top Locations</h3><table><tbody>${locRows}</tbody></table></div>
      </div>
      <div class="card" style="margin-top:16px;"><h3>Top Companies</h3><table><tbody>${companyRows}</tbody></table></div>
    `;
  } catch (err) {
    resultsEl.innerHTML = `<div class="empty-state">Could not load market data: ${err.message}</div>`;
  }
}

document.getElementById("apply-filters").addEventListener("click", loadMarket);
loadFilterOptions();
loadMarket();
