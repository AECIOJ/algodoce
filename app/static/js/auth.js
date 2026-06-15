let authPopup = null;

function showAuthPopup() {
  if (authPopup) return;
  authPopup = document.createElement("div");
  authPopup.id = "auth-popup";
  authPopup.innerHTML = `
    <div class="auth-overlay" onclick="closeAuthPopup()"></div>
    <div class="auth-card">
      <div class="auth-card-inner">
        <span class="auth-close" onclick="closeAuthPopup()">&times;</span>
        <div class="auth-icon">🔐</div>
        <h4>Acesso ao Sistema</h4>
        <input type="text" id="auth-username" placeholder="Usuário" autofocus>
        <input type="password" id="auth-password" placeholder="Senha">
        <div id="auth-error" class="auth-error"></div>
        <button onclick="submitAuth()" class="auth-btn">Entrar</button>
      </div>
    </div>
  `;
  document.body.appendChild(authPopup);
  setTimeout(() => authPopup.classList.add("show"), 10);
  const onEnter = (e) => { if (e.key === "Enter") submitAuth(); };
  document.getElementById("auth-username").addEventListener("keydown", onEnter);
  document.getElementById("auth-password").addEventListener("keydown", onEnter);
  document.getElementById("auth-username").focus();
}

function closeAuthPopup() {
  if (authPopup) {
    authPopup.classList.remove("show");
    setTimeout(() => { authPopup.remove(); authPopup = null; }, 200);
  }
}

function submitAuth() {
  const us = document.getElementById("auth-username").value;
  const pw = document.getElementById("auth-password").value;
  const err = document.getElementById("auth-error");
  err.textContent = "";
  fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: us, password: pw }),
  })
    .then((r) => r.json().then((d) => ({ status: r.status, body: d })))
    .then(({ status, body }) => {
      if (status === 200) window.location.href = body.redirect;
      else err.textContent = body.error || "Senha incorreta";
    })
    .catch(() => { err.textContent = "Erro de conexão"; });
}
