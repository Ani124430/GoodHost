function moveCarousel(id, dir) {
  const carousel = document.getElementById(id);
  const imgs = carousel.querySelectorAll('.carousel-img');
  const dots = carousel.querySelectorAll('.dot');
  let current = [...imgs].findIndex(img => !img.classList.contains('hidden'));
  imgs[current].classList.add('hidden');
  if (dots.length) dots[current].classList.remove('active');
  current = (current + dir + imgs.length) % imgs.length;
  imgs[current].classList.remove('hidden');
  if (dots.length) dots[current].classList.add('active');
}

function goToSlide(id, index) {
  const carousel = document.getElementById(id);
  const imgs = carousel.querySelectorAll('.carousel-img');
  const dots = carousel.querySelectorAll('.dot');
  imgs.forEach((img, i) => img.classList.toggle('hidden', i !== index));
  dots.forEach((dot, i) => dot.classList.toggle('active', i === index));
}
