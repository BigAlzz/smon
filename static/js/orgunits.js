(function(){
  // Optional: If you want cascading behavior, listen to changes and filter options.
  // This assumes existence of three selects with data-org-level attributes (chief/directorate/sub).
  function filterChildOptions(parentSel, childSel){
    const parent = document.querySelector(parentSel);
    const child = document.querySelector(childSel);
    if(!parent || !child) return;
    const val = parent.value;
    Array.from(child.options).forEach(opt => {
      const p = opt.getAttribute('data-parent');
      opt.hidden = !!(p && p !== val);
    });
    child.dispatchEvent(new Event('change'));
  }
  document.addEventListener('change', function(e){
    const el = e.target;
    if(el.matches('[data-org-level="chief"]')){
      filterChildOptions('[data-org-level="chief"]','[data-org-level="dir"]');
    }
    if(el.matches('[data-org-level="dir"]')){
      filterChildOptions('[data-org-level="dir"]','[data-org-level="sub"]');
    }
  });
})();

