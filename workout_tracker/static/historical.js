// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// Local 24-hour picker and gentle blur/submit normalization. Server revalidates
// every value. No normalization occurs while typing, so cursor position is stable.
"use strict";
document.querySelectorAll('[data-clock-control]').forEach(control => {
  const input=control.querySelector('[data-clock-input]'), picker=control.querySelector('[data-clock-picker]'),
    open=control.querySelector('[data-clock-open]'), hour=control.querySelector('[data-clock-hour]'), minute=control.querySelector('[data-clock-minute]');
  // Turn four digits into a clock only after editing; never move the typing cursor.
  const normalize=()=>{if (/^\d{4}$/.test(input.value)) input.value=input.value.slice(0,2)+':'+input.value.slice(2);};
  // Close the local chooser and keep its accessibility state in agreement.
  const close=()=>{picker.hidden=true;open.setAttribute('aria-expanded','false');};
  input.addEventListener('blur',normalize);input.form.addEventListener('submit',normalize);
  open.addEventListener('click',()=>{
    normalize();picker.hidden=!picker.hidden;open.setAttribute('aria-expanded',String(!picker.hidden));
    if (!picker.hidden) {const parts=input.value.split(':');hour.value=parts[0]||'';minute.value=parts[1]||'';hour.focus();}
  });
  control.querySelector('[data-clock-apply]').addEventListener('click',()=>{
    if (hour.value===''||minute.value==='') return;
    input.value=hour.value+':'+minute.value;close();input.focus();
  });
  control.querySelector('[data-clock-clear]').addEventListener('click',()=>{input.value='';close();input.focus();});
  picker.addEventListener('keydown',event=>{if(event.key==='Escape'){close();open.focus();}});
});
const summary=document.querySelector('.error-summary');if(summary) summary.focus();
