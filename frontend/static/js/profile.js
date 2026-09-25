requireAuth();

async function loadProfile() {
  const el = document.getElementById("profile-content");
  try {
    const user = await apiFetch("/api/auth/me");
    el.innerHTML = `
      <p><strong>Name:</strong> ${user.name}</p>
      <p><strong>Email:</strong> ${user.email}</p>
      <p><strong>User ID:</strong> ${user.id}</p>
    `;
  } catch (err) {
    el.innerHTML = `<div class="empty-state">${err.message}</div>`;
  }
}

loadProfile();
