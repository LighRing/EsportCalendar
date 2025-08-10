// --- Config par défaut
const DEFAULT_BACKEND = "http://localhost:8080";

// --- Récupération des préférences (backend + clubs)
async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      {
        backendUrl: DEFAULT_BACKEND,
        clubs: [
          // Valeur par défaut : Team Vitality
          {
            name: "Team Vitality",
            primary: "#F8D000",
            secondary: "#1A1A1A",
            aliases: ["Vitality", "Team_Vitality"]
          }
        ]
      },
      (res) => resolve(res)
    );
  });
}

const clubEl = document.getElementById("club");
const listEl = document.getElementById("list");
const gameFilterEl = document.getElementById("gameFilter");
const refreshBtn = document.getElementById("refreshBtn");
const settingsLink = document.getElementById("settingsLink");

// ---------------- Helpers couleurs & clubs ----------------
const norm = (s) => (s || "").toLowerCase().trim();

function matchClubForName(name, clubs) {
  // reconnait le club même si le nom varie (Team Vitality vs Vitality)
  const n = norm(name);
  for (const c of clubs) {
    const main = norm(c.name);
    const aliases = (c.aliases || []).map(norm);

    // égalité stricte
    if (n === main || aliases.includes(n)) return c;

    // correspondance "contient" dans les deux sens
    if (n.includes(main) || main.includes(n)) return c;
    if (aliases.some(a => n.includes(a) || a.includes(n))) return c;
  }
  return null;
}

function involvedClubs(match, clubs) {
  const a = matchClubForName(match.team, clubs);
  const b = matchClubForName(match.opponent, clubs);
  if (a && b && norm(a.name) === norm(b.name)) return [a]; // sécurité
  return [a, b].filter(Boolean);
}

function cardStyleFor(clubsInvolved) {
  if (clubsInvolved.length === 2) {
  const [c1, c2] = clubsInvolved;
  const p1 = c1.primary || "#ddd";
  const p2 = c2.primary || "#eee";
  const leftName  = m.team || "?";
  const rightName = m.opponent || "TBA";

  const html = `
    <li class="card split">
      <div class="teams">
        <div class="team-half" style="background-color:${p1}">
          <div class="team-content">
            <div class="badge">${m.game || ""}</div>
            <div class="team-name">${leftName}</div>
          </div>
        </div>
        <div class="team-half" style="background-color:${p2}">
          <div class="team-content">
            <div class="badge">${m.game || ""}</div>
            <div class="team-name">${rightName}</div>
          </div>
        </div>
      </div>
      <div class="details">
        <div class="meta">${m.tournament || ""} ${m.stage ? " • " + m.stage : ""} ${m.bo ? " • " + m.bo : ""}</div>
        <div class="meta">${when}</div>
        <div class="streams">${streams.join(" ")}</div>
      </div>
    </li>`;
  listEl.insertAdjacentHTML("beforeend", html);

}
  if (clubsInvolved.length === 1) {
    const c = clubsInvolved[0];
    const p = c.primary || "#f7f7f7";
    // teinte douce (opacité) + bordure colorée
    return `background: ${p}1a; border: 1px solid ${p}66;`;
  }
  return ""; // neutre
}

// déduplication d’un match “miroir” (deux clubs suivis)
function canonicalKey(m) {
  const t1 = norm(m.team), t2 = norm(m.opponent);
  const duo = [t1, t2].sort().join("|");
  return [duo, norm(m.tournament), norm(m.start_time_utc || ""), norm(m.game || "")].join("#");
}

// ---------------- Rendu ----------------
function renderMatches(data, filter, clubs) {
  listEl.innerHTML = "";

  let items = (data.matches || []).filter(m => filter === "ALL" || m.game === filter);
  if ((clubs || []).length) {
    items = items.filter(m => involvedClubs(m, clubs).length >= 1);
  }

  // déduplication (match miroir)
  const seen = new Set();
  const deduped = [];
  for (const m of items) {
    const key = canonicalKey(m);
    if (!seen.has(key)) { seen.add(key); deduped.push(m); }
  }

  if (!deduped.length) {
    listEl.innerHTML = `<li class="empty">Aucun match trouvé.</li>`;
    return;
  }

  for (const m of deduped) {
    const when = m.start_time_utc ? new Date(m.start_time_utc).toLocaleString() : "TBA";
    const streams = [];
    (m.streams?.twitch || []).forEach(u => streams.push(`<a href="${u}" target="_blank">Twitch</a>`));
    (m.streams?.youtube || []).forEach(u => streams.push(`<a href="${u}" target="_blank">YouTube</a>`));

    const clubsInvolved = involvedClubs(m, clubs);
    // couleurs
    let className = "card";
    let style = "";
    if (clubsInvolved.length === 2) {
      className += " split";
      style = `--c1:${clubsInvolved[0].primary || "#ddd"}; --c2:${clubsInvolved[1].primary || "#eee"};`;
    } else if (clubsInvolved.length === 1) {
      className += " tinted";
      style = `--c1:${clubsInvolved[0].primary || "#f7f7f7"};`;
    }

    // noms à gauche/droite si split
    const leftName  = clubsInvolved.length === 2 ? (m.team || "?")     : `${m.team || "?"} vs ${m.opponent || "TBA"}`;
    const rightName = clubsInvolved.length === 2 ? (m.opponent || "TBA"): "";

    const teamsHtml = (clubsInvolved.length === 2)
  ? `<div class="teams"><span class="left">${leftName}</span><span class="right">${rightName}</span></div>`
  : `<div class="teams">${leftName}</div>`;

    // 👉 si split: badge au-dessus ; sinon: à droite (comme avant)
    const rowContent = (clubsInvolved.length === 2)
        ? `<div class="badge">${m.game || ""}</div>${teamsHtml}`
        : `${teamsHtml}<div class="badge">${m.game || ""}</div>`;

    const html = `
        <li class="${className}" style="${style}">
            <div class="veil"></div>
            <div class="inner">
            <div class="row">
                ${rowContent}
            </div>
                <div class="meta">${m.tournament || ""} ${m.stage ? " • " + m.stage : ""} ${m.bo ? " • " + m.bo : ""}</div>
                <div class="meta">${when}</div>
                <div class="streams">${streams.join(" ")}</div>
            </div>
      </li>`;
    listEl.insertAdjacentHTML("beforeend", html);
  }
}

// ---------------- Cycle de vie ----------------
async function loadAndRender() {
  try {
    const { backendUrl, clubs } = await getSettings();
    const res = await fetch(`${backendUrl}/api/schedule`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const updated = data.updated_at ? new Date(data.updated_at).toLocaleString() : "";
    clubEl.textContent = `${data.club || ""} • maj ${updated}`;
    renderMatches(data, gameFilterEl.value, clubs);
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
