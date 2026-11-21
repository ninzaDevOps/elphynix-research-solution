function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

async function api(url, options = {}) {
  const headers = { ...(options.headers || {}), 'X-CSRFToken': csrfToken() };
  options.headers = headers;
  options.credentials = 'same-origin';
  const response = await fetch(url, options);
  if (response.status === 401) {
    location.assign('/login');
    throw new Error('Your session has expired. Please log in again.');
  }
  return response;
}

async function logout() {
  await fetch('/auth/logout', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-CSRFToken': csrfToken() }
  });
  location.assign('/login');
}

async function loadMetrics() {
  try {
    const response = await api('/api/analytics/metrics');
    if (!response.ok) throw new Error('Could not load dashboard metrics');
    const data = await response.json();
    document.getElementById('total').textContent = data.totalTraffics.value;
    document.getElementById('complete').textContent = `${data.completePercent.value}%`;
    document.getElementById('terminate').textContent = `${data.terminatePercent.value}%`;
    document.getElementById('quota').textContent = `${data.quotaFullPercent.value}%`;
  } catch (error) {
    console.error(error);
  }
}
