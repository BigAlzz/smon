(function(){
  function getSelText(sel){
    if(!sel) return '';
    if(sel.multiple){
      return Array.from(sel.selectedOptions).map(o=>o.textContent.trim()).join(', ');
    }
    return sel.selectedOptions[0] ? sel.selectedOptions[0].textContent.trim() : '';
  }
  function refresh(){
    const m = new Map([
      ['title', document.getElementById('id_title')?.value || ''],
      ['description', document.getElementById('id_description')?.value || ''],
      ['strategic_objective', document.getElementById('id_strategic_objective')?.value || ''],
      ['financial_year', getSelText(document.getElementById('id_financial_year'))],
      ['owner', getSelText(document.getElementById('id_owner'))],
      ['org_units', getSelText(document.getElementById('id_org_units'))],
    ]);
    m.forEach((v,k)=>{
      const el = document.querySelector('[data-preview="'+k+'"]');
      if(el) el.textContent = v || '—';
    });
  }
  document.addEventListener('input', function(e){
    if(e.target.closest('#id_title, #id_description, #id_strategic_objective')) refresh();
  });
  document.addEventListener('change', function(e){
    if(e.target.closest('#id_financial_year, #id_owner, #id_org_units')) refresh();
  });
  document.addEventListener('click', function(e){
    if(e.target.closest('#btn-refresh-preview')) refresh();
  });
  document.addEventListener('DOMContentLoaded', refresh);
})();

