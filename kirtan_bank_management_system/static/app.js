let currentUser = null;

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {"Content-Type":"application/json", ...(options.headers || {})},
    ...options
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function money(value) {
  return new Intl.NumberFormat("en-IN", {
    style:"currency", currency:"INR", maximumFractionDigits:2
  }).format(value);
}

function toast(message, error=false) {
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  el.textContent = (error ? "⚠ " : "✓ ") + message;
  document.getElementById("toastBox").appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function showAuth(type) {
  document.getElementById("loginForm").classList.toggle("hidden", type !== "login");
  document.getElementById("registerForm").classList.toggle("hidden", type !== "register");
  document.querySelectorAll(".tab").forEach((b,i) => b.classList.toggle("active", (type==="login" ? i===0 : i===1)));
}

async function register() {
  try {
    const data = await api("/api/register", {
      method:"POST",
      body:JSON.stringify({
        name: document.getElementById("regName").value,
        age: document.getElementById("regAge").value,
        email: document.getElementById("regEmail").value,
        pin: document.getElementById("regPin").value
      })
    });
    toast("Account created.");
    showAuth("login");
    document.getElementById("loginAccount").value = data.account_no;
    alert(`Account created successfully!\n\nYour Account Number:\n${data.account_no}\n\nSave this number safely.`);
  } catch(e) { toast(e.message, true); }
}

async function login() {
  try {
    await api("/api/login", {
      method:"POST",
      body:JSON.stringify({
        account_no:document.getElementById("loginAccount").value,
        pin:document.getElementById("loginPin").value
      })
    });
    await showDashboard();
    toast("Welcome back.");
  } catch(e) { toast(e.message, true); }
}

async function showDashboard() {
  document.getElementById("authView").classList.add("hidden");
  document.getElementById("dashboard").classList.remove("hidden");
  document.getElementById("headerActions").innerHTML = `<span class="secure-pill">● SECURE SESSION</span>`;
  await loadDashboard();
}

async function loadDashboard() {
  try {
    currentUser = await api("/api/me");
    document.getElementById("userName").textContent = currentUser.name.split(" ")[0];
    document.getElementById("balance").textContent = money(currentUser.balance);
    document.getElementById("accountNo").textContent = currentUser.account_no;

    const tx = await api("/api/transactions");
    document.getElementById("transactionCount").textContent = tx.length;
    renderTransactions(tx);
  } catch(e) {
    if (e.message.includes("login")) location.reload();
    else toast(e.message, true);
  }
}

function renderTransactions(rows) {
  const el = document.getElementById("transactions");
  if (!rows.length) {
    el.innerHTML = `<div class="empty">No transactions yet. Deposit or withdraw money to see activity.</div>`;
    return;
  }
  el.innerHTML = rows.slice(0,10).map(t => {
    const deposit = t.type === "DEPOSIT";
    return `<div class="transaction">
      <div class="tx-icon ${deposit ? "deposit" : "withdraw"}">${deposit ? "↓" : "↑"}</div>
      <div><div class="tx-name">${deposit ? "Money Deposited" : "Money Withdrawn"}</div><div class="tx-date">${t.created_at}</div></div>
      <div class="tx-amount ${deposit ? "green" : "red"}">${deposit ? "+" : "-"}${money(t.amount)}</div>
      <div class="tx-balance">Bal. ${money(t.balance_after)}</div>
    </div>`;
  }).join("");
}

function openMoney(type) {
  const deposit = type === "deposit";
  document.getElementById("modalContent").innerHTML = `
    <h3>${deposit ? "Deposit Money" : "Withdraw Money"}</h3>
    <p>${deposit ? "Add funds to your bank account." : "Withdraw funds from your available balance."}</p>
    <label>Amount</label>
    <input id="moneyAmount" type="number" min="1" max="100000" placeholder="₹ 0.00">
    <div class="modal-actions">
      <button class="ghost" onclick="closeModal()">Cancel</button>
      <button class="primary" style="padding:11px 15px;border-radius:10px" onclick="submitMoney('${type}')">${deposit ? "Deposit" : "Withdraw"}</button>
    </div>`;
  document.getElementById("modal").classList.remove("hidden");
  document.getElementById("moneyAmount").focus();
}

async function submitMoney(type) {
  try {
    const amount = document.getElementById("moneyAmount").value;
    await api(`/api/${type}`, {method:"POST", body:JSON.stringify({amount})});
    closeModal();
    await loadDashboard();
    toast(type === "deposit" ? "Money deposited successfully." : "Money withdrawn successfully.");
  } catch(e) { toast(e.message, true); }
}

function openProfile() {
  document.getElementById("modalContent").innerHTML = `
    <h3>My Profile</h3><p>Update your name and email.</p>
    <label>Full Name</label><input id="profileName" value="${escapeHtml(currentUser.name)}">
    <label>Email</label><input id="profileEmail" type="email" value="${escapeHtml(currentUser.email)}">
    <div class="modal-actions"><button class="ghost" onclick="closeModal()">Cancel</button><button class="primary" style="padding:11px 15px;border-radius:10px" onclick="saveProfile()">Save Changes</button></div>`;
  document.getElementById("modal").classList.remove("hidden");
}

async function saveProfile() {
  try {
    await api("/api/profile", {
      method:"PUT",
      body:JSON.stringify({
        name:document.getElementById("profileName").value,
        email:document.getElementById("profileEmail").value
      })
    });
    closeModal(); await loadDashboard(); toast("Profile updated.");
  } catch(e) { toast(e.message, true); }
}

async function confirmDelete() {
  if (currentUser.balance !== 0) {
    toast("Withdraw your full balance before deleting the account.", true);
    return;
  }
  if (!confirm("Delete your account permanently? This cannot be undone.")) return;
  try {
    await api("/api/account", {method:"DELETE"});
    location.reload();
  } catch(e) { toast(e.message, true); }
}

async function logout() {
  await api("/api/logout", {method:"POST"});
  location.reload();
}

function downloadStatement() {
  window.location.href = "/api/statement";
}

function closeModal() {
  document.getElementById("modal").classList.add("hidden");
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));
}

document.getElementById("modal").addEventListener("click", e => {
  if (e.target.id === "modal") closeModal();
});

document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeModal();
});

api("/api/me").then(showDashboard).catch(() => {});
