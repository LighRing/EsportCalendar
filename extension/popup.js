// Backend par défaut — tu peux le changer dans les paramètres (options.html)
const DEFAULT_BACKEND = "http://localhost:8080";

const clubEl = document.getElementById("club");
const listEl = document.getElementById("list");
const gameFilterEl = document.getElementById("gameFilter");
const refreshBtn = document.getElementById("refreshBtn");
const settingsLink = document.getElementById("settingsLink");

async function getBackendURL() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ backendUrl: DEFAULT_BACKEND }, (res) => {
      resolve(res.backendUrl || DEFAULT_BACKEND);
    });
  });
}

function renderMatches(data, filter) {
  listEl.innerHTML = "";
  const items = (data.matches || []).filter(m => filter === "ALL" || m.game === filter);
  if (!items.length) {
    listEl.innerHTML = `<li class="empty">Aucun match trouvé.</li>`;
    return;
  }
  for (const m of items) {
    const when = m.start_time_utc ? new Date(m.start_time_utc).toLocaleString() : "TBA";
    const streams = [];
    (m.streams?.twitch || []).forEach(u => streams.push(`<a href="${u}" target="_blank">Twitch</a>`));
    (m.streams?.youtube || []).forEach(u => streams.push(`<a href="${u}" target="_blank">YouTube</a>`));

    const html = `
      <li class="card">
        <div class="top">
          <div class="teams">${m.team || "?"} vs ${m.opponent || "TBA"}</div>
          <div class="meta">${m.game || ""}</div>
        </div>
        <div class="meta">${m.tournament || ""} ${m.stage ? " • " + m.stage : ""} ${m.bo ? " • " + m.bo : ""}</div>
        <div class="meta">${when}</div>
        <div class="streams">${streams.join(" ")}</div>
      </li>`;
    listEl.insertAdjacentHTML("beforeend", html);
  }
}

async function loadAndRender() {
  try {
    const backend = await getBackendURL();
    const res = await fetch(`${backend}/api/schedule`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const updated = data.updated_at ? new Date(data.updated_at).toLocaleString() : "";
    clubEl.textContent = `${data.club || ""} • maj ${updated}`;
    renderMatches(data, gameFilterEl.value);
  } catch (e) {
    listEl.innerHTML = `<li class="empty">Erreur de chargement : ${e.message}</li>`;
  }
}

refreshBtn.addEventListener("click", loadAndRender);
gameFilterEl.addEventListener("change", loadAndRender);
settingsLink.addEventListener("click", async (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});

loadAndRender();
