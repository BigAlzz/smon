(function(){
  // Build cascading selects from JSON in data-orgunits
  function initCascade(){
    const dataEl = document.getElementById('orgunits-data');
    if(!dataEl) {
      console.error('orgunits-data element not found');
      return;
    }
    console.log('Found orgunits-data element:', dataEl);
    const rawData = dataEl.textContent || '[]';
    console.log('Raw org units data:', rawData);
    const data = JSON.parse(rawData);
    console.log('Parsed org units data:', data);

    const byId = Object.fromEntries(data.map(u=>[u.id, u]));
    const ceos = data.filter(x=>x.type==='CEO_OFFICE');
    const chiefs = data.filter(x=>x.type==='CHIEF_DIRECTORATE');
    console.log('CEO Office units:', ceos);
    console.log('Chief Directorate units:', chiefs);

    const selChief = document.getElementById('id_org_cdu');
    const selDir = document.getElementById('id_org_dir');
    const selSub = document.getElementById('id_org_sub');
    const hiddenMulti = document.getElementById('id_org_units');

    console.log('Dropdown elements found:', {
      selChief: !!selChief,
      selDir: !!selDir,
      selSub: !!selSub,
      hiddenMulti: !!hiddenMulti
    });

    function childrenOf(parentId){ return data.filter(x=>x.parent === parentId); }

    function setOptions(sel, items){
      if (!sel) {
        console.error('setOptions called with null selector');
        return;
      }
      console.log('Setting options for', sel.id, 'with', items.length, 'items');
      sel.innerHTML = '';
      const ph = document.createElement('option'); ph.value=''; ph.textContent='— Select —'; sel.appendChild(ph);
      items.forEach(it=>{
        const o = document.createElement('option');
        o.value = it.id; o.textContent = it.name;
        sel.appendChild(o);
        console.log('Added option:', it.name, 'with ID:', it.id);
      });
    }

    function syncHidden(){
      const selected = [selChief.value, selDir.value, selSub.value].filter(Boolean);
      Array.from(hiddenMulti.options).forEach(o=> o.selected = false);
      selected.forEach(id=>{
        const op = Array.from(hiddenMulti.options).find(o=>o.value===id);
        if(op) op.selected = true;
      });
      hiddenMulti.dispatchEvent(new Event('change'));
    }

    // First level: CEO Office and/or Chief Directorates
    const topLevel = [...ceos, ...chiefs];
    console.log('Top level units for first dropdown:', topLevel);
    setOptions(selChief, topLevel);
    setOptions(selDir, []);
    setOptions(selSub, []);

    selChief.addEventListener('change', function(){
      const d = childrenOf(selChief.value); // generic children regardless of type
      setOptions(selDir, d);
      setOptions(selSub, []);
      syncHidden();
    });

    selDir.addEventListener('change', function(){
      const s = childrenOf(selDir.value);
      setOptions(selSub, s);
      syncHidden();
    });

    selSub.addEventListener('change', syncHidden);

    // Preselect existing selections (deepest first)
    const selectedIds = Array.from(hiddenMulti.selectedOptions).map(o=>o.value);
    function preselectChain(){
      let preChief = null, preDir = null, preSub = null;
      const subSel = selectedIds.find(id => byId[id] && byId[id].type==='SUB_DIRECTORATE');
      const dirSel = selectedIds.find(id => byId[id] && byId[id].type==='DIRECTORATE');
      const topSel = selectedIds.find(id => byId[id] && (byId[id].type==='CEO_OFFICE' || byId[id].type==='CHIEF_DIRECTORATE'));
      if(subSel){
        preSub = subSel;
        const dir = byId[byId[subSel].parent];
        if(dir){ preDir = dir.id; const top = byId[dir.parent]; if(top){ preChief = top.id; } }
      } else if(dirSel){
        preDir = dirSel;
        const top = byId[byId[dirSel].parent]; if(top){ preChief = top.id; }
      } else if(topSel){
        preChief = topSel;
      }

      // Apply
      if(preChief){ selChief.value = preChief; selChief.dispatchEvent(new Event('change')); }
      if(preDir){ selDir.value = preDir; selDir.dispatchEvent(new Event('change')); }
      if(preSub){ selSub.value = preSub; selSub.dispatchEvent(new Event('change')); }
    }
    preselectChain();
  }

  document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded - starting cascade initialization');
    initCascade();
  });
})();

