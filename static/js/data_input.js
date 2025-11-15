document.addEventListener('DOMContentLoaded', () => {
  formSubmitAction();
  populateCaseDropdown();
});

function formSubmitAction() {
  const form = document.getElementById('case-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(form);

    try {
      const response = await fetch('/add-case', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();

      if (response.ok) {
        alert('✓ ' + data.message);
        form.reset();
      } else {
        alert('✗ ' + data.error);
      }
    } catch (error) {
      alert('✗ Hiba: ' + error.message);
    }
  });
}

function populateCaseDropdown() {
  const caseSelect = document.getElementById('case-select');
  if (!caseSelect) return;
  fetch('/get-cases')
    .then((response) => response.json())
    .then((data) => {
      console.log('Esetek betöltve:', data);
      data.forEach((caseItem) => {
        const option = document.createElement('option');
        option.value = caseItem.id;
        option.textContent = caseItem.id + ' - ' + caseItem.name;
        caseSelect.appendChild(option);
      });
    })
    .catch((error) => console.error('Hiba a case lista betöltésekor:', error));
}
