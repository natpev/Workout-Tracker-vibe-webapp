// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// A confirmed Install submit synchronously opens one trusted status tab, then
// uses CSRF-protected fetch so the original application tab stays available.
"use strict";
document.querySelectorAll('[data-update-install]').forEach(form=>{
  let submitting=false;
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(submitting||!form.reportValidity())return;
    const target=new URL(form.dataset.statusUrl,location.href);
    if(target.protocol!=='http:'||target.username||target.password)return;
    submitting=true;
    const button=form.querySelector('button'),note=document.getElementById('update-submit-status');
    const child=window.open('about:blank','_blank');
    if(child){child.opener=null;child.location.replace(target.href);}
    else document.getElementById('popup-fallback').hidden=false;
    button.disabled=true;
    const body=new FormData(form);body.set('action','install');
    try{
      const response=await fetch(location.href,{method:'POST',body,credentials:'same-origin',headers:{Accept:'application/json'}});
      const result=await response.json();
      if(!response.ok)throw new Error(result.error||'Update was not accepted. Review its status before retrying.');
      note.textContent='Update accepted. Follow the independent progress tab; the application may temporarily stop.';
    }catch{
      note.textContent='Check independent update progress before retrying. The application may be restarting or the request may not have been accepted.';
      document.getElementById('popup-fallback').hidden=false;
    }
  });
});
