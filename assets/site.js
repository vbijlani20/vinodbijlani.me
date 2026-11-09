// Small progressive enhancements. The site works without this file.
(function () {
  // Topic filter on the publications page
  var buttons = document.querySelectorAll('.filters button');
  var rows = document.querySelectorAll('[data-filterable] > li');
  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      var t = b.dataset.topic;
      buttons.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      rows.forEach(function (li) { li.hidden = !(t === 'all' || li.dataset.topic === t); });
    });
  });

  // Photo lightbox for talk galleries
  var links = Array.prototype.slice.call(document.querySelectorAll('[data-lightbox]'));
  if (!links.length) return;
  var box = document.createElement('div');
  box.className = 'lightbox';
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-modal', 'true');
  box.setAttribute('aria-label', 'Photo viewer');
  box.innerHTML = '<button type="button" class="lb-close" aria-label="Close">×</button>' +
    '<button type="button" class="lb-prev" aria-label="Previous photo">‹</button>' +
    '<img alt=""><button type="button" class="lb-next" aria-label="Next photo">›</button>';
  document.body.appendChild(box);
  var img = box.querySelector('img'), idx = 0;
  function show(i) { idx = (i + links.length) % links.length; img.src = links[idx].href; img.alt = links[idx].querySelector('img').alt; }
  function open(i) { show(i); box.classList.add('open'); box.querySelector('.lb-close').focus(); }
  function close() { box.classList.remove('open'); links[idx].focus(); }
  links.forEach(function (a, i) { a.addEventListener('click', function (ev) { ev.preventDefault(); open(i); }); });
  box.querySelector('.lb-close').addEventListener('click', close);
  box.querySelector('.lb-prev').addEventListener('click', function () { show(idx - 1); });
  box.querySelector('.lb-next').addEventListener('click', function () { show(idx + 1); });
  box.addEventListener('click', function (ev) { if (ev.target === box) close(); });
  document.addEventListener('keydown', function (ev) {
    if (!box.classList.contains('open')) return;
    if (ev.key === 'Escape') close();
    if (ev.key === 'ArrowLeft') show(idx - 1);
    if (ev.key === 'ArrowRight') show(idx + 1);
  });
})();
