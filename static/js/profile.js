function submitDecline(reqId) {
  var reason = prompt('Причина за отказ (по желание):') || '';
  document.querySelector('.decline-reason-' + reqId).value = reason;
  document.querySelector('.decline-form-' + reqId).submit();
}

function openBioEdit() {
  document.getElementById('bio-display').style.display = 'none';
  document.querySelector('.edit-bio-btn').style.display = 'none';
  document.getElementById('bio-form').style.display = 'block';
  document.getElementById('bio-textarea').focus();
}
function closeBioEdit() {
  document.getElementById('bio-display').style.display = '';
  document.querySelector('.edit-bio-btn').style.display = '';
  document.getElementById('bio-form').style.display = 'none';
}
function openHelpEdit() {
  document.getElementById('help-display').style.display = 'none';
  document.getElementById('edit-help-btn').style.display = 'none';
  document.getElementById('help-form').style.display = 'block';
  document.getElementById('help-textarea').focus();
}
function closeHelpEdit() {
  document.getElementById('help-display').style.display = '';
  document.getElementById('edit-help-btn').style.display = '';
  document.getElementById('help-form').style.display = 'none';
}

document.querySelectorAll('.gallery-img').forEach(function(img) {
  img.addEventListener('click', function() {
    document.getElementById('lightbox-img').src = this.src;
    document.getElementById('lightbox').style.display = 'flex';
  });
});
document.querySelectorAll('.delete-photo-form').forEach(function(form) {
  form.addEventListener('submit', function(e) {
    e.stopPropagation();
  });
});
