/* Classroom Python - student page.  ES5 only (Android 4.2 browsers).
 *
 * Two ways to run a program, chosen by the teacher on the Pi (see admin.html):
 *   "client" - Skulpt runs the Python inside this tablet's browser
 *   "server" - the code is sent to the Pi, which runs real CPython and sends output back
 * Add ?mode=client or ?mode=server to the address to force one for testing.
 */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var els = {
    run: $('run'), stop: $('stop'), clear: $('clear'), colours: $('colours'), status: $('status'),
    notice: $('notice'), wrap: $('editorwrap'), code: $('code'), out: $('out'),
    inputrow: $('inputrow'), stdin: $('stdin'), bar: $('bar')
  };

  // ---------- small helpers ----------
  function store(key, val) {
    try {
      if (val === undefined) { return window.localStorage.getItem(key); }
      window.localStorage.setItem(key, val);
    } catch (e) { /* private mode / storage full */ }
    return null;
  }

  function xhr(method, url, body, cb, timeout) {
    var r = new XMLHttpRequest();
    var finished = false;
    function done(status, data) {
      if (finished) { return; }
      finished = true;
      cb(status, data);
    }
    try {
      r.open(method, url, true);
      r.timeout = timeout || 8000;
      r.onreadystatechange = function () {
        if (r.readyState !== 4) { return; }
        var data = null;
        try { data = JSON.parse(r.responseText); } catch (e) { data = null; }
        done(r.status, data);
      };
      r.ontimeout = function () { done(0, null); };
      r.onerror = function () { done(0, null); };
      if (body !== null && body !== undefined) {
        r.setRequestHeader('Content-Type', 'application/json');
        r.send(JSON.stringify(body));
      } else {
        r.send();
      }
    } catch (e) { done(0, null); }
  }

  var clientId = store('cp.client');
  if (!clientId) {
    clientId = String(new Date().getTime()) + '-' + Math.floor(Math.random() * 1e9);
    store('cp.client', clientId);
  }

  // ---------- editor (plain textarea, optionally CodeMirror for colours) ----------
  var cm = null;
  var DEFAULT_CODE = 'name = input("What is your name? ")\nprint("Hello, " + name)\n';
  els.code.value = store('cp.code') || DEFAULT_CODE;

  function getCode() { return cm ? cm.getValue() : els.code.value; }
  function setCode(v) { if (cm) { cm.setValue(v); } else { els.code.value = v; } }

  var saveTimer = null;
  function scheduleSave() {
    if (saveTimer) { clearTimeout(saveTimer); }
    saveTimer = setTimeout(function () { store('cp.code', getCode()); }, 400);
  }
  els.code.onkeyup = els.code.oninput = els.code.onchange = scheduleSave;

  function setColours(on) {
    var h = els.code.style.height;
    if (on && !cm && window.CodeMirror) {
      cm = window.CodeMirror.fromTextArea(els.code, {
        mode: 'python', lineNumbers: true, indentUnit: 4, indentWithTabs: false, smartIndent: true,
        extraKeys: { Tab: function (c) { c.replaceSelection('    ', 'end'); } }
      });
      cm.on('change', scheduleSave);
    } else if (!on && cm) {
      cm.toTextArea();
      cm = null;
      els.code.onkeyup = els.code.oninput = els.code.onchange = scheduleSave;
    }
    els.code.style.height = h;
    els.colours.innerHTML = 'Colours: ' + (cm ? 'on' : 'off');
    store('cp.colours', cm ? '1' : '0');
    layout();
  }
  els.colours.onclick = function () { setColours(!cm); };

  // ---------- layout (no flexbox/calc on old Android) ----------
  function layout() {
    var total = window.innerHeight || document.documentElement.clientHeight;
    var used = els.bar.offsetHeight + (els.notice.style.display === 'block' ? els.notice.offsetHeight : 0) +
      (els.inputrow.style.display === 'block' ? els.inputrow.offsetHeight : 0) + 2;
    var avail = Math.max(total - used, 200);
    var editorH = Math.floor(avail * 0.5);
    var outH = avail - editorH;
    els.wrap.style.height = editorH + 'px';
    if (cm) { cm.setSize('100%', editorH); } else { els.code.style.height = editorH + 'px'; }
    els.out.style.height = outH + 'px';
    if (cm) { cm.refresh(); }
  }
  window.onresize = window.onorientationchange = function () { setTimeout(layout, 150); };

  // ---------- output ----------
  function write(text, cls) {
    if (!text) { return; }
    var node;
    if (cls) {
      node = document.createElement('span');
      node.className = cls;
      node.appendChild(document.createTextNode(text));
    } else {
      node = document.createTextNode(text);
    }
    els.out.appendChild(node);
    els.out.scrollTop = els.out.scrollHeight;
  }
  function clearOut() { els.out.innerHTML = ''; }
  els.clear.onclick = clearOut;

  function showNotice(msg) {
    els.notice.style.display = msg ? 'block' : 'none';
    els.notice.innerHTML = '';
    if (msg) { els.notice.appendChild(document.createTextNode(msg)); }
    layout();
  }

  // ---------- mode (set by the teacher on the Pi) ----------
  var forced = (/[?&]mode=(client|server)/.exec(window.location.search) || [])[1] || null;
  var teacherMode = forced || 'client';
  var skulptOk = (typeof window.Sk !== 'undefined') && !!window.Sk.python3;

  function effectiveMode() {
    if (teacherMode === 'client' && !skulptOk) { return 'server'; }
    return teacherMode;
  }

  function updateStatus() {
    var m = effectiveMode();
    var text = m === 'server' ? 'Running on the Pi' : 'Running on this tablet';
    if (running) { text = 'Running...'; }
    els.status.innerHTML = '';
    els.status.appendChild(document.createTextNode(text));
    if (teacherMode === 'client' && !skulptOk) {
      showNotice('This tablet cannot run Python by itself, so your programs run on the Pi instead.');
    } else if (forced) {
      showNotice('Test mode: ' + forced + ' (set in the address). Remove ?mode= to follow the teacher.');
    } else {
      showNotice('');
    }
  }

  function pollConfig() {
    xhr('GET', 'api/config', null, function (status, data) {
      if (status === 200 && data && !forced && (data.mode === 'client' || data.mode === 'server')) {
        teacherMode = data.mode;
      }
      if (!running) { updateStatus(); }
      setTimeout(pollConfig, 5000);
    }, 4000);
  }

  // ---------- running ----------
  var running = false;
  var current = null; // {stop: function, send: function(text)}
  var awaitingInput = false;

  function setRunning(on) {
    running = on;
    els.run.disabled = on;
    els.stop.disabled = !on;
    if (!on) { showInput(false); }
    updateStatus();
  }

  function showInput(on) {
    awaitingInput = on;
    els.inputrow.style.display = on ? 'block' : 'none';
    layout();
    if (on) {
      els.stdin.value = '';
      try { els.stdin.focus(); } catch (e) { /* ignore */ }
    }
  }

  function submitInput() {
    var text = els.stdin.value;
    els.stdin.value = '';
    write(text + '\n', 'echo');
    if (current && current.send) { current.send(text); }
    return false;
  }
  $('inputrow').onsubmit = submitInput;
  $('send').onclick = function (e) { if (e && e.preventDefault) { e.preventDefault(); } submitInput(); return false; };

  els.run.onclick = function () {
    if (running) { return; }
    var code = getCode();
    store('cp.code', code);
    clearOut();
    setRunning(true);
    if (effectiveMode() === 'server') { runOnServer(code); } else { runInBrowser(code); }
  };
  els.stop.onclick = function () { if (current && current.stop) { current.stop(); } };

  function finish(note, cls) {
    if (note) { write((els.out.lastChild && !/\n$/.test(els.out.textContent) ? '\n' : '') + note + '\n', cls); }
    current = null;
    setRunning(false);
  }

  // --- A: Skulpt in the browser ---
  function runInBrowser(code) {
    var Sk = window.Sk;
    var stopped = false;
    var pendingInput = null; // {resolve, waitStart}
    var limitMs = 15000;

    current = {
      stop: function () {
        stopped = true;
        Sk.execLimit = 0; // makes the interpreter raise TimeLimitError at its next check
        if (pendingInput) { var p = pendingInput; pendingInput = null; p.resolve(''); }
      },
      send: function (text) {
        if (pendingInput) {
          var p = pendingInput;
          pendingInput = null;
          // time spent waiting for the student must not count towards the loop limit
          Sk.execStart = new Date(Sk.execStart.getTime() + (new Date().getTime() - p.waitStart));
          showInput(false);
          p.resolve(text);
        }
      }
    };

    Sk.configure({
      output: function (t) { write(t); },
      read: function (x) {
        if (Sk.builtinFiles === undefined || Sk.builtinFiles.files[x] === undefined) {
          throw "File not found: '" + x + "'";
        }
        return Sk.builtinFiles.files[x];
      },
      __future__: Sk.python3,
      inputfunTakesPrompt: true,
      inputfun: function (prompt) {
        write(prompt || '');
        return new Promise(function (resolve) {
          pendingInput = { resolve: resolve, waitStart: new Date().getTime() };
          showInput(true);
        });
      },
      execLimit: limitMs,
      yieldLimit: 100
    });
    delete Sk.execStart;

    var p = Sk.misceval.asyncToPromise(function () {
      return Sk.importMainWithBody('<stdin>', false, code, true);
    });
    p.then(function () {
      finish(stopped ? '[Stopped]' : null, 'note');
    }, function (e) {
      if (stopped) { finish('[Stopped]', 'note'); return; }
      var msg = String(e);
      if (/TimeLimitError/.test(msg)) {
        finish('[Stopped: the program ran for more than ' + (limitMs / 1000) +
          ' seconds. Is there an endless loop?]', 'note');
        return;
      }
      if (/SyntaxError/.test(msg) && /(^|[^\w])[fF]["']/.test(code)) {
        msg += '\n(Hint: f"..." strings are not supported when running on the tablet. ' +
          'Use "..." + str(x) or "{}".format(x), or ask your teacher to switch to Pi mode.)';
      }
      finish(msg, 'err');
    });
  }

  // --- B: real CPython on the Pi ---
  function runOnServer(code) {
    var sid = null;
    var pos = 0;
    var stopped = false;
    var failures = 0;
    var ended = false;

    current = {
      stop: function () {
        stopped = true;
        if (sid) { xhr('POST', 'api/kill', { id: sid }, function () { /* poll reports it */ }); }
      },
      send: function (text) {
        if (sid) { xhr('POST', 'api/stdin', { id: sid, text: text + '\n' }, function () { }); }
      }
    };

    function lost() {
      if (ended) { return; }
      ended = true;
      finish('[Lost the connection to the Pi. Check the Wi-Fi and try again.]', 'err');
    }

    function poll() {
      if (ended) { return; }
      xhr('GET', 'api/poll?id=' + encodeURIComponent(sid) + '&pos=' + pos, null, function (status, d) {
        if (ended) { return; }
        if (status !== 200 || !d) {
          failures += 1;
          if (failures >= 6) { lost(); } else { setTimeout(poll, 500); }
          return;
        }
        failures = 0;
        if (d.out) { write(d.out); pos = d.pos; }
        if (d.done) {
          ended = true;
          finish(null);
          return;
        }
        setTimeout(poll, 250);
      }, 5000);
    }

    xhr('POST', 'api/run', { client: clientId, code: code }, function (status, d) {
      if (status === 503) {
        ended = true;
        finish('[The Pi is busy right now. Wait a moment and press Run again.]', 'note');
        return;
      }
      if (status !== 200 || !d || !d.id) { lost(); return; }
      sid = d.id;
      showInput(true); // a program on the Pi may ask for input at any time
      if (stopped) { xhr('POST', 'api/kill', { id: sid }, function () { }); }
      poll();
    }, 8000);
  }

  // ---------- go ----------
  setColours(store('cp.colours') === '1');
  layout();
  updateStatus();
  pollConfig();
}());
