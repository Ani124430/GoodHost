document.addEventListener('DOMContentLoaded', function() {
  const passwordConfirm = document.getElementById('password_confirm');
  if (passwordConfirm) {
    passwordConfirm.addEventListener('change', function() {
      const password = document.getElementById('password').value;
      this.value !== password
        ? this.setCustomValidity('Паролите не съвпадат.')
        : this.setCustomValidity('');
    });
  }

  const photos = document.getElementById('photos');
  if (photos) {
    photos.addEventListener('change', function() {
      if (this.files.length > 20) {
        alert('Можете да качите най-много 20 снимки.');
        this.value = '';
      }
    });
  }
});
