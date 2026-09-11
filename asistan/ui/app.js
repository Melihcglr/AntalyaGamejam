const TOKEN_KEY = "jarvis_api_token";

const els = {
  name: document.getElementById("assistantName"),
  listen: document.getElementById("listenState"),
  brain: document.getElementById("brainState"),
  wake: document.getElementById("wakeState"),
  notes: document.getElementById("notesState"),
  mic: document.getElementById("micState"),
  form: document.getElementById("cmdForm"),
  input: document.getElementById("cmdInput"),
  reply: document.getElementById("reply"),
  warnings: document.getElementById("deviceWarnings"),
  log: document.getElementById("logList"),
  apiToken: document.getElementById("apiToken"),
  btnSaveToken: document.getElementById("btnSaveToken"),
  btnGenToken: document.getElementById("btnGenToken"),
  btnListen: document.getElementById("btnListen"),
  btnMute: document.getElementById("btnMute"),
  btnPtt: document.getElementById("btnPtt"),
  btnCamera: document.getElementById("btnCamera"),
  btnScreen: document.getElementById("btnScreen"),
  btnDescribe: document.getElementById("btnDescribe"),
  btnWake: document.getElementById("btnWake"),
  btnGame: document.getElementById("btnGame"),
  btnWork: document.getElementById("btnWork"),
  btnLightOff: document.getElementById("btnLightOff"),
  btnScan: document.getElementById("btnScan"),
  btnAdopt: document.getElementById("btnAdopt"),
};

let listening = false;
let requireWake = false;
let micMuted = false;
let pushToTalk = false;
let confirmToken = null;

if (els.apiToken) {
  els.apiToken.value = localStorage.getItem(TOKEN_KEY) || "";
}

function authHeaders() {
  const token = (els.apiToken && els.apiToken.value.trim()) || localStorage.getItem(TOKEN_KEY) || "";
  if (!token) return {};
  return {
    Authorization: `Bearer ${token}`,
    "X-Jarvis-Token": token,
  };
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
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
  micMuted = !!status.mic_muted;
  pushToTalk = !!status.push_to_talk;
  els.listen.textContent = listening ? "açık" : "kapalı";
  els.brain.textContent = status.brain_ready ? "API bağlı" : "çevrimdışı kurallar";
  els.wake.textContent = requireWake ? (status.wake_word || "zorunlu") : "serbest";
  els.notes.textContent = String(status.notes_count ?? 0);
  if (els.mic) {
    els.mic.textContent = micMuted ? "mute" : pushToTalk ? "PTT" : "hazır";
  }
  els.btnListen.textContent = listening ? "Dinlemeyi kapat" : "Dinlemeyi aç";
  els.btnListen.classList.toggle("active", listening);
  els.btnWake.textContent = requireWake ? "Wake: zorunlu" : "Wake: serbest";
  els.btnWake.classList.toggle("active", requireWake);
  if (els.btnMute) {
    els.btnMute.textContent = micMuted ? "Mikrofon aç" : "Mikrofon mute";
    els.btnMute.classList.toggle("active", micMuted);
  }
  if (els.btnPtt) {
    els.btnPtt.classList.toggle("active", pushToTalk);
    els.btnPtt.textContent = pushToTalk ? "PTT basılı tut" : "PTT (basılı tut)";
  }
  if (els.warnings) {
    const warns = status.device_warnings || [];
    els.warnings.textContent = warns.length ? warns.join(" · ") : "";
  }

  els.log.innerHTML = "";
  (status.log || []).slice().reverse().forEach((item) => {
    const li = document.createElement("li");
    const ts = document.createElement("span");
    ts.className = "ts";
    ts.textContent = item.ts || "";
    const kind = document.createElement("span");
    kind.className = "kind";
    kind.textContent = item.kind || "";
    const msg = document.createElement("span");
    msg.textContent = item.message || "";
    li.append(ts, kind, msg);
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

els.btnSaveToken?.addEventListener("click", () => {
  localStorage.setItem(TOKEN_KEY, els.apiToken.value.trim());
  els.reply.textContent = "Token kaydedildi (bu tarayıcı).";
});

els.btnGenToken?.addEventListener("click", async () => {
  try {
    const data = await api("/api/token/generate", { method: "POST", body: "{}" });
    els.apiToken.value = data.api_token || "";
    localStorage.setItem(TOKEN_KEY, els.apiToken.value);
    els.reply.textContent = "Yeni API token üretildi. ESP AUTH_TOKEN ile aynı yap.";
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

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

els.btnMute?.addEventListener("click", async () => {
  try {
    await api("/api/listen/mute", {
      method: "POST",
      body: JSON.stringify({ muted: !micMuted }),
    });
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
});

(function bindPtt() {
  if (!els.btnPtt) return;
  const down = async () => {
    try {
      if (!pushToTalk) {
        await api("/api/settings", {
          method: "PATCH",
          body: JSON.stringify({ push_to_talk: true }),
        });
        pushToTalk = true;
      }
      await api("/api/listen/ptt", { method: "POST", body: JSON.stringify({ active: true }) });
      els.btnPtt.classList.add("active");
    } catch (err) {
      els.reply.textContent = String(err.message || err);
    }
  };
  const up = async () => {
    try {
      await api("/api/listen/ptt", { method: "POST", body: JSON.stringify({ active: false }) });
      els.btnPtt.classList.remove("active");
    } catch (err) {
      els.reply.textContent = String(err.message || err);
    }
  };
  els.btnPtt.addEventListener("mousedown", down);
  els.btnPtt.addEventListener("mouseup", up);
  els.btnPtt.addEventListener("mouseleave", up);
  els.btnPtt.addEventListener("touchstart", (e) => {
    e.preventDefault();
    down();
  });
  els.btnPtt.addEventListener("touchend", (e) => {
    e.preventDefault();
    up();
  });
})();

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

async function runPhrase(text) {
  els.reply.textContent = "İşleniyor…";
  try {
    const result = await api("/api/command", { method: "POST", body: JSON.stringify({ text }) });
    els.reply.textContent = result.speech || result.result?.message || "Tamam.";
    await refresh();
  } catch (err) {
    els.reply.textContent = String(err.message || err);
  }
}

els.btnGame.addEventListener("click", () => runPhrase("oyun modu"));
els.btnWork.addEventListener("click", () => runPhrase("çalışma modu"));
els.btnLightOff.addEventListener("click", () => runPhrase("ışığı kapat"));
els.btnScan.addEventListener("click", () => runPhrase("ağı tara"));
els.btnAdopt.addEventListener("click", () => runPhrase("bulunan cihazları bağla"));

refresh();
setInterval(refresh, 4000);
