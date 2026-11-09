// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// Select/Clear only changes this form's export checkboxes. The server validates
// owned IDs/date ranges and creates the download; no data or date is changed here.
"use strict";
document.querySelectorAll('[data-csv-select]').forEach(button=>{
  button.addEventListener('click',()=>{
    button.form.querySelectorAll('[name="export_exercise"]').forEach(input=>{
      input.checked=button.dataset.csvSelect==='all';
    });
  });
});
