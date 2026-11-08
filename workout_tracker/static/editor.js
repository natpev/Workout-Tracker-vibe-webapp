// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// Management templates load this local file. It switches visible target fields
// and disables irrelevant inputs; Flask independently validates every POST.
"use strict";
document.querySelectorAll("[data-configuration]").forEach((form) => {
  // Apply only the chosen mode's constraints; radio inputs retain native arrow
  // key behavior and checked state for assistive technology.
  const update = () => {
    const choice = form.querySelector("[name=measurement_type]:checked").value;
    form.querySelectorAll("[data-fields]").forEach((group) => {
      const active = group.dataset.fields === choice;
      group.hidden = !active;
      group.querySelectorAll("input,select").forEach((input) => {
        input.disabled = !active;
        input.required = active && ["target_reps", "unit"].includes(input.name);
      });
    });
  };
  form.querySelectorAll("[name=measurement_type]").forEach((radio) => radio.addEventListener("change", update));
  update();
});
