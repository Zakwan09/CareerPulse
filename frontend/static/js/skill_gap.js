requireAuth();

let currentSkills = [];


/* =========================================================
   SKILL TAGS
========================================================= */

function renderTags() {
  const wrap = document.getElementById("tag-wrap");
  const input = document.getElementById("skill-tag-input");

  if (!wrap || !input) return;

  wrap.querySelectorAll(".tag").forEach((tag) => tag.remove());

  currentSkills.forEach((skill, idx) => {
    const tag = document.createElement("span");

    tag.className = "tag";

    tag.innerHTML = `
      ${escapeHtml(skill)}
      <button
        type="button"
        data-idx="${idx}"
        aria-label="Remove ${escapeHtml(skill)}"
      >
        &times;
      </button>
    `;

    wrap.insertBefore(tag, input);
  });

  wrap.querySelectorAll(".tag button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const index = parseInt(btn.dataset.idx, 10);

      if (!Number.isNaN(index)) {
        currentSkills.splice(index, 1);
        renderTags();
      }
    });
  });
}


/* =========================================================
   MANUAL SKILL INPUT
========================================================= */

const skillInput =
  document.getElementById("skill-tag-input");

if (skillInput) {
  skillInput.addEventListener("keydown", (e) => {

    if (e.key !== "Enter" && e.key !== ",") {
      return;
    }

    e.preventDefault();

    const value = e.target.value
      .trim()
      .replace(/,$/, "");

    if (
      value &&
      !currentSkills.some(
        (skill) =>
          skill.toLowerCase() === value.toLowerCase()
      )
    ) {
      currentSkills.push(value);
      renderTags();
    }

    e.target.value = "";
  });
}


/* =========================================================
   RESUME FILE
========================================================= */

const resumeInput =
  document.getElementById("resume-file");

if (resumeInput) {

  resumeInput.addEventListener("change", (e) => {

    const file = e.target.files[0];

    const nameElement =
      document.getElementById("resume-name");

    if (!nameElement) return;

    if (!file) {
      nameElement.textContent = "";
      return;
    }

    const allowedExtensions = [
      ".pdf",
      ".docx"
    ];

    const fileName =
      file.name.toLowerCase();

    const valid =
      allowedExtensions.some(
        (extension) =>
          fileName.endsWith(extension)
      );

    if (!valid) {

      e.target.value = "";

      nameElement.textContent =
        "Please select a PDF or DOCX file.";

      return;
    }

    nameElement.textContent =
      `Selected: ${file.name}`;
  });
}


/* =========================================================
   LOAD ROLES
========================================================= */

async function loadRoles() {

  try {

    const data =
      await apiFetch("/api/roles");

    const select =
      document.getElementById("target-role");

    if (!select) return;

    select.innerHTML =
      '<option value="">Select a target role</option>';

    const roles =
      Array.isArray(data.roles)
        ? data.roles
        : [];

    roles.forEach((role) => {

      const option =
        document.createElement("option");

      option.value = role;
      option.textContent = role;

      select.appendChild(option);
    });

  } catch (error) {

    console.error(
      "Failed to load roles:",
      error
    );
  }
}


/* =========================================================
   PRIORITY BADGE
========================================================= */

function priorityBadge(level) {

  const safeLevel =
    String(level || "Low");

  return `
    <span class="badge ${safeLevel.toLowerCase()}">
      ${escapeHtml(safeLevel)}
    </span>
  `;
}


/* =========================================================
   ESCAPE HTML
========================================================= */

function escapeHtml(value) {

  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}


/* =========================================================
   API ERROR PARSER
========================================================= */

function getApiErrorMessage(data) {

  if (!data) {
    return "Skill-gap analysis failed.";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {

    return data.detail
      .map((error) => {

        if (typeof error === "string") {
          return error;
        }

        if (
          error &&
          typeof error === "object"
        ) {

          const location =
            Array.isArray(error.loc)
              ? error.loc.join(" → ")
              : "";

          const message =
            error.msg ||
            error.message ||
            JSON.stringify(error);

          return location
            ? `${location}: ${message}`
            : message;
        }

        return String(error);
      })
      .join(", ");
  }

  if (typeof data.error === "string") {
    return data.error;
  }

  if (typeof data.message === "string") {
    return data.message;
  }

  return "Skill-gap analysis failed.";
}


/* =========================================================
   RESPONSE JSON HELPER
========================================================= */

async function parseResponse(response) {

  const contentType =
    response.headers.get("content-type") || "";

  if (
    contentType.includes(
      "application/json"
    )
  ) {
    return await response.json();
  }

  const text =
    await response.text();

  return {
    detail:
      text ||
      `Request failed with status ${response.status}.`
  };
}


/* =========================================================
   ANALYZE SKILL GAP
========================================================= */

async function analyze() {

  const targetRoleElement =
    document.getElementById("target-role");

  const resumeInput =
    document.getElementById("resume-file");

  const resultsEl =
    document.getElementById("gap-results");

  if (
    !targetRoleElement ||
    !resultsEl
  ) {

    console.error(
      "Skill-gap page elements are missing."
    );

    return;
  }

  const targetRole =
    targetRoleElement.value.trim();

  if (!targetRole) {

    resultsEl.innerHTML = `
      <div class="empty-state">
        Please select a target role.
      </div>
    `;

    return;
  }


  /* -------------------------------------------------------
     GET RESUME
  ------------------------------------------------------- */

  const resumeFile =
    resumeInput?.files?.[0] || null;


  /* -------------------------------------------------------
     CHECK INPUT
  ------------------------------------------------------- */

  if (
    !resumeFile &&
    currentSkills.length === 0
  ) {

    resultsEl.innerHTML = `
      <div class="empty-state">
        Please upload a resume or enter at least one skill.
      </div>
    `;

    return;
  }


  /* -------------------------------------------------------
     VALIDATE RESUME
  ------------------------------------------------------- */

  if (resumeFile) {

    const fileName =
      resumeFile.name.toLowerCase();

    const allowedExtensions = [
      ".pdf",
      ".docx"
    ];

    const valid =
      allowedExtensions.some(
        (extension) =>
          fileName.endsWith(extension)
      );

    if (!valid) {

      resultsEl.innerHTML = `
        <div class="empty-state">
          Please upload a PDF or DOCX resume.
        </div>
      `;

      return;
    }
  }


  /* -------------------------------------------------------
     LOADING
  ------------------------------------------------------- */

  resultsEl.innerHTML = `
    <div class="loading">
      Analyzing your resume...
    </div>
  `;


  try {

    /*
     * Resume upload requires FormData.
     *
     * IMPORTANT:
     * Do NOT manually set Content-Type.
     * The browser automatically creates:
     *
     * multipart/form-data; boundary=...
     */

    const formData =
      new FormData();


    /* Target role */

    formData.append(
      "target_role",
      targetRole
    );


    /* Manual skills */

    formData.append(
      "current_skills",
      JSON.stringify(currentSkills)
    );


    /* Resume */

    if (resumeFile) {

      formData.append(
        "resume",
        resumeFile,
        resumeFile.name
      );
    }


    /* -----------------------------------------------------
       AUTH TOKEN
    ----------------------------------------------------- */

    const token =
      localStorage.getItem("auth_token");

    if (!token) {

      throw new Error(
        "Your session has expired. Please log in again."
      );
    }


    /* -----------------------------------------------------
       SEND REQUEST
    ----------------------------------------------------- */

    const response =
      await fetch(
        "/api/skill-gap/analyze",
        {
          method: "POST",

          headers: {
            Authorization:
              `Bearer ${token}`
          },

          body: formData
        }
      );


    /* -----------------------------------------------------
       READ RESPONSE
    ----------------------------------------------------- */

    const data =
      await parseResponse(response);


    /* -----------------------------------------------------
       HANDLE API ERROR
    ----------------------------------------------------- */

    if (!response.ok) {

      throw new Error(
        getApiErrorMessage(data)
      );
    }


    /* -----------------------------------------------------
       BACKEND NOTE
    ----------------------------------------------------- */

    if (data.note) {

      resultsEl.innerHTML = `
        <div class="empty-state">
          ${escapeHtml(data.note)}
        </div>
      `;

      return;
    }


    /* =====================================================
       EXTRACTED SKILLS
    ===================================================== */

    const extractedSkills =
      Array.isArray(
        data.extracted_skills
      )
        ? data.extracted_skills
        : [];

    let extractedHtml = "";


    if (extractedSkills.length > 0) {

      extractedHtml = `

        <div
          class="card"
          style="margin-bottom:16px;"
        >

          <h3>
            Skills Extracted From Resume
          </h3>

          <div style="margin-top:10px;">

            ${extractedSkills
              .map(
                (skill) =>
                  `
                  <span class="tag">
                    ${escapeHtml(skill)}
                  </span>
                  `
              )
              .join(" ")}

          </div>

        </div>

      `;
    }


    /* =====================================================
       MATCHED SKILLS
    ===================================================== */

    const matchedSkills =
      Array.isArray(
        data.matched_skills
      )
        ? data.matched_skills
        : [];


    const matchedChips =
      matchedSkills
        .map(
          (skill) =>
            `
            <span
              class="tag"
              style="background:var(--cp-accent);"
            >
              ${escapeHtml(skill)}
            </span>
            `
        )
        .join(" ");


    /* =====================================================
       MISSING SKILLS
    ===================================================== */

    const missingSkills =
      Array.isArray(
        data.missing_skills
      )
        ? data.missing_skills
        : [];


    const missingChips =
      missingSkills
        .map(
          (skill) =>
            `
            <span
              class="tag"
              style="background:var(--cp-danger);"
            >
              ${escapeHtml(skill)}
            </span>
            `
        )
        .join(" ");


    /* =====================================================
       LEARNING PRIORITIES
    ===================================================== */

    const priorities =
      Array.isArray(
        data.learning_priorities
      )
        ? data.learning_priorities
        : [];


    const priorityRows =
      priorities
        .map((priority) => {

          const reasons =
            Array.isArray(
              priority.reasons
            )
              ? priority.reasons.join("; ")
              : "";

          return `

            <tr>

              <td>
                ${escapeHtml(
                  priority.skill
                )}
              </td>

              <td>
                ${priorityBadge(
                  priority.priority
                )}
              </td>

              <td>
                ${escapeHtml(
                  priority.priority_score
                )}
              </td>

              <td
                style="
                  font-size:12px;
                  color:var(--cp-text-dim);
                "
              >
                ${escapeHtml(reasons)}
              </td>

            </tr>

          `;
        })
        .join("");


    /* =====================================================
       DISPLAY RESULTS
    ===================================================== */

    resultsEl.innerHTML = `

      ${extractedHtml}


      <!-- MATCH SCORES -->

      <div
        class="grid grid-2"
        style="margin-bottom:16px;"
      >

        <div class="card kpi">

          <div class="value">

            ${escapeHtml(
              data.match_percentage ?? 0
            )}%

          </div>

          <div class="label">
            Simple Match
          </div>

        </div>


        <div class="card kpi">

          <div class="value">

            ${escapeHtml(
              data.weighted_match_score ?? 0
            )}%

          </div>

          <div class="label">
            Weighted Match Score
          </div>

        </div>

      </div>


      <!-- MATCHED SKILLS -->

      <div
        class="card"
        style="margin-bottom:16px;"
      >

        <h3>
          Matched Skills
        </h3>

        <div style="margin-top:10px;">

          ${
            matchedChips ||
            `
              <span class="empty-state">
                None matched yet.
              </span>
            `
          }

        </div>

      </div>


      <!-- MISSING SKILLS -->

      <div
        class="card"
        style="margin-bottom:16px;"
      >

        <h3>
          Missing Skills
        </h3>

        <div style="margin-top:10px;">

          ${
            missingChips ||
            `
              <span class="empty-state">
                No gaps found — great match!
              </span>
            `
          }

        </div>

      </div>


      <!-- LEARNING PRIORITIES -->

      <div class="card">

        <h3>
          Learning Priorities
        </h3>

        <table>

          <thead>

            <tr>
              <th>Skill</th>
              <th>Priority</th>
              <th>Score</th>
              <th>Why</th>
            </tr>

          </thead>


          <tbody>

            ${
              priorityRows ||

              `
                <tr>

                  <td
                    colspan="4"
                    class="empty-state"
                  >
                    Nothing to prioritize.
                  </td>

                </tr>
              `
            }

          </tbody>

        </table>

      </div>

    `;


  } catch (error) {

    console.error(
      "Skill gap analysis error:",
      error
    );


    resultsEl.innerHTML = `

      <div class="empty-state">

        ${escapeHtml(
          error?.message ||
          "Something went wrong while analyzing the resume."
        )}

      </div>

    `;
  }
}


/* =========================================================
   ANALYZE BUTTON
========================================================= */

const analyzeButton =
  document.getElementById("analyze-btn");

if (analyzeButton) {

  analyzeButton.addEventListener(
    "click",
    analyze
  );
}


/* =========================================================
   INITIALIZE
========================================================= */

loadRoles();