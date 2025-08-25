(function(){
  function ajax(url, data, cb){
    fetch(url, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCsrfToken()
      },
      body: new URLSearchParams(data)
    }).then(r => r.json()).then(cb).catch(err => {
      console.error(err);
      alert('Failed to save.');
    });
  }

  function getCsrfToken(){
    // Use global function if available
    if (window.getCSRFToken) {
      return window.getCSRFToken();
    }

    // Fallback to original implementation
    const name = 'csrftoken=';
    const parts = document.cookie.split(';');
    for(let p of parts){
      p = p.trim();
      if(p.startsWith(name)) return p.substring(name.length);
    }
    // fallback: try meta tag
    const m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute('content') : '';
  }

  function makeEditable(cell){
    const field = cell.getAttribute('data-field');
    const itemId = cell.getAttribute('data-item');
    const type = cell.getAttribute('data-type') || 'text';
    const display = cell.textContent.trim();

    const input = document.createElement('input');
    input.type = (type === 'decimal') ? 'text' : 'text';
    input.value = display.replace(/^R\s*/, '').replace(/,/g, '');
    input.className = 'form-control form-control-sm';

    const orig = cell.innerHTML;
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    input.select();

    function done(save){
      if(!save){ cell.innerHTML = orig; return; }
      ajax(`/plan/item/${itemId}/update-field`, {field: field, value: input.value}, function(resp){
        if(resp && resp.ok){
          cell.innerHTML = resp.display;
        } else {
          alert(resp && resp.error ? resp.error : 'Failed to save.');
          cell.innerHTML = orig;
        }
      });
    }

    input.addEventListener('keydown', function(e){
      if(e.key === 'Enter'){ done(true); }
      if(e.key === 'Escape'){ done(false); }
    });
    input.addEventListener('blur', function(){ done(true); });
  }

  document.addEventListener('click', function(e){
    const cell = e.target.closest('[data-inline="true"]');
    if(!cell) return;
    makeEditable(cell);
  });
})();

