requireAuth();

function skillRow(s) {
  return `<div class="bar-row">
    <div class="label">${s.skill}</div>
    <div class="bar-track"><div class="bar-fill" style="width:${s.demand_pct}%"></div></div>
    <div class="bar-value">${s.demand_pct}%</div>
  </div>`;
}

async function loadTopSkills() {
  try {
    const data = await apiFetch("/api/skills?limit=20");
    document.getElementById("skills-list").innerHTML = data.skills.map(skillRow).join("");

    const sel = document.getElementById("skill-select");
    data.skills.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.skill; opt.textContent = s.skill;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => {
      if (sel.value) loadSkillDetail(sel.value);
    });
  } catch (err) {
    document.getElementById("skills-list").innerHTML = `<div class="empty-state">${err.message}</div>`;
  }
}

async function loadSkillDetail(skillName) {
  const el = document.getElementById("skill-detail");
  el.innerHTML = `<div class="loading">Loading...</div>`;
  try {
    const d = await apiFetch(`/api/skills/${encodeURIComponent(skillName)}`);
    el.innerHTML = `
      <div class="grid grid-2" style="margin-bottom:14px;">
        <div class="card kpi"><div class="value">${d.demand_pct}%</div><div class="label">Overall Demand</div></div>
        <div class="card kpi"><div class="value">${d.salary_avg_lpa ?? "—"}</div><div class="label">Avg Salary (LPA)</div></div>
      </div>
      <p><strong>Category:</strong> ${d.category}</p>
      <p><strong>Top Roles:</strong> ${d.top_roles.map((r) => `${r[0]} (${r[1]})`).join(", ") || "—"}</p>
      <p><strong>Top Locations:</strong> ${d.top_locations.map((l) => `${l[0]} (${l[1]})`).join(", ") || "—"}</p>
      <p><strong>Related Skills:</strong> ${d.related_skills.join(", ") || "—"}</p>
    `;
  } catch (err) {
    el.innerHTML = `<div class="empty-state">${err.message}</div>`;
  }
}

loadTopSkills();
