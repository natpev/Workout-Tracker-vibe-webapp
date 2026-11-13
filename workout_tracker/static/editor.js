// SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
// Management templates load this local file. It switches visible target fields
// and disables irrelevant inputs; Flask independently validates every POST.
"use strict";
document.querySelectorAll("[data-configuration]").forEach((form) => {
  if(form.querySelector('[name=capabilities_form]')) {
    const update=()=>{
      const selected=[...form.querySelectorAll('[data-capability]:checked')].map(input=>input.dataset.capability);
      form.querySelectorAll('[data-capability-fields]').forEach(group=>{
        const enabled=selected.includes(group.dataset.capabilityFields);
        group.hidden=!enabled;
        group.querySelectorAll('input,select').forEach(input=>{
          input.disabled=!enabled;
          input.required=enabled&&['target_reps','weight_basis'].includes(input.name);
        });
      });
    };
    form.querySelectorAll('[data-capability]').forEach(input=>input.addEventListener('change',update));
    update();return;
  }
  // Apply only the chosen mode's constraints; radio inputs retain native arrow
  // key behavior and checked state for assistive technology.
  const update = () => {
    const choice = form.querySelector("[name=measurement_type]:checked").value;
    form.querySelectorAll("[data-fields]").forEach((group) => {
      const active = group.dataset.fields.split(" ").includes(choice);
      group.hidden = !active;
      group.querySelectorAll("input,select").forEach((input) => {
        input.disabled = !active;
        input.required = active && ["target_reps", "unit", "weight_basis"].includes(input.name);
      });
    });
  };
  form.querySelectorAll("[name=measurement_type]").forEach((radio) => radio.addEventListener("change", update));
  update();
});
