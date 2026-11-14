/* Browser-only review state. No localStorage, IndexedDB, telemetry files or remote services.
   Time-series points are distinct collections observed by this browser, capped at 120
   per owner/channel. The server remains a latest-result view, not a history database. */
"use strict";
(() => {
  const LIMIT = 120;
  const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const formatValue = value => {
    if (typeof value === "boolean") return value ? "Detected / active" : "Not detected / inactive";
    if (!Number.isFinite(value)) return "—";
    const magnitude = Math.abs(value);
    if (value !== 0 && (magnitude < .001 || magnitude >= 1e6)) return value.toExponential(3);
    return new Intl.NumberFormat("en", {maximumFractionDigits: magnitude < .1 ? 6 : magnitude < 10 ? 3 : 2}).format(value);
  };
  const utc = value => new Date(value).toISOString().replace("T", " ").replace(/\.\d{3}Z$/, " UTC");
  const shortTime = value => new Date(value).toISOString().slice(11,19);
  const duration = seconds => seconds >= 86400 ? `${(seconds/86400).toFixed(1)} d` : seconds >= 3600 ? `${(seconds/3600).toFixed(1)} h` : seconds >= 60 ? `${(seconds/60).toFixed(1)} min` : `${Math.round(seconds)} s`;
  const isLab = meta => meta.scope === "crew" && ["serum", "plasma", "saliva", "24h urine", "spot urine", "interstitial fluid", "local sweat"].includes(meta.specimen);
  const HYDRATION_CHANNELS = new Set(["body_mass", "urine_specific_gravity", "sweat_rate", "sweat_sodium_concentration", "sweat_sodium_flux", "urine_volume_24h"]);
  const groupOf = meta => meta.scope === "environment" ? "environment" : HYDRATION_CHANNELS.has(meta.channel) ? "hydration" : isLab(meta) ? "lab" : "crew";
  function baselineText(entry) {
    const baseline = entry?.baseline_source_value;
    if (!(baseline > 0) || typeof entry.source_value !== "number") return "";
    const change = 100 * (entry.source_value / baseline - 1);
    const direction = Math.abs(change) < 0.0001 ? "at" : change > 0 ? "above" : "below";
    const label = entry.reading.channel === "body_mass" ? "configured mass baseline" : "configured local reference";
    return direction === "at" ? `At ${label}` : `${formatValue(Math.abs(change))}% ${direction} ${label}`;
  }
  const displayed = (entry, units) => units === "wire" ? entry.reading.value : entry.source_value;
  const displayUnit = (meta, units) => units === "wire" ? meta.unit : meta.source_unit;
  const keyOf = (owner, channel) => JSON.stringify([owner, channel]);

  function chartSVG(points, units, width=300, height=80) {
    const usable = points.filter(p => typeof displayed(p, units) === "number");
    if (!usable.length) return '<div class="plot-empty">No numeric observations yet</div>';
    const values = usable.map(p => displayed(p, units));
    const times = usable.map(p => Date.parse(p.reading.measured_at));
    const min = Math.min(...values), max = Math.max(...values);
    const pad = Math.max((max-min)*.2, Math.abs(max)*.002, 1e-12);
    const x = time => 6 + (width-12)*(times.length === 1 ? .5 : (time-times[0])/Math.max(1,times.at(-1)-times[0]));
    const y = value => height-10 - (height-20)*(value-(min-pad))/(max-min+2*pad);
    const coordinates = values.map((v,i) => `${x(times[i]).toFixed(2)},${y(v).toFixed(2)}`).join(" ");
    const dots = usable.map((p,i) => `<circle cx="${x(times[i]).toFixed(2)}" cy="${y(values[i]).toFixed(2)}" r="${usable.length===1?3:2}" fill="currentColor"><title>${escapeHTML(formatValue(values[i]))} · ${escapeHTML(utc(p.reading.measured_at))}</title></circle>`).join("");
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${usable.length} observed samples; range ${escapeHTML(formatValue(min))} to ${escapeHTML(formatValue(max))}" style="color:var(--accent)"><line x1="0" y1="${height-9}" x2="${width}" y2="${height-9}" stroke="#e9eff2"/>${usable.length>1?`<polyline points="${coordinates}" fill="none" stroke="currentColor" stroke-width="1.6" vector-effect="non-scaling-stroke"/>`:""}${dots}</svg>`;
  }

  // Expose pure formatting/chart helpers for dependency-free Node tests.
  globalThis.ImitacijaView = {formatValue, chartSVG, escapeHTML, duration, isLab, groupOf, baselineText, displayed, LIMIT};
  if (typeof document === "undefined") return;

  const $ = id => document.getElementById(id);
  const state = {metadata: null, run: null, snapshot: null, rows: new Map(), cards: new Map(), history: new Map(), units:"source", view:"all", paused:false, selected:null, lastDetailStamp:null};
  const groups = {
    crew: {title:"Crew physiology", subtitle:"Vital signs & supporting observations", description:"Each measurement retains its own acquisition time. Result interpretation belongs to the backend."},
    hydration: {title:"Dehydration & Electrolyte Loss", subtitle:"PDF page 2 · objective hydration inputs", description:"PDF screening inputs: acute body-mass loss >2%, urine specific gravity >1.020, and local sweat rate / sodium flux relative to baseline. Mass change alone does not establish water retention. Sparse samples cannot establish an acute event; activity changes local sweat flow."},
    lab: {title:"Biochemistry & laboratory results", subtitle:"Specimen-specific measurements", description:"CGM accompanies episodic laboratory results. Waiting for a scheduled collection or processing is expected."},
    environment: {title:"Environment", subtitle:"Independent compartment sensors", description:"Shared cabin measurements. Monitor dose is distinct from an astronaut’s personal effective or career dose."}
  };
  for (const [key, group] of Object.entries(groups)) {
    const section = document.createElement("section"); section.id=`group-${key}`;
    section.innerHTML=`<div class="group-header"><h2>${group.title}</h2><span>${group.subtitle}</span></div><p class="group-description">${group.description}</p><div class="grid" id="grid-${key}"></div>`;
    $("sections").append(section);
  }

  function initialize(meta, snapshot) {
    state.metadata=meta; state.run=snapshot.run_id; state.rows.clear(); state.cards.clear(); state.history.clear();
    for (const key of Object.keys(groups)) $(`grid-${key}`).replaceChildren();
    $("owner").replaceChildren(new Option("All owners", "all"));
    for (const owner of [...snapshot.crew_ids, meta.environment.id]) $("owner").add(new Option(owner, owner));
    for (const channel of meta.channels) {
      const owners = channel.scope === "environment" ? [meta.environment.id] : snapshot.crew_ids;
      for (const owner of owners) {
        const key=keyOf(owner,channel.channel);
        state.rows.set(key, {meta:channel, owner, entry:null});
        const card=document.createElement("article"); card.className="card"; card.dataset.key=key;
        card.innerHTML=`<div class="card-head"><div><h3 class="card-title">${escapeHTML(channel.name)}</h3><div class="owner-label">${escapeHTML(owner)} · ${escapeHTML(channel.specimen)}</div></div><span class="pill">Awaiting</span></div><div class="value-row"><span class="value waiting">—</span><span class="unit"></span></div><div class="baseline-note"></div><div class="plot"></div><div class="plot-caption"><span class="sample-count"></span><span class="range"></span></div><div class="card-foot"><span class="age"></span><button type="button" aria-label="Inspect ${escapeHTML(channel.name)} for ${escapeHTML(owner)}">Inspect ↗</button></div>`;
        card.querySelector("button").addEventListener("click",()=>openDetail(key));
        $(`grid-${groupOf(channel)}`).append(card); state.cards.set(key,card);
      }
    }
    $("all-count").textContent=state.rows.size;
    $("loading").hidden=true;
    if (state.selected) {$("detail").close(); state.selected=null;}
  }

  function chartCaption(points, units) {
    const values=points.map(p=>displayed(p,units)).filter(v=>typeof v==="number");
    return values.length ? `${formatValue(Math.min(...values))}–${formatValue(Math.max(...values))}` : "Categorical result";
  }

  function render() {
    if (!state.snapshot) return;
    const search=$("search").value.trim().toLowerCase(), owner=$("owner").value, status=$("status").value;
    let available=0, waiting=0, enabled=0, visible=0;
    const groupCounts={crew:0,hydration:0,lab:0,environment:0};
    for (const [key,row] of state.rows) {
      const {meta, entry}=row, card=state.cards.get(key), history=state.history.get(key)||[];
      if (meta.enabled) {enabled++; if(entry) available++; else waiting++;}
      const matchesSearch=[meta.name,meta.channel,meta.specimen,row.owner].some(text=>text.toLowerCase().includes(search));
      const matchesView=state.view==="all" || groupOf(meta)===state.view;
      const matchesStatus=status==="all" || status==="available"&&entry || status==="waiting"&&!entry&&meta.enabled;
      const show=matchesSearch&&matchesView&&matchesStatus&&(owner==="all"||owner===row.owner);
      card.hidden=!show;
      if(show){visible++; groupCounts[groupOf(meta)]++;}
      card.classList.toggle("disabled",!meta.enabled);
      const pill=card.querySelector(".pill"); pill.className="pill"; pill.textContent=!meta.enabled?"Disabled":entry?"Available":"Awaiting";
      const value=card.querySelector(".value"); value.classList.toggle("waiting",!entry);
      value.textContent=entry?(typeof displayed(entry,state.units)==="boolean" ? (displayed(entry,state.units)?"Detected":"Not detected") :formatValue(displayed(entry,state.units))):"—";
      if (meta.channel==="spe_flag" && entry) value.textContent=entry.reading.value?"Active":"No event";
      card.querySelector(".unit").textContent=meta.value_schema==="boolean"?"":displayUnit(meta,state.units);
      const baseline=card.querySelector(".baseline-note");
      baseline.textContent=baselineText(entry); baseline.hidden=!baseline.textContent;
      const stamp=`${entry?.reading.measured_at}|${state.units}|${state.run}`;
      if (card.dataset.stamp!==stamp) {
        card.querySelector(".plot").innerHTML=entry?chartSVG(history,state.units):'<div class="plot-empty">'+(meta.enabled?"Waiting for collection / result availability":"Not enabled in this profile")+'</div>';
        card.querySelector(".sample-count").textContent=entry?`${history.length} observed ${history.length===1?"sample":"samples"}`:"No sample yet";
        card.querySelector(".range").textContent=entry?chartCaption(history,state.units):"";
        card.dataset.stamp=stamp;
      }
      card.querySelector(".age").textContent=entry?`${duration(Math.max(0,(Date.parse(state.snapshot.simulation_time)-Date.parse(entry.reading.measured_at))/1000))} ago · sim`:(meta.enabled?"Independently scheduled":"Disabled by profile");
    }
    $("available").textContent=`${available} / ${enabled}`; $("waiting").textContent=waiting;
    $("sim-time").textContent=utc(state.snapshot.simulation_time);
    $("speed").textContent=`${state.snapshot.speed.toLocaleString()}× speed · run ${state.run.slice(0,8)}`;
    for(const key of Object.keys(groups)) $(`group-${key}`).hidden=groupCounts[key]===0;
    $("empty").hidden=visible!==0;
    renderDetail();
  }

  function openDetail(key) {state.selected=key; state.lastDetailStamp=null; renderDetail(); $("detail").showModal();}
  function renderDetail() {
    if (!state.selected) return;
    const row=state.rows.get(state.selected); if(!row)return;
    const {meta,entry}=row, history=state.history.get(state.selected)||[];
    const stamp=`${entry?.reading.measured_at}|${state.units}|${state.selected}`;
    if(stamp===state.lastDetailStamp)return;
    state.lastDetailStamp=stamp;
    $("detail-owner").textContent=`${meta.scope} / ${row.owner}`; $("detail-title").textContent=meta.name;
    const details=[
      ["Channel",meta.channel],["Specimen / input",meta.specimen],["Method",meta.method],
      ["Collection",entry?utc(entry.reading.measured_at):"No result available yet"],
      ["Schedule",meta.collection_schedule],
      ["Raw acquisition",meta.raw_acquisition_hz ? `${meta.raw_acquisition_hz} Hz (model input)` : "No continuous raw stream declared"],
      ["Timing source",`${meta.frequency_basis} · rows ${(meta.frequency_matrix_rows||[]).join(", ") || "not specified"}`],["Window",meta.window_s?duration(meta.window_s):"Point measurement"],
      ["Processing delay",duration(meta.availability_delay_s)+" (simulation time)"],
      ["Wire unit",meta.unit],["Source unit",meta.source_unit],
      ...(entry?.baseline_source_value ? [["Configured baseline",`${formatValue(entry.baseline_source_value)} ${meta.source_unit}`], ["Baseline comparison",baselineText(entry)]] : [])
    ];
    const sources=meta.citations.filter(url=>/^https:\/\//.test(url)).map(url=>`<a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(new URL(url).hostname)} ↗</a>`).join("");
    $("detail-content").innerHTML=`<div><span class="detail-value">${entry?escapeHTML(formatValue(displayed(entry,state.units))):"Awaiting sample"}</span><span class="unit">${escapeHTML(displayUnit(meta,state.units))}</span> <span class="pill">${!meta.enabled?"Disabled":entry?"Available":"Awaiting"}</span></div><div class="detail-chart">${chartSVG(history,state.units,640,180)}</div><p class="detail-note">${history.length} observed samples · ${history.length?escapeHTML(chartCaption(history,state.units)):"No numeric series yet"}. ${history.length?escapeHTML(utc(history[0].reading.measured_at))+" → "+escapeHTML(utc(history.at(-1).reading.measured_at)):""} Lines are visual guides between observations, not reconstructed measurements.</p><dl>${details.map(([key,value])=>`<dt>${escapeHTML(key)}</dt><dd>${escapeHTML(value)}</dd>`).join("")}</dl><h3>Measurement sources</h3><p class="detail-note">Sources describe the stated assay or measurement method. Model waveform coefficients remain assumptions; a citation does not validate the full simulation.</p><div class="sources">${sources}</div><h3>Exact POST body · SI units</h3><pre>${entry?escapeHTML(JSON.stringify(entry.reading,null,2)):"No sampled result to display."}</pre>`;
  }

  async function poll() {
    if(state.paused)return;
    try {
      const response=await fetch("/readings",{cache:"no-store",signal:AbortSignal.timeout(5000)});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const snapshot=await response.json();
      if(state.paused)return;
      if(!state.metadata||snapshot.run_id!==state.run){
        const metaResponse=await fetch("/dictionary",{cache:"no-store",signal:AbortSignal.timeout(5000)});
        if(!metaResponse.ok)throw new Error(`Dictionary HTTP ${metaResponse.status}`);
        const metadata=await metaResponse.json();
        if(state.paused)return;
        initialize(metadata,snapshot);
      }
      state.snapshot=snapshot;
      for(const entry of snapshot.readings){
        const key=keyOf(entry.owner,entry.reading.channel), row=state.rows.get(key); if(!row)continue;
        row.entry=entry;
        const history=state.history.get(key)||[];
        if(!history.length||Date.parse(entry.reading.measured_at)>Date.parse(history.at(-1).reading.measured_at)){
          history.push(entry); if(history.length>LIMIT)history.shift(); state.history.set(key,history);
        }
      }
      $("connection").className="connection live"; $("connection").textContent="Live · 1 s refresh"; render();
    } catch(error) {
      $("connection").className="connection error"; $("connection").textContent="Disconnected · retrying";
      $("loading").textContent="Cannot reach the simulator. Check that preview mode is still running.";
      // Existing values remain visible with their original timestamps after a network error.
    }
  }
  for(const button of document.querySelectorAll("[data-view]"))button.addEventListener("click",()=>{
    state.view=button.dataset.view;
    for(const item of document.querySelectorAll("[data-view]")){item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",String(item===button));}
    render();
  });
  for(const id of ["search","owner","status"])$(id).addEventListener("input",render);
  for(const radio of document.querySelectorAll('[name="units"]'))radio.addEventListener("change",()=>{state.units=radio.value;render();});
  $("pause").addEventListener("click",()=>{state.paused=!state.paused;$("pause").textContent=state.paused?"Resume view":"Pause view";if(state.paused){$("connection").className="connection";$("connection").textContent="View paused";}else void poll();});
  $("close-detail").addEventListener("click",()=>$("detail").close());
  $("detail").addEventListener("close",()=>{state.selected=null;});
  async function refreshLoop(){await poll();setTimeout(refreshLoop,1000);}
  void refreshLoop();
})();
