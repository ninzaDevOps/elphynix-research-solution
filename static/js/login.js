document.getElementById('loginForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = document.getElementById('msg');
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Login failed');
    // Authentication is held in the HttpOnly server-side session cookie, not localStorage.
    location.assign('/dashboard');
  } catch (error) {
    message.textContent = error.message;
    message.style.color = 'crimson';
  }
});
