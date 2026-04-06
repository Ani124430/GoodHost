// ===================== CSS INJECTION =====================
(function () {
  var s = document.createElement('style');
  s.textContent = [
    // Shared calendar widget
    '.mini-cal{background:#fff;border-radius:0.75em;border:1px solid rgba(155,28,53,0.12);padding:1em;max-width:22em;}',
    '.mini-cal-nav{display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75em;}',
    '.mini-cal-nav button{background:none;border:1px solid rgba(155,28,53,0.25);color:#9B1C35;border-radius:50%;width:1.8em;height:1.8em;font-size:1rem;cursor:pointer;line-height:1;display:flex;align-items:center;justify-content:center;}',
    '.mini-cal-nav button:hover{background:rgba(155,28,53,0.08);}',
    '.mini-cal-nav span{font-weight:bold;font-size:0.95rem;color:#9B1C35;}',
    '.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:0.2em;}',
    '.cal-hdr{text-align:center;font-size:0.7rem;font-weight:bold;color:#9B1C35;opacity:0.5;padding:0.2em 0;}',
    '.cal-cell{text-align:center;padding:0.35em 0.1em;font-size:0.82rem;border-radius:0.3em;cursor:pointer;color:#9B1C35;transition:background 0.15s;}',
    '.cal-cell.empty{cursor:default;}',
    '.cal-cell.cal-busy{background:#f8d7da;color:#721c24;cursor:default;font-weight:bold;}',
    '.cal-cell.cal-today{font-weight:bold;outline:2px solid #9B1C35;outline-offset:-2px;}',
    '.cal-cell.cal-past{opacity:0.55;}',
    '.cal-cell:not(.cal-busy):not(.empty):hover{background:rgba(168,194,86,0.25);}',
    '.cal-cell.selected{background:#A8C256;color:#fff;font-weight:bold;}',
    '.cal-cell.cal-range{background:rgba(168,194,86,0.25);}',
    '.cal-cell.cal-range-end{background:#A8C256;color:#fff;font-weight:bold;}',
    // Legend
    '.cal-legend{display:flex;gap:0.8em;margin-top:0.5em;font-size:0.72rem;color:#9B1C35;opacity:0.7;}',
    '.cal-legend-dot{width:0.7em;height:0.7em;border-radius:50%;display:inline-block;margin-right:0.25em;}',
    // Action area
    '.cal-action{margin-top:0.75em;}',
    '.cal-sel-info{font-size:0.82rem;color:#9B1C35;opacity:0.7;margin-bottom:0.4em;}',
    '.cal-btn{border:none;border-radius:1.5em;padding:0.5em 1.2em;font-size:0.85rem;font-family:Georgia,serif;cursor:pointer;font-weight:bold;width:100%;}',
    '.cal-btn-visited{background:#9B1C35;color:#FBF3E4;}',
    '.cal-btn-visited:hover{background:#7a1228;}',
    '.cal-btn-plan{background:#A8C256;color:#fff;}',
    '.cal-btn-plan:hover{background:#8faa3e;}',
    // Volunteer calendar modal
    '#cal-modal .modal-box{max-width:26em;width:95%;text-align:left;}',
    '#cal-modal .reviews-modal-title{margin-bottom:0.75em;}',
    // Host calendar section in profile
    '.host-cal-section{margin-top:1.5em;}',
    '.host-cal-note{font-size:0.78rem;color:#9B1C35;opacity:0.55;margin-bottom:0.6em;}',
    // Availability badge on host card
    '.avail-label{font-size:0.78rem;display:inline-block;margin-top:0.15em;}',
    '.avail-free{color:#A8C256;}',
    '.avail-from{color:#9B1C35;opacity:0.75;}',
    // Calendar open button in card-extra
    '.cal-link-btn{background:none;border:1px solid rgba(155,28,53,0.3);color:#9B1C35;border-radius:1em;padding:0.3em 0.8em;font-size:0.8rem;font-family:Georgia,serif;cursor:pointer;margin-top:0.25em;}',
    '.cal-link-btn:hover{background:rgba(155,28,53,0.07);}',
  ].join('');
  document.head.appendChild(s);
})();

// ===================== VOLUNTEER CALENDAR MODAL =====================
var volCal = { hostId: null, hostName: '', maxGuests: 1, year: 0, month: 0, busy: new Set(), rangeStart: null };

function openCalendarModal(hostId, hostName, maxGuests) {
  var now = new Date();
  volCal.hostId = hostId;
  volCal.hostName = hostName;
  volCal.maxGuests = maxGuests || 1;
  volCal.year  = now.getFullYear();
  volCal.month = now.getMonth() + 1;
  volCal.rangeStart = null;
  document.getElementById('cal-modal-title').textContent = 'График на ' + hostName;
  document.getElementById('cal-modal').style.display = 'flex';
  fetchAndDrawVolCal();
}

function buildGuestsSelect() {
  var opts = '';
  for (var i = 1; i <= volCal.maxGuests; i++) {
    opts += '<option value="' + i + '">' + i + (i === 1 ? ' (само аз)' : '') + '</option>';
  }
  return '<label style="font-size:0.8rem;color:#9B1C35;display:block;margin:0.4em 0;">Брой гости ' +
    '<select name="num_guests" style="font-size:0.82rem;border:1px solid rgba(155,28,53,0.3);border-radius:0.3em;padding:0.2em 0.4em;margin-left:0.3em;">' +
    opts + '</select></label>';
}

function closeCalendarModal(e) {
  if (!e || e.target === document.getElementById('cal-modal')) {
    document.getElementById('cal-modal').style.display = 'none';
  }
}

function volCalChangeMonth(delta) {
  volCal.rangeStart = null;
  volCal.month += delta;
  if (volCal.month > 12) { volCal.month = 1; volCal.year++; }
  if (volCal.month < 1)  { volCal.month = 12; volCal.year--; }
  fetchAndDrawVolCal();
}

function fetchAndDrawVolCal() {
  fetch('/hosts/' + volCal.hostId + '/busy-days?year=' + volCal.year + '&month=' + volCal.month)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      volCal.busy = new Set(data.busy_days);
      drawCal('vol-cal-label', 'vol-cal-grid', volCal.year, volCal.month, volCal.busy, selectVolDay, false);
      updateVolCalAction();
    });
}

function clearVolRangeHighlight() {
  document.querySelectorAll('#vol-cal-grid .cal-cell').forEach(function (c) {
    c.classList.remove('selected', 'cal-range', 'cal-range-end');
  });
}

function highlightVolRange(from, to) {
  clearVolRangeHighlight();
  var fromDate = new Date(from), toDate = new Date(to);
  if (fromDate > toDate) { var tmp = fromDate; fromDate = toDate; toDate = tmp; }
  document.querySelectorAll('#vol-cal-grid .cal-cell[data-date]').forEach(function (c) {
    var d = new Date(c.dataset.date);
    if (d.getTime() === fromDate.getTime()) { c.classList.add('selected'); }
    else if (d.getTime() === toDate.getTime()) { c.classList.add('cal-range-end'); }
    else if (d > fromDate && d < toDate) { c.classList.add('cal-range'); }
  });
}

function updateVolCalAction() {
  var action = document.getElementById('cal-action');
  if (!action) return;
  if (!volCal.rangeStart) {
    action.innerHTML = '<p class="host-cal-note">Натисни ден за начало на периода, после избери краен ден.</p>';
    return;
  }
  action.innerHTML =
    '<p class="cal-sel-info">От: <strong>' + fmtDisp(volCal.rangeStart) + '</strong> — избери краен ден от календара</p>' +
    '<button onclick="clearVolRange()" style="background:none;border:1px solid rgba(155,28,53,0.3);color:#9B1C35;border-radius:1em;padding:0.25em 0.8em;font-size:0.8rem;font-family:Georgia,serif;cursor:pointer;margin-top:0.3em;">Откажи</button>';
}

function clearVolRange() {
  volCal.rangeStart = null;
  clearVolRangeHighlight();
  updateVolCalAction();
}

function showVolRangeConfirm(from, to) {
  if (new Date(from) > new Date(to)) { var tmp = from; from = to; to = tmp; }
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var endDate = new Date(to);
  var isPast = endDate <= today;
  var action = document.getElementById('cal-action');
  if (isPast) {
    action.innerHTML =
      '<p class="cal-sel-info">Период: <strong>' + fmtDisp(from) + ' — ' + fmtDisp(to) + '</strong></p>' +
      '<div style="display:flex;gap:0.5em;margin-top:0.4em;">' +
        '<form method="POST" action="/hosts/' + volCal.hostId + '/visited">' +
          '<input type="hidden" name="from_date" value="' + from + '">' +
          '<input type="hidden" name="to_date" value="' + to + '">' +
          '<button type="submit" class="cal-btn cal-btn-visited" style="width:auto;padding:0.45em 1.1em;">✓ Посетих от ' + fmtDisp(from) + ' до ' + fmtDisp(to) + '</button>' +
        '</form>' +
        '<button onclick="clearVolRange()" style="background:none;border:1px solid #999;color:#666;border-radius:1.5em;padding:0.45em 0.9em;font-size:0.85rem;font-family:Georgia,serif;cursor:pointer;">Откажи</button>' +
      '</div>';
  } else {
    action.innerHTML =
      '<p class="cal-sel-info">Период: <strong>' + fmtDisp(from) + ' — ' + fmtDisp(to) + '</strong></p>' +
      '<form method="POST" action="/hosts/' + volCal.hostId + '/request-visit" style="margin-top:0.4em;">' +
        '<input type="hidden" name="from_date" value="' + from + '">' +
        '<input type="hidden" name="to_date" value="' + to + '">' +
        buildGuestsSelect() +
        '<textarea name="message" rows="2" placeholder="Кажи нещо за себе си (по желание)..." style="width:100%;box-sizing:border-box;font-size:0.82rem;border:1px solid rgba(155,28,53,0.25);border-radius:0.3em;padding:0.4em 0.5em;resize:vertical;font-family:Georgia,serif;margin-bottom:0.4em;"></textarea>' +
        '<div style="display:flex;gap:0.5em;">' +
          '<button type="submit" class="cal-btn cal-btn-plan" style="width:auto;padding:0.45em 1.1em;">📅 Заяви посещение</button>' +
          '<button type="button" onclick="clearVolRange()" style="background:none;border:1px solid #999;color:#666;border-radius:1.5em;padding:0.45em 0.9em;font-size:0.85rem;font-family:Georgia,serif;cursor:pointer;">Откажи</button>' +
        '</div>' +
      '</form>';
  }
}

function selectVolDay(dateStr, isPastOrToday) {
  if (volCal.busy.has(dateStr)) return;

  if (!volCal.rangeStart) {
    volCal.rangeStart = dateStr;
    clearVolRangeHighlight();
    var cell = document.querySelector('#vol-cal-grid [data-date="' + dateStr + '"]');
    if (cell) cell.classList.add('selected');
    updateVolCalAction();
  } else if (volCal.rangeStart === dateStr) {
    // single day confirm
    var disp = fmtDisp(dateStr);
    var action = document.getElementById('cal-action');
    if (isPastOrToday) {
      action.innerHTML =
        '<p class="cal-sel-info">Избрана дата: <strong>' + disp + '</strong></p>' +
        '<div style="display:flex;gap:0.5em;margin-top:0.4em;">' +
          '<form method="POST" action="/hosts/' + volCal.hostId + '/visited">' +
            '<input type="hidden" name="from_date" value="' + dateStr + '">' +
            '<input type="hidden" name="to_date" value="' + dateStr + '">' +
            '<button type="submit" class="cal-btn cal-btn-visited" style="width:auto;padding:0.45em 1.1em;">✓ Посетих на ' + disp + '</button>' +
          '</form>' +
          '<button onclick="clearVolRange()" style="background:none;border:1px solid #999;color:#666;border-radius:1.5em;padding:0.45em 0.9em;font-size:0.85rem;font-family:Georgia,serif;cursor:pointer;">Откажи</button>' +
        '</div>';
    } else {
      action.innerHTML =
        '<p class="cal-sel-info">Избрана дата: <strong>' + disp + '</strong></p>' +
        '<form method="POST" action="/hosts/' + volCal.hostId + '/request-visit" style="margin-top:0.4em;">' +
          '<input type="hidden" name="from_date" value="' + dateStr + '">' +
          '<input type="hidden" name="to_date" value="' + dateStr + '">' +
          buildGuestsSelect() +
          '<textarea name="message" rows="2" placeholder="Кажи нещо за себе си (по желание)..." style="width:100%;box-sizing:border-box;font-size:0.82rem;border:1px solid rgba(155,28,53,0.25);border-radius:0.3em;padding:0.4em 0.5em;resize:vertical;font-family:Georgia,serif;margin-bottom:0.4em;"></textarea>' +
          '<div style="display:flex;gap:0.5em;">' +
            '<button type="submit" class="cal-btn cal-btn-plan" style="width:auto;padding:0.45em 1.1em;">📅 Заяви посещение</button>' +
            '<button type="button" onclick="clearVolRange()" style="background:none;border:1px solid #999;color:#666;border-radius:1.5em;padding:0.45em 0.9em;font-size:0.85rem;font-family:Georgia,serif;cursor:pointer;">Откажи</button>' +
          '</div>' +
        '</form>';
    }
    volCal.rangeStart = null;
  } else {
    highlightVolRange(volCal.rangeStart, dateStr);
    showVolRangeConfirm(volCal.rangeStart, dateStr);
    volCal.rangeStart = null;
  }
}

// ===================== HOST PROFILE CALENDAR =====================
var hostCal = { hostId: null, year: 0, month: 0, busy: new Set(), rangeStart: null };

function initHostCal(hostId) {
  var now = new Date();
  hostCal.hostId = hostId;
  hostCal.year  = now.getFullYear();
  hostCal.month = now.getMonth() + 1;
  fetchAndDrawHostCal();
}

function hostCalChangeMonth(delta) {
  hostCal.rangeStart = null;
  hostCal.month += delta;
  if (hostCal.month > 12) { hostCal.month = 1; hostCal.year++; }
  if (hostCal.month < 1)  { hostCal.month = 12; hostCal.year--; }
  fetchAndDrawHostCal();
}

function fetchAndDrawHostCal() {
  fetch('/hosts/' + hostCal.hostId + '/busy-days?year=' + hostCal.year + '&month=' + hostCal.month)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      hostCal.busy = new Set(data.busy_days);
      drawCal('host-cal-label', 'host-cal-grid', hostCal.year, hostCal.month, hostCal.busy, onHostDayClick, true);
      updateHostCalAction();
    });
}

function fmtDisp(dateStr) {
  var p = dateStr.split('-');
  return parseInt(p[2]) + '.' + parseInt(p[1]) + '.' + p[0];
}

function clearHostRangeHighlight() {
  document.querySelectorAll('#host-cal-grid .cal-cell').forEach(function (c) {
    c.classList.remove('selected', 'cal-range', 'cal-range-end');
  });
}

function highlightRange(from, to) {
  clearHostRangeHighlight();
  var fromDate = new Date(from), toDate = new Date(to);
  if (fromDate > toDate) { var tmp = fromDate; fromDate = toDate; toDate = tmp; }
  document.querySelectorAll('#host-cal-grid .cal-cell[data-date]').forEach(function (c) {
    var d = new Date(c.dataset.date);
    if (d.getTime() === fromDate.getTime()) { c.classList.add('selected'); }
    else if (d.getTime() === toDate.getTime()) { c.classList.add('cal-range-end'); }
    else if (d > fromDate && d < toDate) { c.classList.add('cal-range'); }
  });
}

function updateHostCalAction() {
  var action = document.getElementById('host-cal-action');
  if (!action) return;
  if (!hostCal.rangeStart) {
    action.innerHTML = '<p class="host-cal-note">Натисни ден за начало на периода, после избери краен ден.</p>';
    return;
  }
  action.innerHTML =
    '<p class="cal-sel-info">От: <strong>' + fmtDisp(hostCal.rangeStart) + '</strong> — избери краен ден от календара</p>' +
    '<button onclick="clearHostRange()" style="background:none;border:1px solid rgba(155,28,53,0.3);color:#9B1C35;border-radius:1em;padding:0.25em 0.8em;font-size:0.8rem;font-family:Georgia,serif;cursor:pointer;margin-top:0.3em;">Откажи</button>';
}

function clearHostRange() {
  hostCal.rangeStart = null;
  clearHostRangeHighlight();
  updateHostCalAction();
}

function showRangeConfirm(from, to) {
  if (new Date(from) > new Date(to)) { var tmp = from; from = to; to = tmp; }
  var action = document.getElementById('host-cal-action');
  action.innerHTML =
    '<p class="cal-sel-info">Период: <strong>' + fmtDisp(from) + ' — ' + fmtDisp(to) + '</strong></p>' +
    '<div style="display:flex;gap:0.5em;margin-top:0.4em;">' +
      '<button onclick="confirmBusyRange(\'' + from + '\',\'' + to + '\')" class="cal-btn cal-btn-visited" style="width:auto;padding:0.45em 1.1em;">Маркирай като заето</button>' +
      '<button onclick="clearHostRange()" style="background:none;border:1px solid #999;color:#666;border-radius:1.5em;padding:0.45em 0.9em;font-size:0.85rem;font-family:Georgia,serif;cursor:pointer;">Откажи</button>' +
    '</div>';
}

function confirmBusyRange(from, to) {
  fetch('/hosts/' + hostCal.hostId + '/busy-days/range', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_date: from, to_date: to })
  })
  .then(function (r) { return r.json(); })
  .then(function () {
    hostCal.rangeStart = null;
    fetchAndDrawHostCal();
  });
}

function onHostDayClick(dateStr) {
  if (hostCal.busy.has(dateStr)) {
    // toggle off single busy day
    fetch('/hosts/' + hostCal.hostId + '/busy-days/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'date=' + dateStr
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var cell = document.querySelector('#host-cal-grid [data-date="' + dateStr + '"]');
      if (cell && data.status === 'removed') {
        cell.classList.remove('cal-busy');
        hostCal.busy.delete(dateStr);
      }
    });
    return;
  }

  if (!hostCal.rangeStart) {
    hostCal.rangeStart = dateStr;
    clearHostRangeHighlight();
    var cell = document.querySelector('#host-cal-grid [data-date="' + dateStr + '"]');
    if (cell) cell.classList.add('selected');
    updateHostCalAction();
  } else if (hostCal.rangeStart === dateStr) {
    clearHostRange();
  } else {
    highlightRange(hostCal.rangeStart, dateStr);
    showRangeConfirm(hostCal.rangeStart, dateStr);
    hostCal.rangeStart = null;
  }
}

// ===================== SHARED DRAW FUNCTION =====================
function drawCal(labelId, gridId, year, month, busySet, onDayClick, isHostMode) {
  var months = ['Януари','Февруари','Март','Април','Май','Юни',
                'Юли','Август','Септември','Октомври','Ноември','Декември'];
  document.getElementById(labelId).textContent = months[month - 1] + ' ' + year;

  var grid = document.getElementById(gridId);
  grid.innerHTML = '';

  ['П','В','С','Ч','П','С','Н'].forEach(function (d) {
    var el = document.createElement('div');
    el.className = 'cal-hdr';
    el.textContent = d;
    grid.appendChild(el);
  });

  var firstDay = new Date(year, month - 1, 1).getDay();
  var daysInMonth = new Date(year, month, 0).getDate();
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var offset = firstDay === 0 ? 6 : firstDay - 1;

  for (var i = 0; i < offset; i++) {
    var empty = document.createElement('div');
    empty.className = 'cal-cell empty';
    grid.appendChild(empty);
  }

  for (var day = 1; day <= daysInMonth; day++) {
    var mm = String(month).padStart(2, '0');
    var dd = String(day).padStart(2, '0');
    var dateStr = year + '-' + mm + '-' + dd;
    var date = new Date(year, month - 1, day);
    var isBusy = busySet.has(dateStr);
    var isPast = date < today;
    var isToday = date.getTime() === today.getTime();

    var el = document.createElement('div');
    el.className = 'cal-cell';
    el.dataset.date = dateStr;
    el.textContent = day;
    if (isBusy)  el.classList.add('cal-busy');
    if (isToday) el.classList.add('cal-today');
    if (isPast)  el.classList.add('cal-past');

    (function (ds, past, today_flag) {
      el.onclick = function () {
        if (isHostMode) {
          onDayClick(ds);
        } else if (!isBusy) {
          onDayClick(ds, past || today_flag);
        }
      };
    })(dateStr, isPast, isToday);

    grid.appendChild(el);
  }
}
