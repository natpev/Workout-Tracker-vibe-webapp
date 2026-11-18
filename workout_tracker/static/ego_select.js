// SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
// Fetch only the owned, server-rendered preview. Stale responses cannot replace a newer choice.
"use strict";
(() => {
 const select=document.getElementById('ego-exercise'), form=document.getElementById('ego-select-form');
 let sequence=0;
 select.addEventListener('change',async()=>{
  const current=++sequence, value=select.value, button=document.getElementById('ego-select-button');
  button.disabled=true;document.getElementById('ego-preview').replaceChildren();
  if(!value){history.replaceState(null,'',location.pathname);return;}
  try {
   const url=new URL(location.href);url.searchParams.set('exercise',value);
   const response=await fetch(url,{credentials:'same-origin'});
   if(!response.ok)throw new Error('Preview unavailable');
   const page=new DOMParser().parseFromString(await response.text(),'text/html');
   if(current!==sequence)return;
   document.getElementById('ego-preview').replaceChildren(...page.getElementById('ego-preview').childNodes);
   form.action=form.dataset.recordBase+encodeURIComponent(value);button.disabled=false;
   history.replaceState(null,'',url);
  } catch(error) {if(current===sequence)document.getElementById('ego-preview').textContent='Could not load the exercise. Choose it again to retry.';}
 });
})();
