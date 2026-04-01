let pendingForm = null;

function openModal(formId) {
  pendingForm = document.getElementById(formId);
  document.getElementById('delete-modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('delete-modal').style.display = 'none';
  pendingForm = null;
}

document.getElementById('modal-confirm').addEventListener('click', function() {
  if (pendingForm) pendingForm.submit();
});
