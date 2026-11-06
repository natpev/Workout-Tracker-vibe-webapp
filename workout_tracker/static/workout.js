// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// Loaded only by workout/discard templates. Browser input -> revision-checked
// Flask POST -> SQLite commit -> acknowledged Saved/progress. Input remains in
// the page on failure; no previous performance is ever copied into a field.
"use strict";
(() => {
  const dialog = document.getElementById("discard-dialog");
  if (dialog) {
    // Explicit acknowledgment gates OK; Cancel and Escape never submit discard.
    const ack = document.getElementById("discard-ack");
    const ok = document.getElementById("discard-ok");
    ack.addEventListener("change", () => { ok.disabled = !ack.checked; });
    dialog.removeAttribute("open");
    dialog.showModal();
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      window.location.assign(document.getElementById("discard-cancel").href);
    });
    return;
  }
  const form = document.getElementById("workout-form");
  if (!form) return;
  const status = document.getElementById("save-status");
  const revision = form.elements.namedItem("revision");
  const cursor = form.elements.namedItem("current_position");
  let dirty = false, sequence = 0, timer, pending = null, draining = null, conflict = false, submitting = false, allowSubmit = false;

  const flush = (position = null) => {
    // Serialize fetches; edits typed while awaiting a response are saved next.
    // Never replace newer local text with a normalized response for older text.
    clearTimeout(timer);
    if (position !== null && cursor.value !== String(position)) {
      cursor.value = String(position);
      dirty = true;
      sequence += 1;
    }
    if (conflict) return Promise.resolve(false);
    if (draining) return draining;
    // All callers share one draining promise. Debounce, navigation and Finish
    // cannot accidentally issue concurrent requests with the same revision.
    draining = (async () => {
    while (dirty) {
      const sentSequence = sequence;
      const body = new URLSearchParams(new FormData(form));
      status.textContent = "Saving…";
      pending = (async () => {
        try {
          const response = await fetch(form.dataset.autosave, {
            method: "POST", body, credentials: "same-origin", headers: {"Accept": "application/json"}
          });
          const data = await response.json().catch(() => ({}));
          if (!response.ok) {
            if (response.status === 409) conflict = true;
            throw new Error(data.error || `Save failed (${response.status}). Reload if your session expired.`);
          }
          if (!Number.isSafeInteger(data.revision) || !Number.isSafeInteger(data.completed) ||
              !Number.isSafeInteger(data.total) || data.completed < 0 || data.completed > data.total ||
              typeof data.updated_at !== "string") throw new Error("Invalid server acknowledgment.");
          revision.value = String(data.revision);
          document.querySelectorAll("[data-entry-state]").forEach((element) => {
            if (element.dataset.entryState === data.entry_id) element.textContent = data.measurement_display;
          });
          document.getElementById("workout-progress").value = data.completed;
          document.getElementById("progress-text").textContent = `${data.completed} / ${data.total} done`;
          if (data.completed !== 0) document.getElementById("all-skipped-confirmation").hidden = true;
          document.getElementById("confirmed-at").textContent = data.updated_at;
          if (sequence === sentSequence) {
            for (const name of ["weight", "minutes", "seconds"]) {
              const input = form.elements.namedItem(name);
              if (input) input.value = data[name];
            }
            form.elements.namedItem("increase").checked = data.increase;
            dirty = false;
            status.textContent = "✓ Saved";
            status.dataset.state = "saved";
            document.getElementById("save-error").hidden = true;
          } else {
            status.textContent = "Saving newer changes…";
          }
          return true;
        } catch (error) {
          status.textContent = "Save failed";
          status.dataset.state = "error";
          const detail = document.getElementById("save-error");
          detail.hidden = false;
          detail.textContent = `Not saved: ${error.message} Your input is still visible; earlier confirmed saves are retained. Stay here and retry Save draft, or reload after copying unsaved input.`;
          return false;
        }
      })();
      const saved = await pending;
      pending = null;
      if (!saved) return false;
    }
    return true;
    })().finally(() => { draining = null; });
    return draining;
  };

  form.querySelectorAll("[name=weight],[name=minutes],[name=seconds],[name=increase]").forEach((input) => {
    input.addEventListener("input", () => {
      // Mark unsaved immediately, not only once the debounce request begins.
      dirty = true;
      sequence += 1;
      status.textContent = conflict ? "Save failed" : "Unsaved";
      clearTimeout(timer);
      timer = setTimeout(() => { void flush(); }, 300);
    });
  });
  form.addEventListener("submit", async (event) => {
    if (allowSubmit) return;
    event.preventDefault();
    const submitter = event.submitter;
    if (submitting) return;
    submitting = true;
    // Persist pending changes before the normal atomic save/finish POST. The
    // server revalidates its revision and includes any final form input as well.
    if (await flush()) {
      allowSubmit = true;
      // Even an already-resolved flush must leave the native submit dispatch
      // before requesting submission again; browsers ignore reentrant submits.
      setTimeout(() => {
        if (submitter) form.requestSubmit(submitter);
        else form.requestSubmit();
      }, 0);
    } else {
      submitting = false;
    }
  });
  document.querySelectorAll("[data-workout-nav],[data-workout-leave]").forEach((link) => {
    link.addEventListener("click", async (event) => {
      event.preventDefault();
      if (submitting) return;
      submitting = true;
      if (await flush(link.dataset.position)) window.location.assign(link.href);
      else submitting = false;
    });
  });
  const jump = document.getElementById("exercise-jump");
  jump.addEventListener("change", async () => {
    if (submitting) return;
    submitting = true;
    if (await flush(jump.value)) window.location.assign(jump.selectedOptions[0].dataset.url);
    else submitting = false;
  });
  window.addEventListener("beforeunload", (event) => {
    // Closing a browser cannot guarantee an in-flight request reached SQLite.
    // Warn on unsaved input; never label it Saved before acknowledgment.
    if (dirty || pending) { event.preventDefault(); event.returnValue = ""; }
  });
})();
