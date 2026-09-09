const els = {
  name: document.getElementById("assistantName"),
  listen: document.getElementById("listenState"),
  brain: document.getElementById("brainState"),
  wake: document.getElementById("wakeState"),
  notes: document.getElementById("notesState"),
  form: document.getElementById("cmdForm"),
  input: document.getElementById("cmdInput"),
  reply: document.getElementById("reply"),
  log: document.getElementById("logList"),
  btnListen: document.getElementById("btnListen"),
  btnCamera: document.getElementById("btnCamera"),
  btnScreen: document.getElementById("btnScreen"),
  btnDescribe: document.getElementById("btnDescribe"),
  btnWake: document.getElementById("btnWake"),
};

let listening = false;
let requireWake = false;
let confirmToken = null;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    throw new Error(typeof detail === "string" ? detail : res.statusText || "İstek başarısız");
  }
  return data;
}

function renderStatus(status) {
  els.name.textContent = (status.name || "JARVIS").toUpperCase();
  listening = !!status.listening;
  requireWake = !!status.require_wake_word;
  els.listen.textContent = listening ? "açık" : "kapalı";
  els.brain.textContent = status.brain_ready ? "API bağlı" : "çevrimdışı kurallar";
  els.wake.textContent = requireWake ? (status.wake_word || "zorunlu") : "serbest";
  els.notes.textContent = String(status.notes_count ?? 0);
  els.btnListen.textContent = listening ? "Dinlemeyi kapat" : "Dinlemeyi aç";
  els.btnListen.classList.toggle("active", listening);
  els.btnWake.textContent = requireWake ? "Wake: zorunlu" : "Wake: serbest";
  els.btnWake.classList.toggle("active", requireWake);

  els.log.innerHTML = "";
  (status.log || []).slice().reverse().forEach((item) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="ts">${item.ts || ""}</span><span class="kind">${item.kind || ""}</span><span>${item.message || ""}</span>`;
    els.log.appendChild(li);
  });
}

async function refresh() {
  try {
    const status = await api("/api/status");
    renderStatus(status);
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
}

els.form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = els.input.value.trim();
  if (!text) return;
  els.reply.textContent = "İşleniyor…";
  try {
    const body = { text };
    if (confirmToken) body.confirm_token = confirmToken;
    const result = await api("/api/command", { method: "POST", body: JSON.stringify(body) });
    els.reply.textContent = result.speech || result.result?.message || "Tamam.";
    if (result.result?.needs_confirm) {
      confirmToken = result.result.confirm_token;
      els.reply.textContent += ` Onay için aynı komutu tekrar gönder (token: ${confirmToken}).`;
    } else {
      confirmToken = null;
    }
    els.input.value = "";
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

els.btnListen.addEventListener("click", async () => {
  try {
    if (listening) {
      await api("/api/listen/stop", { method: "POST", body: "{}" });
    } else {
      await api("/api/listen/start", { method: "POST", body: "{}" });
    }
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

els.btnCamera.addEventListener("click", async () => {
  els.reply.textContent = "Kamera…";
  try {
    const result = await api("/api/camera", { method: "POST", body: "{}" });
    els.reply.textContent = result.result?.message || result.speech || "Tamam.";
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

els.btnScreen.addEventListener("click", async () => {
  els.reply.textContent = "Ekran…";
  try {
    const result = await api("/api/screen", { method: "POST", body: "{}" });
    els.reply.textContent = result.result?.message || result.speech || "Tamam.";
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

els.btnDescribe.addEventListener("click", async () => {
  els.reply.textContent = "Ekran inceleniyor…";
  try {
    const result = await api("/api/describe/screen", { method: "POST", body: "{}" });
    els.reply.textContent = result.speech || result.result?.message || "Tamam.";
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

els.btnWake.addEventListener("click", async () => {
  try {
    await api("/api/settings", {
      method: "PATCH",
      body: JSON.stringify({ require_wake_word: !requireWake }),
    });
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

refresh();
setInterval(refresh, 4000);
