function toggleNav() {
  document.querySelector('nav').classList.toggle('open');
}

document.addEventListener('click', function (e) {
  if (!e.target.closest('header')) {
    var nav = document.querySelector('nav');
    if (nav) nav.classList.remove('open');
  }
});
