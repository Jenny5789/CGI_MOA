(() => {
  const resultImg = document.getElementById('hero-result-img');
  const objectImg = document.getElementById('hero-object-img');
  const bgImg = document.getElementById('hero-bg-img');
  const thumbs = document.querySelectorAll('#hero-thumbs .ln-thumb-polaroid');
  const bgLayerA = document.getElementById('bg-blur-a');
  const bgLayerB = document.getElementById('bg-blur-b');

  if (resultImg && thumbs.length && bgLayerA && bgLayerB) {
    const sources = Array.from(thumbs).map((el) => el.dataset.src);
    bgLayerA.style.backgroundImage = `url(${sources[0]})`;

    let current = 0;
    let showingA = true;

    function goTo(index) {
      current = index;
      const src = sources[current];

      resultImg.src = src;
      const t = thumbs[current];
      if (objectImg && t.dataset.object) objectImg.src = t.dataset.object;
      if (bgImg && t.dataset.bg) bgImg.src = t.dataset.bg;
      thumbs.forEach((el, i) => el.classList.toggle('active', i === current));

      const nextLayer = showingA ? bgLayerB : bgLayerA;
      const prevLayer = showingA ? bgLayerA : bgLayerB;
      nextLayer.style.backgroundImage = `url(${src})`;
      nextLayer.classList.add('active');
      prevLayer.classList.remove('active');
      showingA = !showingA;
    }

    thumbs.forEach((el, i) => {
      el.addEventListener('click', () => goTo(i));
    });

    setInterval(() => goTo((current + 1) % sources.length), 2600);
  }

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
})();
