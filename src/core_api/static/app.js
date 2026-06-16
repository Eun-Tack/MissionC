// MC core-api — minimal client-side helpers

// Reveal row action buttons on touch/dynamic content without rebinding rows.
document.addEventListener('pointerover', function(e) {
  e.target.closest?.('.row')?.querySelector('.row-actions')?.style.setProperty('opacity', '1');
});

document.addEventListener('pointerout', function(e) {
  const row = e.target.closest?.('.row');
  if (!row || row.contains(e.relatedTarget)) return;
  row.querySelector('.row-actions')?.style.setProperty('opacity', '0');
});

// Clear capture input after successful POST
document.addEventListener('htmx:afterRequest', function(e) {
  if (e.detail.elt?.closest('form') && e.detail.successful) {
    const input = e.detail.elt.closest('form')?.querySelector('#capture-input');
    if (input) input.value = '';
  }
});
