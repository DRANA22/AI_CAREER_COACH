document.addEventListener("DOMContentLoaded", () => {
  // Initialize voice input for the job description field
  initVoiceInput("voice-btn", "job-description");

  // ── Resume Analysis ────────────────────────────────────────
  const analyzeForm = document.getElementById("analyze-form");
  if (analyzeForm) {
    analyzeForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const spinner = document.getElementById("spinner");
      const resultSection = document.getElementById("result-section");
      spinner.classList.add("active");
      resultSection.innerHTML = "";

      const formData = new FormData(analyzeForm);
      try {
        const res = await fetch("/analyze", { method: "POST", body: formData });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        renderAnalysis(data.analysis, data.gaps);
      } catch (err) {
        resultSection.innerHTML = `<div class="alert-error">Error: ${err.message}</div>`;
      } finally {
        spinner.classList.remove("active");
      }
    });
  }
});

function renderAnalysis(analysis, gaps) {
  const section = document.getElementById("result-section");
  const score = analysis.match_percentage || 0;

  const missingKeywords = (analysis.missing_keywords || [])
    .map(k => `<span class="tag">${k}</span>`).join("");

  const suggestions = (analysis.improvement_suggestions || [])
    .map(s => `<li style="margin-bottom:0.5rem; color: var(--text-secondary);">${s}</li>`).join("");

  const criticalGaps = (gaps.critical_technical_gaps || [])
    .map(g => `<div style="margin-bottom:0.8rem;">
      <strong>${g.skill}</strong>
      <p style="color:var(--text-secondary); font-size:0.85rem; margin-top:0.2rem;">${g.reason}</p>
    </div>`).join("");

  section.innerHTML = `
    <div class="glass-card fade-in" style="margin-bottom:1.5rem;">
      <h3 style="margin-bottom:1rem; color: var(--accent);">📊 ATS Match Score</h3>
      <div class="score-number">${score}%</div>
      <div class="score-bar-wrapper" style="margin-top:0.5rem;">
        <div class="score-bar-fill" style="width: ${score}%"></div>
      </div>
      <p style="margin-top:1rem; color:var(--text-secondary);">${analysis.profile_summary || ""}</p>
    </div>

    <div class="grid-2" style="margin-bottom:1.5rem;">
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:1rem;">🔑 Missing Keywords</h3>
        <div>${missingKeywords || "<p style='color:var(--text-secondary)'>None detected — great match!</p>"}</div>
      </div>
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:1rem;">💡 Improvement Tips</h3>
        <ul style="list-style:none;">${suggestions}</ul>
      </div>
    </div>

    <div class="glass-card fade-in" style="margin-bottom:1.5rem;">
      <h3 style="margin-bottom:1rem;">🚨 Critical Skill Gaps</h3>
      ${criticalGaps || "<p style='color:var(--text-secondary)'>No critical gaps found!</p>"}
      <div style="margin-top:1rem;">
        <strong style="color:var(--accent-purple);">Priority Action:</strong>
        <p style="color:var(--text-secondary); margin-top:0.3rem;">${gaps.priority_action || ""}</p>
      </div>
    </div>

    <div style="text-align:center; margin-top:1rem;">
      <button class="btn-primary" onclick="generateRoadmap()">🗺️ Generate Learning Roadmap</button>
      <button class="btn-secondary" onclick="speakText('${(analysis.profile_summary || "").replace(/'/g,"")}')"
        style="margin-left:1rem;">🔊 Read Summary Aloud</button>
    </div>
  `;
}

async function generateRoadmap() {
  const roadmapSection = document.getElementById("roadmap-section");
  if (!roadmapSection) return;

  const duration = document.getElementById("duration-select")?.value || "6";
  const role = document.getElementById("target-role")?.value || "Software Engineer";
  const gapsText = document.getElementById("result-section")?.innerText || "";

  roadmapSection.innerHTML = `<div class="spinner active" style="display:block;"></div>`;

  try {
    const res = await fetch("/roadmap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gaps: gapsText, target_role: role, duration })
    });
    const data = await res.json();
    renderRoadmap(data.roadmap);
  } catch (err) {
    roadmapSection.innerHTML = `<div class="alert-error">Error: ${err.message}</div>`;
  }
}

// ── NEW: Updated renderRoadmap with PDF Download Support ────────
function renderRoadmap(roadmap) {
  const section = document.getElementById("roadmap-section");
  if (!Array.isArray(roadmap) || roadmap.length === 0) {
    section.innerHTML = "<p style='color:var(--text-secondary)'>No roadmap generated.</p>";
    return;
  }

  const items = roadmap.map((item, i) => {
    const goals = (item.goals || []).map(g => `<li>${g}</li>`).join("");
    return `
      <div class="timeline-item" style="animation-delay: ${i * 0.1}s;">
        <div class="timeline-month">Month ${item.month}</div>
        <div class="timeline-phase">${item.phase || ""}</div>
        <div class="timeline-focus">${item.focus || ""}</div>
        <ul style="margin-top:0.5rem; color:var(--text-secondary); font-size:0.85rem;">${goals}</ul>
        <div style="margin-top:0.5rem; padding:0.5rem; background:rgba(56,189,248,0.05);
          border-radius:8px; border-left:3px solid var(--accent);">
          <strong style="font-size:0.8rem; color:var(--accent);">🏁 Milestone:</strong>
          <p style="color:var(--text-secondary); font-size:0.85rem;">${item.milestone || ""}</p>
        </div>
      </div>
    `;
  }).join("");

  section.innerHTML = `
    <div class="glass-card fade-in">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;">
        <h3 style="color:var(--accent-purple); margin:0;">🗺️ Your Personalized Learning Roadmap</h3>
        <button id="download-roadmap-btn" class="btn-secondary" style="font-size:0.85rem; padding:0.5rem 1rem;">
          📥 Download PDF
        </button>
      </div>
      <div class="timeline">${items}</div>
    </div>
  `;

  // ── Event Listener for PDF Download ────────────────────────────
  document.getElementById("download-roadmap-btn").addEventListener("click", async () => {
    try {
      const response = await fetch("/download_roadmap", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roadmap: roadmap })
      });

      if (!response.ok) throw new Error("Failed to generate PDF");

      // Handle the file download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "My_Career_Roadmap.pdf";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      alert("Download error: " + err.message);
    }
  });
}
