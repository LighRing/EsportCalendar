const DEFAULT_BACKEND = "http://localhost:8080";

// 👇 Définition des clubs par défaut (persistés si storage vide)
const DEFAULT_CLUBS = [
  { name: "Team Vitality", primary: "#F8D000", secondary: "#1A1A1A", aliases: ["Vitality","Team_Vitality"] }
];

const backendInput = document.getElementById("backendUrl");
const saveBackendBtn = document.getElementById("saveBackend");

const clubName = document.getElementById("clubName");
const primaryColor = document.getElementById("primaryColor");
const secondaryColor = document.getElementById("secondaryColor");
const aliasesInput = document.getElementById("aliases");
const addBtn = document.getElementById("addClub");
const clubList = document.getElementById("clubList");

// --- Charge l'état et initialise si vide
function loadState() {
  chrome.storage.sync.get(
    { backendUrl: DEFAULT_BACKEND, clubs: null },
    (res) => {
      // init clubs si vide/non défini
      let clubs = res.clubs;
      if (!Array.isArray(clubs) || clubs.length === 0) {
        clubs = [...DEFAULT_CLUBS];
        chrome.storage.sync.set({ clubs }); // 🔒 on persiste les défauts une bonne fois
      }
      backendInput.value = res.backendUrl || DEFAULT_BACKEND;
      renderClubs(clubs);
    }
  );
}

function renderClubs(clubs) {
  clubList.innerHTML = "";
  if (!clubs.length) {
    clubList.innerHTML = `<div class="item">Aucun club suivi pour l’instant.</div>`;
    return;
  }
  clubs.forEach((c, idx) => {
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `
      <div class="row">
        <input type="text" value="${c.name}" data-k="name" />
        <input type="color" value="${c.primary || "#cccccc"}" data-k="primary" />
        <input type="color" value="${c.secondary || "#000000"}" data-k="secondary" />
        <input type="text" value="${(c.aliases || []).join(", ")}" data-k="aliases" />
        <button data-act="del">Suppr</button>
      </div>
    `;
    // supprimer
    item.querySelector('[data-act="del"]').addEventListener("click", () => {
      clubs.splice(idx, 1);
      chrome.storage.sync.set({ clubs }, () => renderClubs(clubs));
    });
    // éditer champs
    item.querySelectorAll("input").forEach((inp) => {
      inp.addEventListener("change", () => {
        const k = inp.dataset.k;
        if (k === "aliases") {
          clubs[idx][k] = inp.value.split(",").map(s => s.trim()).filter(Boolean);
        } else {
          clubs[idx][k] = inp.value;
        }
        chrome.storage.sync.set({ clubs });
      });
    });
    clubList.appendChild(item);
  });
}

// --- Enregistrer l’URL backend (sans toucher aux clubs)
saveBackendBtn.addEventListener("click", () => {
  const url = backendInput.value.trim() || DEFAULT_BACKEND;
  chrome.storage.sync.set({ backendUrl: url }, () => {
    saveBackendBtn.textContent = "Enregistré ✓";
    setTimeout(() => (saveBackendBtn.textContent = "Enregistrer"), 1200);
  });
});

// --- Ajouter un club (on conserve l'existant)
addBtn.addEventListener("click", () => {
  const name = clubName.value.trim();
  if (!name) return;
  const club = {
    name,
    primary: primaryColor.value || "#cccccc",
    secondary: secondaryColor.value || "#000000",
    aliases: aliasesInput.value.split(",").map(s => s.trim()).filter(Boolean)
  };
  chrome.storage.sync.get({ clubs: [] }, (res) => {
    const clubs = Array.isArray(res.clubs) ? res.clubs : [];
    clubs.push(club);
    chrome.storage.sync.set({ clubs }, () => {
      clubName.value = "";
      aliasesInput.value = "";
      renderClubs(clubs);
    });
  });
});

loadState();
