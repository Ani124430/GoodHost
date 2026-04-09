function toggleRequestForm(hostId) {
  var el = document.getElementById('req-form-' + hostId);
  el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function openReviewsModal(hostId, hostName) {
  const modal = document.getElementById('reviews-modal');
  const title = document.getElementById('reviews-modal-title');
  const body  = document.getElementById('reviews-modal-body');
  title.textContent = 'Отзиви за ' + hostName;
  body.innerHTML = '<p style="opacity:0.5;text-align:center;">Зареждане...</p>';
  modal.style.display = 'flex';
  fetch('/hosts/' + hostId + '/reviews')
    .then(r => r.json())
    .then(reviews => {
      if (!reviews.length) {
        body.innerHTML = '<p style="opacity:0.55;text-align:center;">Все още няма отзиви.</p>';
        return;
      }
      body.innerHTML = reviews.map(r => {
        const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
        const comment = r.comment ? '<p class="review-comment">' + r.comment + '</p>' : '';
        return '<div class="review-item">' +
          '<div class="review-header">' +
            '<span class="review-stars">' + stars + '</span>' +
            '<span class="review-author">' + r.volunteer_name + '</span>' +
            '<span class="review-date">' + r.created_at + '</span>' +
          '</div>' + comment +
        '</div>';
      }).join('');
    });
}
function closeReviewsModal(e) {
  if (e.target === document.getElementById('reviews-modal')) {
    document.getElementById('reviews-modal').style.display = 'none';
  }
}
