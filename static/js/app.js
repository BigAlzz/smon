(function(){
  // Initialize flatpickr on any date inputs
  if(window.flatpickr){
    document.querySelectorAll('input[type="date"], .js-date').forEach(el => {
      flatpickr(el, { dateFormat: 'Y-m-d', allowInput: true });
    });
  }
  // Initialize Choices on any select with .js-choices
  if(window.Choices){
    document.querySelectorAll('select.js-choices').forEach(sel => {
      new Choices(sel, { searchEnabled: true, itemSelectText: '', shouldSort: false });
    });
  // Enable Bootstrap tooltips
  if (window.bootstrap){
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl)
    })
  }

  }
})();

