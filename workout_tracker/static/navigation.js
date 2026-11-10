// SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
// Local disclosure menus and tab-scoped workout focus. No account authentication.
// A focus marker redirects navigation back to its draft until explicit exit or
// completion. SQLite draft/revision validation remains the source of truth.
"use strict";
(() => {
  const buttons = [...document.querySelectorAll("[data-menu-button]")];
  const close = (button, restore = false) => {
    // Close one disclosure; Escape returns keyboard focus to its trigger.
    document.getElementById(button.getAttribute("aria-controls")).hidden = true;
    button.setAttribute("aria-expanded", "false");
    if (restore) button.focus();
  };
  buttons.forEach((button) => {
    const panel = document.getElementById(button.getAttribute("aria-controls"));
    button.addEventListener("click", () => {
      const opening = panel.hidden;
      buttons.forEach((other) => close(other));
      panel.hidden = !opening;
      button.setAttribute("aria-expanded", String(opening));
      // A bottom-of-page Library row may need a small vertical scroll so both
      // actions are reachable. CSS alone controls width and name truncation.
      if (opening && panel.classList.contains("library-menu")) panel.scrollIntoView({block:"nearest",inline:"nearest"});
    });
    button.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") { event.preventDefault(); if (panel.hidden) button.click(); panel.querySelector("a,input,button")?.focus(); }
    });
    panel.addEventListener("keydown", (event) => { if (event.key === "Escape") close(button, true); });
  });
  document.addEventListener("click", (event) => {
    buttons.forEach((button) => { if (!button.parentElement.contains(event.target)) close(button); });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") buttons.forEach((button) => { if (button.getAttribute("aria-expanded") === "true") close(button, true); });
  });
  document.addEventListener("focusin", (event) => {
    buttons.forEach((button) => { if (!button.parentElement.contains(event.target)) close(button); });
  });
  // sessionStorage belongs to this tab, so another browser/session can work out
  // independently. Failure to access it never claims drafts were discarded.
  try {
    const body = document.body, key = "workout-focus";
    const previous = JSON.parse(sessionStorage.getItem(key) || "null");
    const exited = new URLSearchParams(location.search).get("exited");
    if (previous && (body.dataset.releaseWorkout === previous.id || exited === previous.id)) {
      sessionStorage.removeItem(key);
    } else if (body.dataset.workoutFocus) {
      sessionStorage.setItem(key, JSON.stringify({id:body.dataset.workoutFocus, url:location.pathname+location.search}));
    } else if (previous && !location.pathname.includes(`/workouts/${previous.id}`)) {
      // Native Back can land on a management screen. Return to the draft rather
      // than offering unrestricted switching; Exit Workout explicitly releases it.
      fetch(previous.url, {credentials:"same-origin"}).then((response) => {
        if (response.status === 404) sessionStorage.removeItem(key);
        else if (response.ok) location.replace(previous.url);
      }).catch(() => { /* No network: beforeunload/input warning remains authoritative. */ });
    }
  } catch { /* Workflow assistance is best effort; no shared authentication state. */ }
  window.addEventListener("pageshow", (event) => {
    // Reload a back/forward cache page to show current server revisions/values.
    if (event.persisted) location.reload();
  });
})();
