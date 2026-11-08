// SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
// Independent read-only polling survives the application's restart. Safe console
// text is inserted with textContent; no HTML, paths or commands are accepted.
"use strict";
(() => {
  const box=document.getElementById('console'), summary=document.getElementById('current-status'), operation=document.getElementById('operation-id');
  let selected=new URLSearchParams(location.search).get('operation'), current=null, cursor=0, lines=[];
  document.getElementById('latest').addEventListener('click',()=>{box.scrollTop=box.scrollHeight;});
  // Read only the host endpoints. A sequence cursor avoids retransferring old lines;
  // the host ring remains authoritative after refresh or a missed poll.
  const poll=async()=>{
    try {
      const response=await fetch('/status.json',{cache:'no-store'});if(!response.ok)throw new Error('status');
      const state=await response.json();summary.textContent=state.status;
      document.getElementById('last-success').textContent=state.last_success||'None';document.getElementById('last-failure').textContent=state.last_failure||'None';
      const identity=selected||state.operation;operation.textContent=identity||'None';
      if(identity){
        // Follow only when already at the bottom; preserve a reader scrolling upward.
        const oldScroll=box.scrollTop,atBottom=box.scrollHeight-box.scrollTop-box.clientHeight<24;
        if(current!==identity){current=identity;cursor=0;lines=[];box.textContent='';}
        const query=new URLSearchParams({operation:identity,after:String(cursor)});
        const result=await fetch('/console.json?'+query,{cache:'no-store'});
        if(result.ok){
          const data=await result.json();
          if(data.first>cursor+1||data.last<cursor){lines=[];cursor=0;}
          for(const row of data.lines){if(row.sequence>cursor){lines.push(row.time.slice(11,19)+' UTC  '+row.text);cursor=row.sequence;}}
          lines=lines.slice(-500);box.textContent=lines.join('\n');
          if(atBottom)box.scrollTop=box.scrollHeight;else box.scrollTop=oldScroll;
        }
      }
      document.getElementById('connection').textContent='Live read-only connection';
    }catch{document.getElementById('connection').textContent='Connection interrupted; reconnecting. Retained output stays visible.';}
    setTimeout(poll,1500);
  };
  poll();
})();
