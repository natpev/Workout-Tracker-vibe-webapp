// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// Loaded by home.html. Reads/writes only this browser's theme preference in
// localStorage; it sends no user data or network requests.
"use strict";
(() => {
  // Apply a saved browser preference; unavailable storage falls back to Auto.
  const selector = document.getElementById("theme");
  const status = document.getElementById("theme-status");
  const allowed = ["auto", "light", "dark"];
  let theme = "auto";
  try {
    const saved = localStorage.getItem("workout-theme");
    if (allowed.includes(saved)) theme = saved;
  } catch {
    status.textContent = "Theme preferences cannot be stored in this browser.";
  }
  document.documentElement.dataset.theme = theme;
  selector.value = theme;
  selector.addEventListener("change", () => {
    // Change appearance immediately; report if browser persistence is blocked.
    const choice = allowed.includes(selector.value) ? selector.value : "auto";
    document.documentElement.dataset.theme = choice;
    try {
      localStorage.setItem("workout-theme", choice);
      status.textContent = "Theme saved for this browser.";
    } catch {
      status.textContent = "Theme changed for this page; this browser could not save it.";
    }
  });
})();
