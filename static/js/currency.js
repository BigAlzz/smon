(function(){
  function formatZAR(n){
    const num = Number(n || 0);
    if (Number.isNaN(num)) return '';
    return 'R ' + num.toLocaleString('en-ZA', {minimumFractionDigits:2, maximumFractionDigits:2});
  }
  document.addEventListener('blur', function(e){
    const el = e.target.closest('input[data-currency="zar"]');
    if(!el) return;
    const raw = (el.value||'').replace(/[R\s,]/g,'');
    const num = parseFloat(raw);
    if(!isNaN(num)){
      el.value = num.toFixed(2);
      const label = el.parentElement.querySelector('.currency-display');
      if(label){ label.textContent = formatZAR(num); }
    }
  }, true);
  document.addEventListener('input', function(e){
    const el = e.target.closest('input[data-currency="zar"]');
    if(!el) return;
    const container = el.parentElement;
    let badge = container.querySelector('.currency-display');
    if(!badge){
      badge = document.createElement('div');
      badge.className = 'form-text currency-display';
      container.appendChild(badge);
    }
    const raw = (el.value||'').replace(/[R\s,]/g,'');
    const num = parseFloat(raw);
    if(!isNaN(num)) badge.textContent = formatZAR(num);
  });
})();

