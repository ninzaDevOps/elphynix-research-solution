const projectRows = document.getElementById('projectRows');
const projectForm = document.getElementById('projectForm');
const projectMessage = document.getElementById('projectMsg');

function addCell(row, value) {
  const cell = document.createElement('td');
  cell.textContent = value == null ? '' : String(value);
  row.appendChild(cell);
}

async function loadProjects() {
  try {
    const response = await api('/projects/all');
    if (!response.ok) throw new Error('Unable to load projects');
    const projects = await response.json();
    projectRows.replaceChildren();
    projects.forEach((project) => {
      const row = document.createElement('tr');
      addCell(row, project.id);
      addCell(row, project.project_identifier);
      addCell(row, project.client_username);
      addCell(row, project.status);
      addCell(row, project.counts);
      projectRows.appendChild(row);
    });
  } catch (error) {
    projectMessage.textContent = error.message;
  }
}

projectForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    projectIdentifier: document.getElementById('pid').value.trim(),
    clientUsername: document.getElementById('client').value.trim(),
    ir: document.getElementById('ir').value,
    loi: document.getElementById('loi').value,
    counts: document.getElementById('counts').value,
    cpi: document.getElementById('cpi').value,
    quota: document.getElementById('quota').value
  };
  try {
    const response = await api('/projects/create/project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || data.error || 'Project creation failed');
    projectMessage.textContent = data.message;
    projectMessage.style.color = 'green';
    projectForm.reset();
    await loadProjects();
  } catch (error) {
    projectMessage.textContent = error.message;
    projectMessage.style.color = 'crimson';
  }
});

loadProjects();
