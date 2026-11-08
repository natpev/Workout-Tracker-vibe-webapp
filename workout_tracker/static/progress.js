// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// Small local SVG tooltip. Point metadata is escaped in HTML and inserted only
// with textContent. Mouse, keyboard and touch share the same measurements.
"use strict";
document.querySelectorAll('.progress-series').forEach(section=>{
  const tooltip=section.querySelector('[data-chart-tooltip]');if(!tooltip)return;
  let current=null;
  // Remove both the visible bubble and its association with the last selected dot.
  const hide=()=>{tooltip.hidden=true;if(current)current.removeAttribute('aria-describedby');current=null;};
  // Reuse the escaped point metadata and clamp the bubble inside the viewport.
  const show=point=>{
    if(current&&current!==point)current.removeAttribute('aria-describedby');current=point;
    tooltip.textContent=point.dataset.tooltip;tooltip.hidden=false;point.setAttribute('aria-describedby',tooltip.id);
    const dot=point.getBoundingClientRect(),box=tooltip.getBoundingClientRect();
    const left=Math.max(8,Math.min(innerWidth-box.width-8,dot.right+10));
    const top=Math.max(8,Math.min(innerHeight-box.height-8,dot.top-box.height-10));
    tooltip.style.left=left+'px';tooltip.style.top=top+'px';
  };
  // All interaction methods call the same show/hide functions; no measurements change.
  section.querySelectorAll('.chart-point').forEach(point=>{
    point.addEventListener('mouseenter',()=>show(point));point.addEventListener('mouseleave',hide);
    point.addEventListener('focus',()=>show(point));point.addEventListener('blur',hide);
    point.addEventListener('click',event=>{event.stopPropagation();show(point);});
    point.addEventListener('keydown',event=>{if(event.key==='Escape')hide();if(event.key==='Enter'||event.key===' '){event.preventDefault();show(point);}});
  });
  document.addEventListener('click',hide);window.addEventListener('resize',hide);window.addEventListener('scroll',hide,{passive:true});
});
