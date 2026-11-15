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

  // Search and format filter on the Speaking page
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

// Mobile menu: slide-in panel
(function () {
  var nav = document.querySelector('.site-nav'); if (!nav) return;
  var btn = nav.querySelector('.menu-btn'), close = nav.querySelector('.menu-close'), scrim = nav.querySelector('.menu-scrim');
  if (!btn) return;
  function set(open) {
    nav.classList.toggle('menu-open', open);
    document.body.classList.toggle('menu-locked', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    scrim.hidden = !open;
    if (open) { close.focus(); } else { btn.focus(); }
  }
  btn.addEventListener('click', function () { set(true); });
  close.addEventListener('click', function () { set(false); });
  scrim.addEventListener('click', function () { set(false); });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && nav.classList.contains('menu-open')) set(false); });
})();

// The AI Stack: build-in on scroll, service highlighting, request trace
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function onView(el, fn) {
    if (!el) return;
    if (!('IntersectionObserver' in window)) { fn(); return; }
    var io = new IntersectionObserver(function (es) { es.forEach(function (x) { if (x.isIntersecting) { fn(); io.disconnect(); } }); }, { threshold: 0.2 });
    io.observe(el);
  }
  var viz = document.querySelector('.stackviz');
  if (viz) {
    var layers = viz.querySelectorAll('.layer'), chips = document.querySelectorAll('.svc-chip'), brackets = viz.querySelectorAll('.bracket');
    var timer = null, cur = -1;
    function show(svc) {
      cur = svc;
      var from = svc < 0 ? null : +chips[svc].getAttribute('data-from');
      viz.classList.toggle('has-active', svc >= 0);
      layers.forEach(function (l) { l.classList.toggle('lit', from !== null && +l.getAttribute('data-i') >= from); });
      chips.forEach(function (c, i) { c.classList.toggle('on', i === svc); c.setAttribute('aria-pressed', i === svc ? 'true' : 'false'); });
      brackets.forEach(function (b) { b.classList.toggle('on', +b.getAttribute('data-svc') === svc); });
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function pick(svc) { stop(); show(cur === svc ? -1 : svc); }
    chips.forEach(function (c) { c.addEventListener('click', function () { pick(+c.getAttribute('data-svc')); }); });
    brackets.forEach(function (b) { b.addEventListener('click', function () { pick(+b.getAttribute('data-svc')); }); });
    onView(viz, function () {
      viz.classList.add('in');
      if (reduce) return;
      var i = 0;
      setTimeout(function () {
        if (cur !== -1) return;
        show(0);
        timer = setInterval(function () { i++; if (i >= chips.length) { stop(); show(-1); return; } show(i); }, 1800);
      }, 1200);
    });
  }
  var scale = document.querySelector('.scale');
  onView(scale, function () { scale.classList.add('in'); });

  var arch = document.querySelector('.arch');
  if (arch) {
    var trace = arch.querySelector('[data-trace]');
    var words = [
      'A request arrives from an app, through the operator network and the security edge.',
      'The AI gateway checks the API key, applies quotas and meters every token.',
      'Guardrails check the prompt on the way in and the response on the way out.',
      'A model runtime picks up the request on the GPU cluster.',
      'GPU workers generate the tokens, talking over the 800G east-west fabric.',
      'Models and data stream from parallel storage over the north-south network.'
    ];
    var step = -1, t = null;
    function go() {
      step = (step + 1) % words.length;
      arch.querySelectorAll('.on').forEach(function (x) { x.classList.remove('on'); });
      arch.querySelectorAll('[data-step="' + step + '"]').forEach(function (x) { x.classList.add('on'); });
      trace.textContent = words[step];
    }
    if (!reduce) onView(arch, function () { go(); t = setInterval(go, 2600); });
  }
})();
