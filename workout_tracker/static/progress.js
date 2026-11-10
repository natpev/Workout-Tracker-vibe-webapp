// SHAMELESSLY VIBE-CODED — AI-generated with minimal human supervision. Review before trusting.
// Small local SVG tooltip. Point metadata is escaped in HTML and inserted only
// with textContent. Mouse, keyboard and touch share the same measurements.
"use strict";
document.querySelectorAll('.progress-series').forEach(section=>{
  const tooltip=section.querySelector('[data-chart-tooltip]');if(!tooltip)return;
  let current=null,pinned=false;
  // Remove both the visible bubble and its association with the last selected dot.
  const hide=()=>{tooltip.hidden=true;if(current)current.removeAttribute('aria-describedby');current=null;pinned=false;};
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
    point.addEventListener('mouseenter',()=>{pinned=false;show(point);});
    // Touch can synthesize mouseleave after click. An activated label stays
    // open until outside click, blur, Escape or scrolling its point offscreen.
    point.addEventListener('mouseleave',()=>{if(!pinned)hide();});
    point.addEventListener('focus',()=>show(point));point.addEventListener('blur',hide);
    point.addEventListener('click',event=>{event.stopPropagation();pinned=true;show(point);});
    point.addEventListener('keydown',event=>{if(event.key==='Escape')hide();if(event.key==='Enter'||event.key===' '){event.preventDefault();show(point);}});
  });
  document.addEventListener('click',hide);window.addEventListener('resize',hide);
  // Tapping/focusing a point can scroll it into view after the click arrives.
  // Keep its bubble attached while the point is visible instead of letting a
  // delayed browser scroll immediately erase the just-opened touch tooltip.
  window.addEventListener('scroll',()=>{
    if(!current)return;
    const dot=current.getBoundingClientRect();
    if(dot.bottom<0||dot.top>innerHeight||dot.right<0||dot.left>innerWidth)hide();
    else show(current);
  },{passive:true});
});
