"use strict";

let currentId = null;
let pollTimer = null;
let reportGenerated = false;

const $ = (sel) => document.querySelector(sel);

const dropzone = $("#dropzone");
const fileInput = $("#fileInput");
const reel = $("#reel");
const progressWrap = $("#progressWrap");
const progressFill = $("#progressFill");
const progressText = $("#progressText");
const uploadError = $("#uploadError");
const currentInfo = $("#currentInfo");
const currentIdEl = $("#currentId");
const currentStatusEl = $("#currentStatus");

const STATUS_TEXT = { done: "完成", processing: "转写中", failed: "失败" };

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) handleFile(fileInput.files[0]);
});

$("#refreshBtn").addEventListener("click", loadHistory);
loadHistory();

async function loadHistory() {
  const resp = await fetch("/api/sessions");
  const sessions = await resp.json();
  const ul = $("#historyList");
  ul.innerHTML = "";
  if (!sessions.length) {
    ul.innerHTML = '<li class="history-empty">暂无记录, 先上传一个音频吧。</li>';
    return;
  }
  sessions.forEach((s) => {
    const li = document.createElement("li");
    li.className = "history-item";
    li.dataset.id = s.id;
    if (s.id === currentId) li.classList.add("active");

    const top = document.createElement("div");
    top.className = "h-item-top";
    const name = document.createElement("span");
    name.className = "h-name";
    name.textContent = s.name || s.filename;
    const st = document.createElement("span");
    st.className = "h-status " + s.status;
    st.innerHTML = `<i></i>${STATUS_TEXT[s.status] || s.status}`;
    top.append(name, st);

    const meta = document.createElement("div");
    meta.className = "h-meta";
    meta.textContent =
      `${s.created_at.slice(0, 16)} · ${s.filename}` +
      (s.duration_sec != null ? ` · 耗时 ${s.duration_sec}s` : "");

    const actions = document.createElement("div");
    actions.className = "h-actions";
    const btnRename = document.createElement("button");
    btnRename.className = "btn ghost sm";
    btnRename.textContent = "改名";
    const btnOpen = document.createElement("button");
    btnOpen.className = "btn primary sm";
    btnOpen.textContent = "打开";
    btnRename.addEventListener("click", () => renameSession(s));
    btnOpen.addEventListener("click", () => openSession(s.id));
    actions.append(btnRename, btnOpen);

    li.append(top, meta, actions);
    ul.appendChild(li);
  });
}

async function renameSession(session) {
  const newName = prompt("输入新的名称:", session.name || session.filename);
  if (!newName || newName === (session.name || session.filename)) return;
  const resp = await fetch(`/api/audio/${session.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: newName }),
  });
  if (!resp.ok) {
    alert("改名失败: " + ((await resp.json()).detail || "未知错误"));
    return;
  }
  loadHistory();
}

async function openSession(id) {
  stopPolling();
  currentId = id;
  reportGenerated = false;
  currentInfo.classList.remove("hidden");
  currentIdEl.textContent = id;
  $("#transcriptView").textContent = "";
  $("#reportView").textContent = "";
  $("#dlTranscript").classList.add("hidden");
  $("#dlReport").classList.add("hidden");
  showTranscriptTab();
  loadHistory();
  await loadCurrent();
}

async function loadCurrent() {
  if (!currentId) return;
  const resp = await fetch(`/api/audio/${currentId}`);
  const data = await resp.json();
  if (data.status === "processing") {
    currentStatusEl.textContent = "转写中...";
    showContent();
    startPolling();
    return;
  }
  if (data.status === "failed") {
    currentStatusEl.textContent = "失败";
    uploadError.textContent = "转写失败: " + (data.error || "未知错误");
    uploadError.classList.remove("hidden");
    return;
  }
  currentStatusEl.textContent =
    data.duration_sec != null ? `完成 (转写耗时 ${data.duration_sec}s)` : "完成";
  $("#transcriptView").textContent = data.transcript || "(无内容)";
  $("#dlTranscript").classList.remove("hidden");
  $("#dlTranscript").href = `/api/audio/${currentId}/transcript/download`;
  showContent();
  showTranscriptTab();
  loadHistory();
  const historyResp = await fetch(`/api/audio/${currentId}/chat`);
  const history = await historyResp.json();
  renderHistory(history);
}

function renderHistory(history) {
  const box = $("#chatBox");
  box.innerHTML = "";
  if (!history.length) {
    box.innerHTML = '<p class="chat-placeholder">音频转写完成后, 在这里提问。</p>';
    return;
  }
  history.forEach((m) => {
    const div = document.createElement("div");
    div.className = "msg " + m.role;
    div.textContent = m.content;
    box.appendChild(div);
  });
  box.scrollTop = box.scrollHeight;
}

async function handleFile(file) {
  stopPolling();
  uploadError.classList.add("hidden");
  const fd = new FormData();
  fd.append("file", file);
  progressWrap.classList.remove("hidden");
  reel.classList.add("spin");
  setProgress(0);
  try {
    const resp = await fetch("/api/audio", { method: "POST", body: fd });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "上传失败");
    currentId = data.id;
    reportGenerated = false;
    currentInfo.classList.remove("hidden");
    currentIdEl.textContent = currentId;
    currentStatusEl.textContent = "转写中...";
    resetContent();
    loadHistory();
    startPolling();
  } catch (err) {
    progressWrap.classList.add("hidden");
    reel.classList.remove("spin");
    uploadError.textContent = "上传失败: " + err.message;
    uploadError.classList.remove("hidden");
  }
}

function setProgress(pct) {
  const p = Math.round(pct * 100);
  progressFill.style.width = p + "%";
  progressText.textContent = p + "%";
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(pollStatus, 1500);
  pollStatus();
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function pollStatus() {
  if (!currentId) return;
  const resp = await fetch(`/api/audio/${currentId}`);
  const data = await resp.json();
  setProgress(data.progress);
  if (data.status === "processing") {
    currentStatusEl.textContent = "转写中...";
    return;
  }
  stopPolling();
  progressWrap.classList.add("hidden");
  reel.classList.remove("spin");
  if (data.status === "failed") {
    currentStatusEl.textContent = "失败";
    uploadError.textContent = "转写失败: " + (data.error || "未知错误");
    uploadError.classList.remove("hidden");
    return;
  }
  currentStatusEl.textContent =
    data.duration_sec != null ? `完成 (转写耗时 ${data.duration_sec}s)` : "完成";
  $("#transcriptView").textContent = data.transcript || "(无内容)";
  $("#dlTranscript").classList.remove("hidden");
  $("#dlTranscript").href = `/api/audio/${currentId}/transcript/download`;
  showContent();
  loadHistory();
}

function resetContent() {
  $("#transcriptView").textContent = "";
  $("#reportView").textContent = "";
  $("#dlTranscript").classList.add("hidden");
  $("#dlReport").classList.add("hidden");
  $("#genReportBtn").disabled = false;
  showTranscriptTab();
}

function showContent() {
  $("#contentPanel").classList.remove("hidden");
  $("#chatPanel").classList.remove("hidden");
}

function showTranscriptTab() {
  $("#transcriptView").classList.remove("hidden");
  $("#reportView").classList.add("hidden");
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.tab === "transcript"));
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;
    $("#transcriptView").classList.toggle("hidden", target !== "transcript");
    $("#reportView").classList.toggle("hidden", target !== "report");
    document.querySelectorAll(".tab").forEach((t) =>
      t.classList.toggle("active", t.dataset.tab === target));
    if (target === "report" && !reportGenerated) tryFetchReport();
  });
});

$("#genReportBtn").addEventListener("click", async () => {
  if (!currentId) return;
  const btn = $("#genReportBtn");
  btn.disabled = true;
  btn.textContent = "生成中...";
  try {
    await fetch(`/api/audio/${currentId}/report`, { method: "POST" });
  } finally {
    btn.textContent = "生成总结报告";
  }
  pollReport();
});

async function pollReport() {
  if (!currentId) return;
  for (let i = 0; i < 120; i++) {
    const ok = await tryFetchReport();
    if (ok) return;
    await new Promise((r) => setTimeout(r, 2000));
  }
}

async function tryFetchReport() {
  if (!currentId) return false;
  const resp = await fetch(`/api/audio/${currentId}/report`);
  const data = await resp.json();
  if (data.report) {
    $("#reportView").textContent = data.report;
    $("#dlReport").classList.remove("hidden");
    $("#dlReport").href = `/api/audio/${currentId}/report/download`;
    reportGenerated = true;
    return true;
  }
  return false;
}

$("#chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = $("#chatInput").value.trim();
  if (!question || !currentId) return;
  appendMsg("user", question);
  $("#chatInput").value = "";
  const resp = await fetch(`/api/audio/${currentId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const data = await resp.json();
  if (data.error) {
    appendMsg("assistant", "错误: " + data.error);
  } else {
    appendMsg("assistant", data.answer);
  }
  $("#chatBox").scrollTop = $("#chatBox").scrollHeight;
});

function appendMsg(role, text) {
  const box = $("#chatBox");
  const ph = box.querySelector(".chat-placeholder");
  if (ph) ph.remove();
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}
