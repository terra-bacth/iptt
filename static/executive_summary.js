# -*- coding: utf-8 -*-
"""
Author: Manoj Mishra
"""

async function loadSummary() {
  console.log("✅ loadSummary() called");

  const res = await fetch(
    `/api/execution/project/${PROJECT_ID}/executive-summary`
  );

  if (!res.ok) {
    console.error("❌ API call failed");
    return;
  }

  const data = await res.json();
  console.log("✅ Executive summary data:", data);

  document.getElementById("totalNodes").innerText = data.total_nodes;
  document.getElementById("completedNodes").innerText = data.completed_nodes;
  document.getElementById("inProgressNodes").innerText = data.in_progress_nodes;
  document.getElementById("atRiskNodes").innerText = data.at_risk_nodes;

  // ✅ API gives fraction → convert to %
  document.getElementById("overallProgress").innerText =
    Math.round(data.overall_progress * 100);

  document.getElementById("totalDelay").innerText = data.total_delay_days;

  renderList("topCircles", data.top_circles, "circle");
  renderList("topFacilities", data.top_facilities, "facility_name");
}

function renderList(containerId, list, key) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";

  list.forEach(item => {
    const p = document.createElement("p");
    p.innerHTML =
      `<b>${item[key]}</b>: ${item.delayed_tasks} delayed tasks, ` +
      `${item.total_delay_days} delay days`;
    container.appendChild(p);
  });
}

// ✅ GUARANTEE execution
document.addEventListener("DOMContentLoaded", loadSummary);