document.addEventListener('DOMContentLoaded', () => {
  // -------- SEARCH --------
  const searchInput = document.getElementById('tableSearch');
  const tableRows = document.querySelectorAll('tbody tr');

  searchInput.addEventListener('keyup', () => {
    const query = searchInput.value.toLowerCase();

    tableRows.forEach((row) => {
      const text = row.innerText.toLowerCase();
      row.style.display = text.includes(query) ? '' : 'none';
    });
  });

  // -------- SORTING --------
  const table = document.querySelector('table');
  const headers = table.querySelectorAll('th.sortable');
  let sortDirection = {};

  headers.forEach((header) => {
    sortDirection[header.dataset.column] = 'asc';

    header.addEventListener('click', () => {
      const columnIndex = header.dataset.column;
      const direction = sortDirection[columnIndex];
      const rowsArray = Array.from(tableRows);

      rowsArray.sort((a, b) => {
        let aText = a.children[columnIndex].innerText.trim();
        let bText = b.children[columnIndex].innerText.trim();

        // Date sort
        if (columnIndex == 3) {
          return direction === 'asc'
            ? new Date(aText) - new Date(bText)
            : new Date(bText) - new Date(aText);
        }

        // Number sort
        if (!isNaN(aText) && !isNaN(bText)) {
          return direction === 'asc' ? aText - bText : bText - aText;
        }

        // String sort
        return direction === 'asc'
          ? aText.localeCompare(bText)
          : bText.localeCompare(aText);
      });

      rowsArray.forEach((row) => table.querySelector('tbody').appendChild(row));

      sortDirection[columnIndex] = direction === 'asc' ? 'desc' : 'asc';
    });
  });
});
