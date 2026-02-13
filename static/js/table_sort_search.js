document.addEventListener('DOMContentLoaded', () => {
  const tables = document.querySelectorAll('table');

  tables.forEach((table) => {
    const tbody = table.querySelector('tbody');
    const headers = table.querySelectorAll('th.sortable');
    let sortDirection = {};

    headers.forEach((header, index) => {
      sortDirection[index] = 'asc';

      header.addEventListener('click', () => {
        const type = header.dataset.type || 'string';
        const direction = sortDirection[index];
        const rows = Array.from(tbody.querySelectorAll('tr'));

        rows.sort((a, b) => {
          let aText = a.children[index].innerText.trim();
          let bText = b.children[index].innerText.trim();

          switch (type) {
            case 'number':
              aText = parseFloat(aText) || 0;
              bText = parseFloat(bText) || 0;
              break;

            case 'date':
              aText = new Date(aText);
              bText = new Date(bText);
              break;

            default:
              return direction === 'asc'
                ? aText.localeCompare(bText, undefined, { numeric: true })
                : bText.localeCompare(aText, undefined, { numeric: true });
          }

          return direction === 'asc' ? aText - bText : bText - aText;
        });

        rows.forEach((row) => tbody.appendChild(row));
        sortDirection[index] = direction === 'asc' ? 'desc' : 'asc';
      });
    });
  });

  // -------- SEARCH (per page, not per table) --------
  const searchInput = document.getElementById('tableSearch');

  if (searchInput) {
    searchInput.addEventListener('keyup', () => {
      const query = searchInput.value.toLowerCase();
      const rows = document.querySelectorAll('tbody tr');

      rows.forEach((row) => {
        row.style.display = row.innerText.toLowerCase().includes(query)
          ? ''
          : 'none';
      });
    });
  }
});
