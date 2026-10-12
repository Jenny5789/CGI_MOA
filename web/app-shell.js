(() => {
  let toastTimer = null;
  function toast(msg) {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 1800);
  }

  document.querySelectorAll('[data-toast]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      toast(btn.dataset.toast);
    });
  });

  document.querySelectorAll('.as-heart').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      btn.classList.toggle('liked');
      btn.textContent = btn.classList.contains('liked') ? '♥' : '♡';
    });
  });

  document.querySelectorAll('.as-toggle-group button').forEach((btn) => {
    btn.addEventListener('click', () => {
      btn.parentElement.querySelectorAll('button').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  document.querySelectorAll('.as-side-item[data-toast]').forEach((item) => {
    item.addEventListener('click', (e) => e.preventDefault());
  });
})();
