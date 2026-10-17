'use strict';
let state, token, selected = 'asset-001', playing = false, busy = false, timer;
const $ = id => document.getElementById(id);
const points = [[300,65],[505,165],[430,335],[170,335],[95,165]];
const svgNS = 'http://www.w3.org/2000/svg';
function svgElement(tag, attributes, text) {
  const element = document.createElementNS(svgNS, tag);
  for (const [key,value] of Object.entries(attributes)) element.setAttribute(key,value);
  if (text !== undefined) element.textContent = text;
  return element;
}
function pause() { playing = false; clearTimeout(timer); $('play').textContent = 'Play'; }
function controls() { for (const id of ['step','reset','play']) $(id).disabled = busy || !state; }
function render() {
  $('clock').textContent = `Epoch ${state.epoch} · Tick ${state.tick} · ${state.simulated_seconds}s simulated`;
  for (const label of ['HEALTHY','WARNING','CRITICAL']) $(label.toLowerCase()).textContent = state.totals[label];
  const svg = $('network'); svg.replaceChildren();
  const defs = svgElement('defs', {});
  for (const active of [false,true]) {
    const marker = svgElement('marker',{id:active?'arrow-active':'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:5,markerHeight:5,orient:'auto'});
    marker.append(svgElement('path',{d:'M 0 0 L 10 5 L 0 10 z',class:active?'arrow active':'arrow'})); defs.append(marker);
  } svg.append(defs);
  points.forEach(([x,y],i) => {
    const [nx,ny] = points[(i+1)%5], dx=nx-x, dy=ny-y, length=Math.hypot(dx,dy);
    const active=state.effects.some(e=>e.predecessor.asset_id===state.assets[i].asset_id);
    svg.append(svgElement('line',{x1:x+dx*51/length,y1:y+dy*51/length,x2:nx-dx*54/length,y2:ny-dy*54/length,class:active?'edge active':'edge','marker-end':`url(#${active?'arrow-active':'arrow'})`}));
  });
  state.assets.forEach((asset,i) => {
    const [x,y]=points[i];
    const group=svgElement('g',{class:`asset s${asset.severity}${selected===asset.asset_id?' selected':''}`,role:'button',tabindex:0,'aria-label':`${asset.asset_id}: ${asset.condition}`,'aria-pressed':String(selected===asset.asset_id),'data-asset':asset.asset_id});
    group.append(svgElement('circle',{cx:x,cy:y,r:46}));
    group.append(svgElement('text',{x,y:y-3},`Asset ${asset.asset_id.slice(-3)}`));
    group.append(svgElement('text',{x,y:y+16,class:'health-label'},asset.condition));
    const choose=()=>{selected=asset.asset_id;render();}; group.addEventListener('click',choose);
    group.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}});svg.append(group);
  });
  const asset=state.assets.find(a=>a.asset_id===selected);
  $('selected').textContent=`Asset ${selected.slice(-3)}`;
  $('condition').textContent=asset.condition; $('condition').className=`condition ${asset.condition.toLowerCase()}`;
  $('explanation').textContent=state.explanations[selected];
  const table=$('history');table.replaceChildren();
  const heading=document.createElement('tr');
  for(const text of ['Asset / tick',...state.history.map(h=>String(h.tick))]){const cell=document.createElement('th');cell.textContent=text;heading.append(cell);}table.append(heading);
  state.assets.forEach((asset,i)=>{const row=document.createElement('tr'), label=document.createElement('th');label.textContent=`Asset ${asset.asset_id.slice(-3)}`;row.append(label);
    state.history.forEach(h=>{const cell=document.createElement('td'), level=h.severities[i];cell.className=`s${level}`;cell.textContent=['H','W','C'][level];cell.title=`Epoch ${h.epoch}, tick ${h.tick}: ${['Healthy','Warning','Critical'][level]}`;row.append(cell);});table.append(row);
  });controls();
}
async function refresh() {
  const response=await fetch('/api/state');if(!response.ok)throw new Error('Local server unavailable');
  const result=await response.json();state=result.state;token=result.token;render();
}
async function command(path, body) {
  busy=true;controls();
  try {
    const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Token':token},body:JSON.stringify(body)});
    const result=await response.json();if(!response.ok)throw new Error(result.error);
    state=result.state;render();return result;
  } catch(error) {pause();$('status').textContent=`Stopped: ${error.message}. Refresh to reconcile shared local state.`;throw error;}
  finally{busy=false;controls();}
}
async function step() {
  await command('/api/step',{epoch:state.epoch,tick:state.tick});
  $('status').textContent='Latest arrows and explanation show the recorded previous-tick consequences.';
}
async function playTick() {
  if(!playing||busy)return;
  try {await step();if(state.tick>=6){pause();$('status').textContent='Progression paused at tick 6. Reset to replay the baseline.';}else if(playing)timer=setTimeout(playTick,1000);}catch{ /* Error is visible; no retry. */ }
}
$('step').addEventListener('click',()=>{pause();step().catch(()=>{});});
$('play').addEventListener('click',()=>{if(playing){pause();return;}playing=true;$('play').textContent='Pause';playTick();});
$('reset').addEventListener('click',async()=>{pause();try{const result=await command('/api/reset',{epoch:state.epoch,command_id:crypto.randomUUID()});$('status').textContent=`Local reset ${result.applied?'applied':'already applied'} · epoch ${result.receipt.epoch}. Baseline and recent history restored.`;}catch{}});
controls();refresh().then(()=>{$('status').textContent='Ready. Step twice to see Asset 001 become critical, then reset.';}).catch(error=>{$('status').textContent=error.message;});
