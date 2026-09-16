
async function loadHeatmap() {
  const res = await fetch(
    `/api/execution/project/${PROJECT_ID}/delay-heatmap`
  );

  const data = await res.json();

  renderHeatmap("circleHeatmap", data.by_circle, "circle");
  renderHeatmap("facilityHeatmap", data.by_facility, "facility_name");
}

function renderHeatmap(containerId, rows, keyName) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  rows.forEach(r => {
    let intensity = Math.min(255, r.total_delay_days * 10);
    let color = `rgb(255, ${255 - intensity}, ${255 - intensity})`;

    const div = document.createElement("div");
    div.style.background = color;
    div.style.padding = "10px";
    div.style.margin = "6px 0";
    div.style.borderRadius = "6px";

    div.innerHTML = `
      <strong>${r[keyName]}</strong><br>
      Delayed Tasks: ${r.delayed_tasks}<br>
      Total Delay Days: ${r.total_delay_days}
    `;

    container.appendChild(div);
  });
}