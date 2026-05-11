// MC core-api — minimal client-side helpers

// Reveal row action buttons on hover (CSS handles this, JS for touch)
document.addEventListener('htmx:afterSettle', function() {
  // Re-bind any newly loaded rows
  document.querySelectorAll('.row').forEach(row => {
    row.addEventListener('mouseenter', () => {
      row.querySelector('.row-actions')?.style.setProperty('opacity', '1');
    });
    row.addEventListener('mouseleave', () => {
      row.querySelector('.row-actions')?.style.setProperty('opacity', '0');
    });
  });
});

// Clear capture input after successful POST
document.addEventListener('htmx:afterRequest', function(e) {
  if (e.detail.elt?.closest('form') && e.detail.successful) {
    const input = e.detail.elt.closest('form')?.querySelector('#capture-input');
    if (input) input.value = '';
  }
});
