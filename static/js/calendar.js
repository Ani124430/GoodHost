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
var volCal = { hostId: null, hostName: '', year: 0, month: 0, busy: new Set() };

function openCalendarModal(hostId, hostName) {
  var now = new Date();
  volCal.hostId = hostId;
  volCal.hostName = hostName;
  volCal.year  = now.getFullYear();
  volCal.month = now.getMonth() + 1;
  document.getElementById('cal-modal-title').textContent = 'Наличност: ' + hostName;
  document.getElementById('cal-modal').style.display = 'flex';
  fetchAndDrawVolCal();
}

function closeCalendarModal(e) {
  if (!e || e.target === document.getElementById('cal-modal')) {
    document.getElementById('cal-modal').style.display = 'none';
  }
}

function volCalChangeMonth(delta) {
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
      document.getElementById('cal-action').innerHTML = '';
    });
}

function selectVolDay(dateStr, isPastOrToday) {
  document.querySelectorAll('#vol-cal-grid .cal-cell.selected').forEach(function (el) { el.classList.remove('selected'); });
  var cell = document.querySelector('#vol-cal-grid [data-date="' + dateStr + '"]');
  if (cell) cell.classList.add('selected');
  var p = dateStr.split('-');
  var disp = parseInt(p[2]) + '.' + parseInt(p[1]) + '.' + p[0];
  var action = document.getElementById('cal-action');
  if (isPastOrToday) {
    action.innerHTML =
      '<p class="cal-sel-info">Избрана дата: <strong>' + disp + '</strong></p>' +
      '<form method="POST" action="/hosts/' + volCal.hostId + '/visited">' +
        '<button type="submit" class="cal-btn cal-btn-visited">✓ Посетих на ' + disp + '</button>' +
      '</form>';
  } else {
    action.innerHTML =
      '<p class="cal-sel-info">Избрана дата: <strong>' + disp + '</strong></p>' +
      '<form method="POST" action="/hosts/' + volCal.hostId + '/plan-visit">' +
        '<input type="hidden" name="date" value="' + dateStr + '">' +
        '<button type="submit" class="cal-btn cal-btn-plan">📅 Ще посетя на ' + disp + '</button>' +
      '</form>';
  }
}

// ===================== HOST PROFILE CALENDAR =====================
var hostCal = { hostId: null, year: 0, month: 0, busy: new Set() };

function initHostCal(hostId) {
  var now = new Date();
  hostCal.hostId = hostId;
  hostCal.year  = now.getFullYear();
  hostCal.month = now.getMonth() + 1;
  fetchAndDrawHostCal();
}

function hostCalChangeMonth(delta) {
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
      drawCal('host-cal-label', 'host-cal-grid', hostCal.year, hostCal.month, hostCal.busy, toggleHostDay, true);
    });
}

function toggleHostDay(dateStr) {
  fetch('/hosts/' + hostCal.hostId + '/busy-days/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'date=' + dateStr
  })
  .then(function (r) { return r.json(); })
  .then(function (data) {
    var cell = document.querySelector('#host-cal-grid [data-date="' + dateStr + '"]');
    if (!cell) return;
    if (data.status === 'added') {
      cell.classList.add('cal-busy');
      hostCal.busy.add(dateStr);
    } else {
      cell.classList.remove('cal-busy');
      hostCal.busy.delete(dateStr);
    }
  });
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
