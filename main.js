/* ═══════════════════════════════════════════════════════════════
   AI CAREER OS — Main JavaScript
   ═══════════════════════════════════════════════════════════════ */

// ─────────────────────────────────────────────────────────────────
//  GLOBAL STATE
// ─────────────────────────────────────────────────────────────────
let chatHistory = [];
let currentQuestions = [];
let currentRole = "Software Engineer";

async function parseJSONResponse(res) {
  const contentType = (res.headers.get("content-type") || "").toLowerCase();

  if (!res.ok) {
    let errText = `Request failed with status ${res.status}`;
    if (contentType.includes("application/json")) {
      try {
        const errJson = await res.json();
        errText = errJson.error || errJson.message || JSON.stringify(errJson);
      } catch {
        const text = await res.text();
        errText = text || errText;
      }
    } else {
      const text = await res.text();
      errText = text || errText;
    }
    throw new Error(errText.trim());
  }

  if (contentType.includes("application/json")) {
    return await res.json();
  }

  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// ─────────────────────────────────────────────────────────────────
//  INITIALIZATION
// ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Init voice input
  if (typeof initVoiceInput === "function") {
    initVoiceInput("voice-btn", "job-description");
  }

  // Init tabs
  initTabs();

  // Init resume form
  initResumeForm();

  // Init chat enter key
  const chatInput = document.getElementById("chat-input");
  if (chatInput) {
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });
  }

  // Load initial data
  loadCareerStats();
  loadCommunityFeed();
  loadAchievements();
  loadLeaderboard();
});

// ─────────────────────────────────────────────────────────────────
//  TAB SYSTEM
// ─────────────────────────────────────────────────────────────────
function initTabs() {
  const tabBtns = document.querySelectorAll(".tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.dataset.tab;
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  // Deactivate all
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

  // Activate selected
  const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  const content = document.getElementById(`tab-${tabId}`);
  if (btn) btn.classList.add("active");
  if (content) content.classList.add("active");

  // Load data on tab switch
  if (tabId === "community") loadCommunityFeed();
  if (tabId === "achievements") { loadAchievements(); loadLeaderboard(); }
}

// ─────────────────────────────────────────────────────────────────
//  CAREER STATS (Overview)
// ─────────────────────────────────────────────────────────────────
async function loadCareerStats() {
  try {
    const res = await fetch("/api/career-stats");
    if (!res.ok) return;
    const data = await parseJSONResponse(res);

    // Update XP bar
    const xpBar = document.getElementById("xp-bar");
    const xpNext = document.getElementById("xp-to-next");
    if (xpBar) xpBar.style.width = `${data.xp_progress || 0}%`;
    if (xpNext) xpNext.textContent = `${data.xp_to_next_level || 0} XP to next level`;

    // Update stat cards
    updateStat("stat-streak", data.streak || 0);
    updateStat("stat-resume", `${data.resume_score || 0}%`);
    updateStat("stat-placement", `${data.placement_chance || 25}%`);
    updateStat("stat-interviews", data.interviews_done || 0);
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

function updateStat(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ─────────────────────────────────────────────────────────────────
//  CAREER AI CHAT
// ─────────────────────────────────────────────────────────────────
async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  input.value = "";

  // Add user bubble
  addChatBubble(message, "user");
  chatHistory.push({ role: "user", content: message });

  // Add typing indicator
  const typingId = addTypingIndicator();

  try {
    const res = await fetch("/api/career-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: chatHistory })
    });

    const data = await parseJSONResponse(res);
    removeTypingIndicator(typingId);

    if (data.success) {
      addChatBubble(data.response, "ai");
      chatHistory.push({ role: "ai", content: data.response });
      showXPToast(data.xp_earned);

      if (data.achievement) {
        showAchievementToast(data.achievement);
      }
    } else {
      addChatBubble("Sorry, something went wrong. Please try again.", "ai");
    }
  } catch (err) {
    removeTypingIndicator(typingId);
    addChatBubble("Connection error. Please check your internet and try again.", "ai");
  }
}

function quickChat(message) {
  const input = document.getElementById("chat-input");
  if (input) {
    input.value = message;
    sendChatMessage();
  }
}

function addChatBubble(text, type) {
  const container = document.getElementById("chat-messages");
  if (!container) return;

  const wrapper = document.createElement("div");
  wrapper.className = `chat-bubble-wrapper ${type} fade-in`;

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar";
  if (type === "ai") {
    avatar.innerHTML = `<div style="background:transparent; width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:var(--accent-cyan); font-weight:bold; font-size:1.2rem;">∅</div>`;
  } else {
    avatar.innerHTML = `<div style="background:var(--gradient-accent); width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:bold;">U</div>`;
  }

  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${type}`;
  bubble.textContent = text;

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}

function addTypingIndicator() {
  const container = document.getElementById("chat-messages");
  if (!container) return null;

  const id = "typing-" + Date.now();
  const wrapper = document.createElement("div");
  wrapper.className = `chat-bubble-wrapper ai fade-in`;
  wrapper.id = id;

  const avatar = document.createElement("div");
  avatar.className = "chat-avatar";
  avatar.innerHTML = `<div style="background:transparent; width:100%; height:100%; display:flex; align-items:center; justify-content:center; color:var(--accent-cyan); font-weight:bold; font-size:1.2rem;">∅</div>`;

  const bubble = document.createElement("div");
  bubble.className = "chat-bubble ai";
  bubble.innerHTML = `<div class="typing-dots"><span></span><span></span><span></span></div>`;

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  if (id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }
}

// ─────────────────────────────────────────────────────────────────
//  RESUME ANALYSIS
// ─────────────────────────────────────────────────────────────────
function initResumeForm() {
  const form = document.getElementById("analyze-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const spinner = document.getElementById("resume-spinner");
    const resultSection = document.getElementById("resume-result-section");
    if (spinner) spinner.classList.add("active");
    if (resultSection) resultSection.innerHTML = "";

    const formData = new FormData(form);

    try {
      const res = await fetch("/api/analyze-resume", { method: "POST", body: formData });
      const data = await parseJSONResponse(res);

      if (data.error) throw new Error(data.error);

      renderResumeAnalysis(data.analysis, data.gaps);
      showXPToast(data.xp_earned);

      if (data.achievement) showAchievementToast(data.achievement);
      if (data.score_achievement) showAchievementToast(data.score_achievement);
      if (data.leveled_up) showXPToast(0, "🎉 Level Up!");

      loadCareerStats();
    } catch (err) {
      if (resultSection) {
        resultSection.innerHTML = `<div class="alert-error">Error: ${err.message}</div>`;
      }
    } finally {
      if (spinner) spinner.classList.remove("active");
    }
  });
}

function renderResumeAnalysis(analysis, gaps) {
  const section = document.getElementById("resume-result-section");
  if (!section) return;

  const score = analysis.ats_score || analysis.match_percentage || 0;
  const scoreColor = score >= 70 ? "var(--success)" : score >= 40 ? "var(--warning)" : "var(--danger)";

  const missingTags = (analysis.missing_keywords || [])
    .map(k => `<span class="tag danger">${k}</span>`).join("");
  const matchedTags = (analysis.matched_keywords || [])
    .map(k => `<span class="tag success">${k}</span>`).join("");

  const suggestions = (analysis.improvement_suggestions || [])
    .map(s => `<li style="margin-bottom:0.5rem; color:var(--text-secondary); font-size:0.88rem;">${s}</li>`).join("");

  const strengths = (analysis.strengths || [])
    .map(s => `<span class="tag success">${s}</span>`).join("");
  const redFlags = (analysis.red_flags || [])
    .map(f => `<span class="tag danger">${f}</span>`).join("");

  const sectionScores = analysis.section_scores || {};
  const sectionBars = Object.entries(sectionScores).map(([key, val]) => {
    const label = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    const color = val >= 70 ? "var(--success)" : val >= 40 ? "var(--warning)" : "var(--danger)";
    return `<div class="factor-bar">
      <span class="factor-label">${label}</span>
      <div class="factor-track">
        <div class="factor-fill" style="width:${val}%; background:${color};"></div>
      </div>
      <span class="factor-value">${val}%</span>
    </div>`;
  }).join("");

  const criticalGaps = (gaps.critical_technical_gaps || [])
    .map(g => `<div style="margin-bottom:0.8rem;">
      <strong>${g.skill}</strong>
      <p style="color:var(--text-secondary); font-size:0.82rem; margin-top:0.15rem;">${g.reason}</p>
      ${g.resource ? `<p style="font-size:0.78rem; color:var(--accent-cyan); margin-top:0.15rem;">📚 ${g.resource}</p>` : ""}
    </div>`).join("");

  section.innerHTML = `
    <div class="glass-card fade-in" style="margin-bottom:1.25rem; text-align:center;">
      <h3 style="margin-bottom:0.75rem; color:var(--accent-cyan);">📊 ATS Match Score</h3>
      <div class="score-number" style="color:${scoreColor};">${score}%</div>
      <div class="score-bar-wrapper" style="margin-top:0.75rem; max-width:400px; margin-left:auto; margin-right:auto;">
        <div class="score-bar-fill" style="width:${score}%;"></div>
      </div>
      <p style="margin-top:0.75rem; color:var(--text-secondary); font-size:0.9rem;">${analysis.profile_summary || ""}</p>
    </div>

    ${sectionBars ? `<div class="glass-card fade-in" style="margin-bottom:1.25rem;">
      <h3 style="margin-bottom:1rem;">📋 Section Scores</h3>
      ${sectionBars}
    </div>` : ""}

    <div class="grid-2" style="margin-bottom:1.25rem;">
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:0.75rem;">✅ Matched Keywords</h3>
        <div>${matchedTags || "<p style='color:var(--text-muted); font-size:0.85rem;'>None detected</p>"}</div>
      </div>
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:0.75rem;">❌ Missing Keywords</h3>
        <div>${missingTags || "<p style='color:var(--text-muted); font-size:0.85rem;'>None — great match!</p>"}</div>
      </div>
    </div>

    <div class="grid-2" style="margin-bottom:1.25rem;">
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:0.75rem;">💪 Strengths</h3>
        <div>${strengths || "<p style='color:var(--text-muted); font-size:0.85rem;'>Upload resume for analysis</p>"}</div>
      </div>
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:0.75rem;">⚠️ Red Flags</h3>
        <div>${redFlags || "<p style='color:var(--text-muted); font-size:0.85rem;'>None detected!</p>"}</div>
      </div>
    </div>

    ${criticalGaps ? `<div class="glass-card fade-in" style="margin-bottom:1.25rem;">
      <h3 style="margin-bottom:0.75rem;">🚨 Critical Skill Gaps</h3>
      ${criticalGaps}
      <div style="margin-top:1rem; padding:0.75rem; background:rgba(167,139,250,0.06); border-radius:var(--radius-md); border-left:3px solid var(--accent-purple);">
        <strong style="color:var(--accent-purple); font-size:0.85rem;">Priority Action:</strong>
        <p style="color:var(--text-secondary); font-size:0.85rem; margin-top:0.2rem;">${gaps.priority_action || ""}</p>
      </div>
    </div>` : ""}

    <div class="glass-card fade-in">
      <h3 style="margin-bottom:0.75rem;">💡 Improvement Suggestions</h3>
      <ul style="list-style:none;">${suggestions}</ul>
    </div>
  `;
}

// ─────────────────────────────────────────────────────────────────
//  MOCK INTERVIEW
// ─────────────────────────────────────────────────────────────────
async function startInterview() {
  const role = document.getElementById("interview-role").value;
  const difficulty = document.getElementById("interview-difficulty").value;
  const spinner = document.getElementById("interview-spinner");
  const section = document.getElementById("interview-questions-section");

  currentRole = role;
  if (spinner) spinner.classList.add("active");
  if (section) section.innerHTML = "";

  try {
    const res = await fetch("/api/mock-interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role, difficulty })
    });

    const data = await parseJSONResponse(res);
    if (data.success) {
      currentQuestions = data.questions;
      renderInterviewQuestions(data.questions);
    }
  } catch (err) {
    if (section) section.innerHTML = `<div class="alert-error">Failed to generate questions. Try again.</div>`;
  } finally {
    if (spinner) spinner.classList.remove("active");
  }
}

function renderInterviewQuestions(questions) {
  const section = document.getElementById("interview-questions-section");
  if (!section) return;

  const cards = questions.map((q, i) => `
    <div class="interview-card fade-in" id="interview-q-${i}">
      <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:0.5rem;">
        <span class="q-type ${q.type}">${q.type.replace("_", " ")}</span>
        <span style="font-size:0.75rem; color:var(--text-muted);">⏱️ ${q.time_limit || 120}s</span>
      </div>
      <div class="question-text">Q${i + 1}: ${q.question}</div>
      <div class="tip-text">💡 Tip: ${q.tips || ""}</div>
      <textarea id="answer-${i}" placeholder="Type your answer here..."></textarea>
      <div style="margin-top:0.5rem; display:flex; gap:0.5rem; align-items:center;">
        <button class="btn-primary" style="font-size:0.82rem; padding:0.5rem 1rem;"
          onclick="submitAnswer(${i}, '${q.question.replace(/'/g, "\\'")}')">
          📝 Submit Answer
        </button>
        <span id="answer-status-${i}" style="font-size:0.8rem; color:var(--text-muted);"></span>
      </div>
      <div id="eval-${i}"></div>
    </div>
  `).join("");

  section.innerHTML = cards;
}

async function submitAnswer(index, question) {
  const answerEl = document.getElementById(`answer-${index}`);
  const statusEl = document.getElementById(`answer-status-${index}`);
  const evalEl = document.getElementById(`eval-${index}`);

  const answer = answerEl ? answerEl.value.trim() : "";
  if (!answer) {
    if (statusEl) statusEl.textContent = "Please write an answer first.";
    return;
  }

  if (statusEl) statusEl.textContent = "Evaluating...";

  try {
    const res = await fetch("/api/evaluate-answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answer, role: currentRole })
    });

    const data = await parseJSONResponse(res);
    if (statusEl) statusEl.textContent = "";

    if (data.success) {
      const ev = data.evaluation;
      const strengths = (ev.strengths || []).map(s => `<span class="tag success">${s}</span>`).join("");
      const improvements = (ev.improvements || []).map(s => `<span class="tag danger">${s}</span>`).join("");

      if (evalEl) {
        evalEl.innerHTML = `
          <div class="eval-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
              <div>
                <span class="eval-grade">${ev.grade}</span>
                <span style="color:var(--text-secondary); font-size:0.85rem; margin-left:0.5rem;">${ev.score}/100</span>
              </div>
              <span style="font-size:0.78rem; color:var(--text-muted);">Confidence: ${ev.confidence_level}</span>
            </div>
            <p style="font-size:0.88rem; color:var(--text-secondary); margin-bottom:0.5rem;">${ev.feedback}</p>
            ${strengths ? `<div style="margin-bottom:0.3rem;"><strong style="font-size:0.78rem;">Strengths:</strong> ${strengths}</div>` : ""}
            ${improvements ? `<div><strong style="font-size:0.78rem;">Improve:</strong> ${improvements}</div>` : ""}
          </div>
        `;
      }

      showXPToast(data.xp_earned);
      if (data.achievement) showAchievementToast(data.achievement);
      loadCareerStats();
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = "Error evaluating. Try again.";
  }
}

// ─────────────────────────────────────────────────────────────────
//  ROADMAP GENERATION
// ─────────────────────────────────────────────────────────────────
async function generateRoadmap() {
  const role = document.getElementById("roadmap-role").value;
  const duration = document.getElementById("roadmap-duration").value;
  const gaps = document.getElementById("roadmap-gaps").value;
  const spinner = document.getElementById("roadmap-spinner");
  const section = document.getElementById("roadmap-section");

  if (spinner) spinner.classList.add("active");
  if (section) section.innerHTML = "";

  try {
    const res = await fetch("/api/generate-roadmap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_role: role, duration, gaps })
    });

    const data = await parseJSONResponse(res);
    if (data.success) {
      renderRoadmap(data.roadmap);
      showXPToast(data.xp_earned);
      if (data.achievement) showAchievementToast(data.achievement);
    }
  } catch (err) {
    if (section) section.innerHTML = `<div class="alert-error">Failed to generate roadmap. Try again.</div>`;
  } finally {
    if (spinner) spinner.classList.remove("active");
  }
}

let lastGeneratedRoadmap = null;

function renderRoadmap(roadmap) {
  const section = document.getElementById("roadmap-section");
  if (!section || !Array.isArray(roadmap) || roadmap.length === 0) {
    if (section) section.innerHTML = "<p style='color:var(--text-muted)'>No roadmap generated.</p>";
    return;
  }

  lastGeneratedRoadmap = roadmap;

  const items = roadmap.map((item, i) => {
    const goals = (item.goals || []).map(g => `<li>${g}</li>`).join("");
    const resources = (item.resources || []).map(r => `<span class="tag info">${r}</span>`).join(" ");

    return `
      <div class="timeline-item" style="animation-delay: ${i * 0.12}s;">
        <div class="timeline-month">Month ${item.month}</div>
        <div class="timeline-phase">${item.phase || ""}</div>
        <div class="timeline-focus">${item.focus || ""}</div>
        <ul style="margin-top:0.4rem; color:var(--text-secondary); font-size:0.85rem; padding-left:1rem;">${goals}</ul>
        ${resources ? `<div style="margin-top:0.4rem;">${resources}</div>` : ""}
        <div style="margin-top:0.5rem; padding:0.5rem; background:rgba(6,214,160,0.04);
          border-radius:var(--radius-sm); border-left:3px solid var(--accent-cyan);">
          <strong style="font-size:0.78rem; color:var(--accent-cyan);">🏁 Milestone:</strong>
          <p style="color:var(--text-secondary); font-size:0.82rem;">${item.milestone || ""}</p>
        </div>
      </div>
    `;
  }).join("");

  section.innerHTML = `
    <div class="glass-card fade-in">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;">
        <h3 style="color:var(--accent-purple); margin:0;">🗺️ Your Personalized Roadmap</h3>
        <button class="btn-primary" style="font-size:0.82rem; padding:0.5rem 1rem;" onclick="downloadRoadmapPDF()">
          📥 Download PDF
        </button>
      </div>
      <div class="timeline">${items}</div>
    </div>
  `;
}

async function downloadRoadmapPDF() {
  if (!lastGeneratedRoadmap) {
    alert("No roadmap to download. Generate one first.");
    return;
  }

  try {
    const res = await fetch("/api/download-roadmap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ roadmap: lastGeneratedRoadmap })
    });

    if (!res.ok) {
      const err = await parseJSONResponse(res);
      throw new Error(err.error || "Download failed");
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "My_Career_Roadmap.pdf";
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();

    showXPToast(0, "📥 Roadmap PDF Downloaded!");
  } catch (err) {
    alert("Download error: " + err.message);
  }
}

// ─────────────────────────────────────────────────────────────────
//  PLACEMENT PREDICTION
// ─────────────────────────────────────────────────────────────────
async function predictPlacement() {
  const spinner = document.getElementById("placement-spinner");
  const section = document.getElementById("placement-result-section");
  const btn = document.getElementById("predict-btn");

  if (spinner) spinner.classList.add("active");
  if (btn) btn.disabled = true;
  if (section) section.innerHTML = "";

  try {
    const res = await fetch("/api/predict-placement", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });

    const data = await parseJSONResponse(res);
    if (data.success) {
      renderPlacementPrediction(data.prediction);
      showXPToast(data.xp_earned);
      if (data.achievement) showAchievementToast(data.achievement);
      loadCareerStats();
    }
  } catch (err) {
    if (section) section.innerHTML = `<div class="alert-error">Prediction failed. Try again.</div>`;
  } finally {
    if (spinner) spinner.classList.remove("active");
    if (btn) btn.disabled = false;
  }
}

function renderPlacementPrediction(pred) {
  const section = document.getElementById("placement-result-section");
  if (!section) return;

  const chance = pred.placement_chance || 50;
  const chanceColor = chance >= 70 ? "var(--success)" : chance >= 40 ? "var(--warning)" : "var(--danger)";

  const factors = pred.factors || {};
  const factorBars = Object.entries(factors).map(([key, val]) => {
    const label = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    const color = val >= 70 ? "var(--success)" : val >= 40 ? "var(--warning)" : "var(--danger)";
    return `<div class="factor-bar">
      <span class="factor-label">${label}</span>
      <div class="factor-track">
        <div class="factor-fill" style="width:${val}%; background:${color};"></div>
      </div>
      <span class="factor-value">${val}%</span>
    </div>`;
  }).join("");

  const strengths = (pred.top_strengths || []).map(s => `<span class="tag success">${s}</span>`).join(" ");
  const improvements = (pred.critical_improvements || []).map(s => `<span class="tag danger">${s}</span>`).join(" ");
  const companies = (pred.recommended_companies || []).map(c => `<span class="tag purple">${c}</span>`).join(" ");

  section.innerHTML = `
    <div class="glass-card fade-in" style="text-align:center; margin-bottom:1.25rem;">
      <h3 style="margin-bottom:0.75rem;">🔮 Placement Chance</h3>
      <div class="score-number" style="font-size:4rem;">${chance}%</div>
      <div class="score-bar-wrapper" style="max-width:350px; margin:0.75rem auto;">
        <div class="score-bar-fill" style="width:${chance}%;"></div>
      </div>
      <div style="display:flex; justify-content:center; gap:2rem; margin-top:1rem;">
        <div>
          <div style="font-size:0.78rem; color:var(--text-muted);">Timeframe</div>
          <div style="font-weight:700; color:var(--accent-cyan);">${pred.timeframe || "N/A"}</div>
        </div>
        <div>
          <div style="font-size:0.78rem; color:var(--text-muted);">Confidence</div>
          <div style="font-weight:700; color:var(--accent-purple);">${pred.confidence_score || 5}/10</div>
        </div>
        <div>
          <div style="font-size:0.78rem; color:var(--text-muted);">Salary Range</div>
          <div style="font-weight:700; color:var(--accent-orange);">${pred.salary_range || "N/A"}</div>
        </div>
      </div>
    </div>

    <div class="glass-card fade-in" style="margin-bottom:1.25rem;">
      <h3 style="margin-bottom:1rem;">📊 Factor Breakdown</h3>
      ${factorBars}
    </div>

    <div class="grid-2" style="margin-bottom:1.25rem;">
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:0.75rem;">💪 Strengths</h3>
        <div>${strengths || "<p style='color:var(--text-muted); font-size:0.85rem;'>Build more experience</p>"}</div>
      </div>
      <div class="glass-card fade-in">
        <h3 style="margin-bottom:0.75rem;">🎯 Critical Improvements</h3>
        <div>${improvements || "<p style='color:var(--text-muted); font-size:0.85rem;'>Keep going!</p>"}</div>
      </div>
    </div>

    ${companies ? `<div class="glass-card fade-in" style="margin-bottom:1.25rem;">
      <h3 style="margin-bottom:0.75rem;">🏢 Recommended Companies</h3>
      <div>${companies}</div>
    </div>` : ""}

    <div class="glass-card fade-in" style="border-left:3px solid var(--accent-cyan);">
      <h3 style="margin-bottom:0.5rem;">⚡ Next Best Action</h3>
      <p style="color:var(--text-secondary); font-size:0.9rem;">${pred.next_action || "Keep building skills and applying!"}</p>
    </div>
  `;
}

// ─────────────────────────────────────────────────────────────────
//  COMMUNITY
// ─────────────────────────────────────────────────────────────────
async function loadCommunityFeed() {
  const feed = document.getElementById("community-feed");
  if (!feed) return;

  try {
    const res = await fetch("/api/community/feed");
    const data = await parseJSONResponse(res);

    if (data.success && data.posts.length > 0) {
      feed.innerHTML = data.posts.map(post => {
        const initials = (post.author || "?").split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
        const typeEmoji = post.type === "question" ? "❓" : post.type === "achievement" ? "🏆" : "💬";
        const timeAgo = getTimeAgo(post.timestamp);

        return `
          <div class="post-card fade-in">
            <div class="post-header">
              <div class="post-avatar">${initials}</div>
              <div>
                <div class="post-author">${post.author || "Anonymous"} 
                  <span style="font-size:0.7rem; color:var(--accent-cyan);">LVL ${post.author_level || 1}</span>
                </div>
                <div class="post-meta">${typeEmoji} ${post.type || "discussion"} · ${timeAgo}</div>
              </div>
            </div>
            <div class="post-content">${post.content}</div>
            <div class="post-actions">
              <button onclick="likePost('${post.id}', this)">❤️ ${post.likes || 0}</button>
            </div>
          </div>
        `;
      }).join("");
    } else {
      feed.innerHTML = `
        <div class="glass-card" style="text-align:center; padding:2rem;">
          <div style="font-size:2rem; margin-bottom:0.5rem;">👥</div>
          <p style="color:var(--text-muted);">No posts yet. Be the first to share!</p>
        </div>
      `;
    }
  } catch (err) {
    feed.innerHTML = `<div class="alert-error">Failed to load community feed.</div>`;
  }
}

async function submitPost() {
  const input = document.getElementById("community-post-input");
  const typeEl = document.getElementById("post-type");
  const content = input ? input.value.trim() : "";
  const postType = typeEl ? typeEl.value : "discussion";

  if (!content) return;

  try {
    const res = await fetch("/api/community/post", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, type: postType })
    });

    const data = await parseJSONResponse(res);
    if (data.success) {
      if (input) input.value = "";
      showXPToast(data.xp_earned);
      loadCommunityFeed();
    }
  } catch (err) {
    console.error("Post failed:", err);
  }
}

async function likePost(postId, btn) {
  try {
    const res = await fetch("/api/community/like", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ post_id: postId })
    });

    const data = await parseJSONResponse(res);
    if (data.success) {
      btn.textContent = `❤️ ${data.likes}`;
    }
  } catch (err) {
    console.error("Like failed:", err);
  }
}

function getTimeAgo(timestamp) {
  if (!timestamp) return "just now";
  try {
    const diff = Date.now() - new Date(timestamp).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  } catch {
    return "recently";
  }
}

// ─────────────────────────────────────────────────────────────────
//  ACHIEVEMENTS & LEADERBOARD
// ─────────────────────────────────────────────────────────────────
async function loadAchievements() {
  const grid = document.getElementById("achievements-grid");
  if (!grid) return;

  try {
    const res = await fetch("/api/career-stats");
    const data = await parseJSONResponse(res);

    const userAch = data.achievements || [];
    const allAch = data.all_achievements || {};

    grid.innerHTML = Object.entries(allAch).map(([id, ach]) => {
      const unlocked = userAch.includes(id);
      return `
        <div class="achievement-card ${unlocked ? "" : "locked"}">
          <div class="achievement-icon">${ach.icon}</div>
          <div class="achievement-name">${ach.name}</div>
          <div class="achievement-desc">${ach.desc}</div>
          <div class="achievement-xp">+${ach.xp} XP</div>
        </div>
      `;
    }).join("");
  } catch (err) {
    grid.innerHTML = `<p style="color:var(--text-muted);">Failed to load achievements.</p>`;
  }
}

async function loadLeaderboard() {
  const section = document.getElementById("leaderboard-section");
  if (!section) return;

  try {
    const res = await fetch("/api/leaderboard");
    const data = await parseJSONResponse(res);

    if (data.success && data.leaders.length > 0) {
      section.innerHTML = `
        <div class="leaderboard-card">
          <div class="leaderboard-header">
            <span>Rank</span>
            <span>Player</span>
            <span>Level</span>
            <span>Streak</span>
            <span>XP</span>
          </div>
          ${data.leaders.map((leader, i) => {
            const rankClass = i === 0 ? "gold" : i === 1 ? "silver" : i === 2 ? "bronze" : "";
            const rankIcon = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i + 1}`;

            return `
              <div class="leader-row">
                <span class="rank ${rankClass}">${rankIcon}</span>
                <span class="leader-name">${leader.name}</span>
                <span class="leader-meta">LVL ${leader.level}</span>
                <span class="leader-meta">🔥 ${leader.streak}</span>
                <span class="leader-xp">${leader.xp} XP</span>
              </div>
            `;
          }).join("")}
        </div>
      `;
    } else {
      section.innerHTML = `
        <div class="glass-card" style="text-align:center; padding:1.5rem;">
          <p style="color:var(--text-muted);">No leaderboard data yet. Start earning XP!</p>
        </div>
      `;
    }
  } catch (err) {
    section.innerHTML = `<p style="color:var(--text-muted);">Failed to load leaderboard.</p>`;
  }
}

// ─────────────────────────────────────────────────────────────────
//  NOTIFICATIONS / TOASTS
// ─────────────────────────────────────────────────────────────────
function showXPToast(xp, customMessage) {
  if (!xp && !customMessage) return;

  const toast = document.createElement("div");
  toast.className = "xp-toast";
  toast.textContent = customMessage || `+${xp} XP Earned! ⚡`;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 3200);
}

function showAchievementToast(achievement) {
  if (!achievement) return;

  const toast = document.createElement("div");
  toast.className = "achievement-toast";
  toast.innerHTML = `
    <div class="ach-icon">${achievement.icon}</div>
    <div class="ach-title">🏆 ${achievement.name} Unlocked!</div>
    <div class="ach-desc">${achievement.desc}</div>
  `;
  document.body.appendChild(toast);

  setTimeout(() => toast.remove(), 4200);
}
