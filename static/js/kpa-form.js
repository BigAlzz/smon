(function(){
  function text(sel){ const el = document.querySelector(sel); return el && el.value ? el.value.trim() : ''; }
  function selText(sel){ const el = document.querySelector(sel); return el && el.selectedOptions[0] ? el.selectedOptions[0].textContent.trim() : ''; }
  function unitsText(){
    const sel = document.getElementById('id_org_units');
    if(!sel) return '';
    const opts = Array.from(sel.selectedOptions).map(o=>o.textContent.trim());
    return opts.join(', ');
  }
  function refreshSummary(){
    document.getElementById('owner-summary').textContent = selText('#id_owner') || '—';
    document.getElementById('unit-summary').textContent = unitsText() || '—';
  }
  document.addEventListener('change', function(e){
    if(e.target.closest('#id_owner, #id_org_units')) refreshSummary();
  });
  document.addEventListener('DOMContentLoaded', refreshSummary);

  // Client-side required markers and scroll-to-first-error on submit
  document.addEventListener('submit', function(e){
    const form = e.target.closest('form');
    if(!form) return;
    const required = ['#id_title','#id_financial_year','#id_owner'];
    let firstMissing = null;
    required.forEach(sel=>{
      const el = document.querySelector(sel);
      if(el && !el.value){
        el.classList.add('is-invalid');
        if(!firstMissing) firstMissing = el;
      } else if(el){
        el.classList.remove('is-invalid');
      }
    });
    if(firstMissing){
      e.preventDefault();
      firstMissing.scrollIntoView({behavior:'smooth', block:'center'});
    }
  }, true);
})();

