function toggleNav() {
  document.querySelector('nav').classList.toggle('open');
}

document.addEventListener('click', function (e) {
  if (!e.target.closest('header')) {
    var nav = document.querySelector('nav');
    if (nav) nav.classList.remove('open');
    document.querySelectorAll('.user-menu').forEach(function(m) {
      m.classList.remove('open');
    });
  }
});

// User menu toggle for touch devices
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.user-menu-name').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.stopPropagation();
      var menu = el.closest('.user-menu');
      menu.classList.toggle('open');
    });
  });
});

// Inject user-menu styles
(function () {
  var style = document.createElement('style');
  style.textContent = [
    '.user-menu{position:relative;}',
    '.user-menu-name{color:#FBF3E4;font-size:1rem;padding:0.5em 1.25em;background-color:#A8C256;border-radius:1.875em;cursor:pointer;font-family:Georgia,serif;display:inline-block;user-select:none;}',
    '.user-dropdown{display:none;position:absolute;top:calc(100% + 0.5em);right:0;background:#fff;border-radius:0.5em;box-shadow:0 0.25em 1em rgba(0,0,0,0.18);min-width:10em;z-index:500;overflow:hidden;}',
    '.user-menu:hover .user-dropdown,.user-menu.open .user-dropdown{display:block;}',
    '.user-dropdown a{display:block;padding:0.65em 1.1em;color:#9B1C35;text-decoration:none;font-size:0.9rem;font-family:Georgia,serif;}',
    '.user-dropdown a+a{border-top:1px solid rgba(155,28,53,0.1);}',
    '.user-dropdown a:hover{background:#FBF3E4;color:#9B1C35;}'
  ].join('');
  document.head.appendChild(style);
})();
