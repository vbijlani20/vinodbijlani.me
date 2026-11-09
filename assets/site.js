// Small progressive enhancements. The site works without this file.
(function () {
  // Topic filter on the publications page
  var buttons = document.querySelectorAll('.filters button[data-topic]');
  var rows = document.querySelectorAll('[data-filterable] > li');
  buttons.forEach(function (b) {
    b.addEventListener('click', function () {
      var t = b.dataset.topic;
      buttons.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      rows.forEach(function (li) { li.hidden = !(t === 'all' || li.dataset.topic === t); });
    });
  });

  // Search and format filter on the Thought Leadership page
  var q = document.getElementById('tl-q');
  if (q) {
    var records = Array.prototype.slice.call(document.querySelectorAll('#tl-results [data-record]'));
    var groups = document.querySelectorAll('#tl-results [data-group]');
    var kindBtns = document.querySelectorAll('.finder .filters button');
    var status = document.getElementById('tl-status');
    var empty = document.querySelector('#tl-results .empty');
    var kind = 'all';
    var texts = records.map(function (r) { return r.textContent.toLowerCase(); });
    var apply = function () {
      var words = q.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      var shown = 0, talks = 0;
      records.forEach(function (r, i) {
        var okKind = kind === 'all' || (' ' + r.dataset.kind + ' ').indexOf(' ' + kind + ' ') > -1;
        var okText = words.every(function (w) { return texts[i].indexOf(w) > -1; });
        r.hidden = !(okKind && okText);
        if (!r.hidden) { shown++; if (r.tagName === 'LI') talks++; }
      });
      groups.forEach(function (g) { g.hidden = !g.querySelector('[data-record]:not([hidden])'); });
      document.querySelectorAll('#tl-results .sec-head').forEach(function (h) {
        var next = h.nextElementSibling; h.hidden = !!(next && next.hidden);
      });
      var heading = document.getElementById('all-talks');
      if (heading) heading.hidden = talks === 0;
      if (empty) empty.hidden = shown > 0;
      status.textContent = (words.length || kind !== 'all') ? talks + (talks === 1 ? ' talk' : ' talks') + ' match' + (talks === 1 ? 'es' : '') : '';
    };
    q.addEventListener('input', apply);
    kindBtns.forEach(function (b) {
      b.addEventListener('click', function () {
        kind = b.dataset.kind;
        kindBtns.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        apply();
      });
    });
  }

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
    '<figure><img alt=""><figcaption></figcaption></figure><button type="button" class="lb-next" aria-label="Next photo">›</button>';
  document.body.appendChild(box);
  var img = box.querySelector('img'), cap = box.querySelector('figcaption'), idx = 0;
  function show(i) {
    idx = (i + links.length) % links.length;
    var a = links[idx], fig = a.closest('figure'), fc = fig && fig.querySelector('figcaption');
    img.src = a.href; img.alt = a.querySelector('img').alt;
    var t = fc ? Array.prototype.map.call(fc.querySelectorAll('strong, span:not(.credit)'), function (n) { return n.textContent; }).join(' — ') : img.alt;
    cap.textContent = t;
  }
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
