const DEFAULT_BACKEND = "http://localhost:8080";
const input = document.getElementById("backendUrl");
const btn = document.getElementById("saveBtn");

chrome.storage.sync.get({ backendUrl: DEFAULT_BACKEND }, (res) => {
  input.value = res.backendUrl || DEFAULT_BACKEND;
});

btn.addEventListener("click", () => {
  const url = input.value.trim() || DEFAULT_BACKEND;
  chrome.storage.sync.set({ backendUrl: url }, () => {
    btn.textContent = "Enregistré ✓";
    setTimeout(() => (btn.textContent = "Enregistrer"), 1200);
  });
});
