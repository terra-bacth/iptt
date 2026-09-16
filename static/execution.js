/* Author: Manoj Mishra
*/

// ✅ RESET SAFE HEADER
let executionData = [];
let currentFilter = "all";
let overrideMode = false;
const isViewer = USER_ROLE === "viewer";

/* ================= GROUP MAP ================= */

function getTaskGroup(taskId) {

  if (taskId >= 1 && taskId <= 8) return "Pre-Checks & Readiness";

  if ((taskId >= 9 && taskId <= 13) || (taskId >= 20 && taskId <= 22))
    return "Planning & Initiation";

  if (taskId >= 10 && taskId <= 18)
    return "HW & IRM Logistics";

  if ((taskId === 19) || (taskId >= 23 && taskId <= 29))
    return "Site Installation & Cabling";

  if (taskId >= 30 && taskId <= 36)
    return "System Setup & Handover";

  if (taskId >= 37 && taskId <= 40)
    return "Integration & Clearances";

  if (taskId >= 41 && taskId <= 48)
    return "Testing & Acceptance";

  if (taskId >= 49 && taskId <= 50)
    return "Go-Live & Closure";

  return "General";
}

/* ================= LOAD ================= */

async function loadExecution() {
  try {
    const container = document.getElementById("executionContainer");
    container.innerHTML = "Loading...";

    const res = await fetch(`/api/execution/scope/${SCOPE_ID}`);

    if (!res.ok) {
      alert("❌ Failed to load execution");
      return;
    }

    const json = await res.json();
    executionData = [json];

    renderGrid();

    setTimeout(() => {
      if (USER_ROLE !== "admin") {
        const btn = document.getElementById("overrideBtn");
        if (btn) btn.style.display = "none";
      }
    }, 100);

    setTimeout(scrollToNextTask, 200);

  } catch (err) {
    console.error(err);
    alert("❌ Error loading");
  }
}

async function autoSaveField(el) {

  const row = el.closest("tr");
  
    if (USER_ROLE === "viewer") {
        alert("⚠️ Viewer cannot update execution");
        return;
    }


  // ✅ READ VALUES FIRST
  let actualStart = row.querySelector("[data-field='actual_start']").value || null;
  let actualFinish = row.querySelector("[data-field='actual_finish']").value || null;

  // ✅ ✅ VALIDATION 1 — Finish without Start
  if (actualFinish && !actualStart) {
      alert("❌ Please enter Actual Start before Actual Finish");

      // reset invalid field
      row.querySelector("[data-field='actual_finish']").value = "";

      return; // ✅ STOP API CALL
  }

  // ✅ ✅ VALIDATION 2 — Finish < Start
  if (actualStart && actualFinish && actualFinish < actualStart) {
      alert("❌ Actual Finish cannot be before Actual Start");

      // reset invalid finish date
      row.querySelector("[data-field='actual_finish']").value = "";

      return; // ✅ STOP API CALL
  }

  // ✅ ✅ AUTO STATUS LOGIC
  let newStatus = "Not Started";

  if (actualStart && !actualFinish) {
      newStatus = "In Progress";
  }
  else if (actualFinish) {
      newStatus = "Completed";
  }

  // ✅ ✅ UPDATE UI DROPDOWN IMMEDIATELY
  const statusDropdown = row.querySelector("[data-field='status']");
  if (statusDropdown && statusDropdown.value !== newStatus) {
      statusDropdown.value = newStatus;

      // ✅ visual feedback
      statusDropdown.style.backgroundColor = "#e6f4ea";

      setTimeout(() => {
          statusDropdown.style.backgroundColor = "";
      }, 500);
  }

  // ✅ FINAL UPDATE OBJECT
  const update = {
    scope_id: Number(el.dataset.scope),
    task_id: Number(el.dataset.task),
    task_name: row.children[0].innerText,
    user: USER_ROLE,

    actual_start: actualStart,
    actual_finish: actualFinish,
    status: newStatus,   // ✅ always correct status
    delay_reason: row.querySelector("[data-field='delay_reason']").value || null
  };

  // ✅ API CALL
  const res = await fetch("/api/execution/bulk-update", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify([update])
  });

  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "❌ Update failed");
  }

  // ✅ INPUT SUCCESS FEEDBACK
  el.style.border = "2px solid green";

  setTimeout(() => {
    el.style.border = "";
  }, 800);
}

/* ================= OVERRIDE ================= */

window.toggleOverride = async function() {

  if (USER_ROLE !== "admin") {
    alert("⚠️ Only admin can enable override mode");
    return;
  }

  overrideMode = !overrideMode;

  const btn = document.getElementById("overrideBtn");

  btn.innerText = overrideMode ? "🔓 Override ON" : "🔒 Override OFF";
  btn.style.backgroundColor = overrideMode ? "#dc3545" : "#6c757d";

  // ✅ audit log
  await fetch("/api/execution/log-override", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      user: USER_ROLE,
      action: overrideMode ? "ENABLE_OVERRIDE" : "DISABLE_OVERRIDE"
    })
  });

  renderGrid();
};

/* ================= RENDER ================= */

function renderGrid() {

  const container = document.getElementById("executionContainer");
  container.innerHTML = "";

  executionData.forEach(scope => {

    let nextTaskMarked = false;

    const totalTasks = scope.tasks.length;
    const completedTasks = scope.tasks.filter(t => t.status === "Completed").length;
    const delayedTasks = scope.tasks.filter(t => t.delay_days > 0).length;

    const progressPercent = totalTasks > 0
      ? Math.round((completedTasks / totalTasks) * 100)
      : 0;

    let html = `
      <div class="scope-card">

        <div class="kpi-panel">
          <div>Progress: ${progressPercent}%</div>
          <div>Total: ${totalTasks}</div>
          <div>Completed: ${completedTasks}</div>
          <div>Pending: ${totalTasks - completedTasks}</div>
          <div>Delayed: ${delayedTasks}</div>
        </div>

        ${overrideMode ? `
          <div class="alert-banner alert-danger">
            ⚠️ Override Mode ACTIVE
          </div>` : ""}

        <div class="scope-header">
          ${scope.scope_name} (${scope.circle})
        </div>
    `;

    /* ===== GROUP TASKS ===== */

    const groupedTasks = {};

    scope.tasks.forEach(t => {
      console.log("Task #:", t.task_number, t.task_name);   // ✅ ADD HERE
      const group = getTaskGroup(t.task_number);

      if (!groupedTasks[group]) groupedTasks[group] = [];
      groupedTasks[group].push(t);
    });

    /* ===== RENDER GROUPS ===== */

    Object.keys(groupedTasks).forEach(group => {

        const tasks = groupedTasks[group];
      
        // ✅ Phase progress calculation
        const total = tasks.length;
        const completed = tasks.filter(t => t.status === "Completed").length;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
        
        // ✅ ADD COLOR LOGIC HERE
        let color = "red";
        if (percent === 100) color = "green";
        else if (percent > 0) color = "orange";


        const autoOpen = false;

          html += `
            <div class="task-group">
    
              <div class="group-header" onclick="toggleGroup(this)">    
                ▶ ${group}
                (${completed}/${total} ✅ | <span style="color:${color}">${percent}%</span>)
              </div>
    
              <div class="group-content" style="display:none;">
                <table>
                  <tr>
                    <th>Task</th>
                    <th>P.Start</th>
                    <th>P.Finish</th>
                    <th>A.Start</th>
                    <th>A.Finish</th>
                    <th>Status</th>
                    <th>Delay</th>
                    <th>Reason</th>
                  </tr>
          `;

      tasks.forEach(t => {

        let highlight = "";
        let isEditable = false;

        if (overrideMode) {
          isEditable = true;
        } else if (!nextTaskMarked && t.status !== "Completed") {
          highlight = "next-task";
          nextTaskMarked = true;
          isEditable = true;
        }

        let disableFinish = !t.actual_start;

        html += `
          <tr class="${highlight}">
            <td>
              ${t.task_name}
              ${highlight ? "<br><small>➡ Next</small>" : ""}

              ${(t.status !== "Completed" && isEditable) ? `
                <br>
                <button onclick="quickComplete(this, ${scope.scope_id}, ${t.task_id})">
                  ✅ Complete
                </button>
              ` : ""}
            </td>

            <td>
              ${
                t.revised_start
                  ? `<span style="color:green; font-weight:600;">${t.revised_start}</span>
                     <br><small style="color:#888;">Planned: ${t.planned_start}</small>`
                  : (t.planned_start || "")
              }
            </td>
            
            <td>
              ${
                t.revised_finish
                  ? `<span style="color:green; font-weight:600;">${t.revised_finish}</span>
                     <br><small style="color:#888;">Planned: ${t.planned_finish}</small>`
                  : (t.planned_finish || "")
              }
            </td>

            <td>
              <input type="date" 
                ${isViewer ? "disabled" : ""}                               
                data-task="${t.task_id}"
                data-scope="${scope.scope_id}"
                data-field="actual_start"
                value="${t.actual_start || ""}"
                onchange="autoSaveField(this)">
            </td>


            <td>
              <input type="date"
                ${isViewer ? "disabled" : ""}
                data-task="${t.task_id}"
                data-scope="${scope.scope_id}"
                data-field="actual_finish"
                value="${t.actual_finish || ""}"
                onchange="autoSaveField(this)">
            </td>

            
            <td>
              <select
                ${isViewer ? "disabled" : ""}
                data-task="${t.task_id}"
                data-scope="${scope.scope_id}"
                data-field="status"
                onchange="autoSaveField(this)">
                
                ${["Not Started", "In Progress", "Completed", "Blocked"]
                  .map(s => `
                    <option value="${s}" ${s === t.status ? "selected" : ""}>
                      ${s}
                    </option>
                  `).join("")}
            
              </select>
            </td>

            <td>${t.delay_days}</td>

            <td>
              <input type="text"
                ${isViewer ? "disabled" : ""}
                ${!isEditable ? "disabled" : ""}
                data-task="${t.task_id}"
                data-scope="${scope.scope_id}"
                data-field="delay_reason"
                value="${t.delay_reason || ""}"
                onblur="autoSaveField(this)">
            </td>
          </tr>
        `;
      });

      html += `
            </table>
          </div>
        </div>
      `;
    });

    html += "</div>";

    // ✅ ✅ IMPORTANT FIX HERE
    container.innerHTML += html;

  });
}
/* ✅ GROUP TOGGLE */

function toggleGroup(el) {

  const content = el.nextElementSibling;

  if (content.style.display === "none") {
    content.style.display = "block";
    el.innerHTML = el.innerHTML.replace("▶", "▼");
  } else {
    content.style.display = "none";
    el.innerHTML = el.innerHTML.replace("▼", "▶");
  }
}

/* ================= QUICK COMPLETE ================= */

async function quickComplete(btn, scope_id, task_id) {

  // ✅ Immediate feedback
  btn.innerText = "⏳ Completing...";
  btn.disabled = true;

  const today = new Date().toISOString().split("T")[0];

  const res = await fetch("/api/execution/bulk-update", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify([{
      scope_id,
      task_id,
      actual_start: today,
      actual_finish: today,
      status: "Completed"
    }])
  });

  if (!res.ok) {
    alert("❌ Failed to complete task");
    btn.innerText = "✅ Complete";
    btn.disabled = false;
    return;
  }

  // ✅ SUCCESS UI UPDATE (no reload)
  btn.innerText = "✔ Completed";
  btn.style.backgroundColor = "#6c757d";

  // ✅ update row visually
  const row = btn.closest("tr");

  // update status text
  const statusCell = row.querySelector("[data-field='status']");
  if (statusCell) statusCell.value = "Completed";

  // update actual dates in UI
  const todayStr = today;

  const startInput = row.querySelector("[data-field='actual_start']");
  const finishInput = row.querySelector("[data-field='actual_finish']");

  if (startInput) startInput.value = todayStr;
  if (finishInput) finishInput.value = todayStr;

  // ✅ optional: change row style
  row.classList.add("status-completed");

}
/* ================= SCROLL ================= */

function scrollToNextTask() {

  const rows = document.querySelectorAll("tr");

  for (let row of rows) {
    if (row.classList.contains("next-task")) {
      row.scrollIntoView({
        behavior: "smooth",
        block: "center"
      });
      break;
    }
  }
}

/* ================= DOWNLOAD ================= */

function downloadExecution() {
  window.open(`/api/execution/scope/${SCOPE_ID}/download`);
}

/* ================= UPLOAD ================= */

async function uploadExcel() {
  const fileInput = document.getElementById("excelFile");

  if (!fileInput.files.length) {
    alert("Select file");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  const res = await fetch(`/api/execution/scope/${SCOPE_ID}/upload`, {
    method: "POST",
    body: formData
  });

  if (res.ok) {
    alert("✅ Uploaded");
    loadExecution();
  } else {
    const error = await res.json();
    alert(error.detail || "Upload failed");
  }
}

function uploadCirclePlan() {

    if (!CURRENT_CIRCLE) {
        alert("⚠ Please select a circle first");
        return;
    }

    const input = document.getElementById("circleUploadFile");

    if (!input.files.length) {
        alert("⚠ Please choose a file first");
        return;
    }

    const file = input.files[0];

    const formData = new FormData();
    formData.append("file", file);

    fetch(`/api/execution/circle/${CURRENT_CIRCLE}/upload`, {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        alert(data.message || "✅ Upload successful");
        location.reload(); // ✅ force refresh
    })
    .catch(err => {
        console.error(err);
        alert("❌ Upload failed");
    });
}