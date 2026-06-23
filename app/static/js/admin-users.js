/**
 * Admin User Management Module
 */

let _userSearchTimer = null;

/**
 * Render users management tab with search and create
 */
async function renderUsers(main) {
  try {
    const q = (main._lastSearch || '').trim();
    const res = await API.get('/admin-panel/users' + (q ? '?search=' + encodeURIComponent(q) : ''));
    const availableRoles = CURRENT_ADMIN_ROLE === 'superuser'
      ? ['superuser', 'admin', 'support', 'client']
      : ['support', 'client'];

    const roleOptions = availableRoles.map(r => 
      `<option value="${r}">${r.charAt(0).toUpperCase() + r.slice(1)}</option>`
    ).join('');

    const userRows = (res.data || []).map(u => {
      const statusColor = u.is_active ? 'var(--green-600)' : 'var(--gray-300)';
      const statusText = u.is_active ? 'Active' : 'Disabled';
      const actionBtn = u.is_active
        ? `<button class="btn btn-sm btn-danger" onclick="disableUser(${u.id})">Disable</button>`
        : `<button class="btn btn-sm" onclick="enableUser(${u.id})">Enable</button>`;

      return `
        <tr id="user-row-${u.id}">
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div class="user-av">${u.name.split(' ').map(x=>x[0]).join('').slice(0,2)}</div>
              <div>
                <div style="font-weight:500">${u.name}</div>
                <div class="text-sm text-muted">${u.email}</div>
              </div>
            </div>
          </td>
          <td>
            <span class="badge ${u.role==='superuser'?'badge-blue':u.role==='admin'?'badge-green':'badge-amber'}">
              ${u.role}
            </span>
          </td>
          <td>KES ${(u.wallet_balance||0).toFixed(2)}</td>
          <td class="text-sm text-muted">${u.region||'—'}</td>
          <td class="text-sm text-muted">${u.last_login ? formatDate(u.last_login) : '—'}</td>
          <td class="text-sm text-muted">${u.last_logout ? formatDate(u.last_logout) : '—'}</td>
          <td>
            <span style="display:flex;align-items:center;gap:4px;font-size:12px">
              <span style="width:7px;height:7px;border-radius:50%;background:${statusColor};display:inline-block"></span>
              ${statusText}
            </span>
          </td>
          <td style="display:flex;gap:4px">
            ${actionBtn}
            <button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id},'${u.name}')">Delete</button>
            <button class="btn btn-sm" onclick="viewUserTransactions(${u.id},'${u.name}')">Transactions</button>
            <button class="btn btn-sm" onclick="viewUserPayments(${u.id},'${u.name}')">Payments</button>
          </td>
        </tr>`;
    }).join('');

    const superuserNote = CURRENT_ADMIN_ROLE !== 'superuser' 
      ? '<div class="text-sm text-muted" style="margin-top:8px">Only superusers can create admin-level accounts.</div>' 
      : '';

    main.innerHTML = `
      <h1>👥 User Management</h1>
      <div style="display:flex;gap:8px;margin-bottom:12px;align-items:center">
        <input id="user-search" class="form-input" placeholder="Search users by name, username or email" 
               style="flex:1" oninput="debouncedUserSearch(event)">
        <button class="btn" onclick="clearUserSearch()">Clear</button>
      </div>
      <div class="card" style="margin-bottom:1.25rem">
        <div class="card-title"><div class="card-icon">➕</div>Create New User</div>
        <div class="form-row">
          <div>
            <label class="form-label">Full Name</label>
            <input id="new-user-name" class="form-input" type="text" placeholder="Jane Doe">
          </div>
          <div>
            <label class="form-label">Username</label>
            <input id="new-user-username" class="form-input" type="text" placeholder="janedoe">
          </div>
          <div>
            <label class="form-label">Email</label>
            <input id="new-user-email" class="form-input" type="email" placeholder="jane@example.com">
          </div>
          <div>
            <label class="form-label">Password</label>
            <input id="new-user-password" class="form-input" type="password" placeholder="Minimum 8 characters">
          </div>
          <div>
            <label class="form-label">Role</label>
            <select id="new-user-role" class="form-input form-select">
              ${roleOptions}
            </select>
          </div>
          <div>
            <label class="form-label">Region</label>
            <input id="new-user-region" class="form-input" type="text" placeholder="Nairobi">
          </div>
        </div>
        <div style="margin-top:12px;display:flex;gap:10px;align-items:center">
          <button class="btn btn-primary" onclick="createUser()">Create User</button>
          <div id="create-user-error" class="alert alert-error" style="display:none;margin:0;padding:0.75rem 1rem;font-size:13px"></div>
        </div>
        ${superuserNote}
      </div>
      <div class="card" style="padding:0;overflow-x:auto">
        <table class="admin-table">
          <thead><tr>
            <th>User</th><th>Role</th><th>Wallet</th><th>Region</th>
            <th>Last Login</th><th>Last Logout</th><th>Status</th><th>Actions</th>
          </tr></thead>
          <tbody>${userRows}</tbody>
        </table>
      </div>`;
  } catch (error) {
    main.innerHTML = `<div class="alert alert-error">Failed to load users: ${error.message}</div>`;
  }
}

/**
 * View user transactions in modal
 */
async function viewUserTransactions(userId, userName) {
  try {
    const res = await API.get(`/admin-panel/users/${userId}/transactions`);
    const rows = res.data || [];
    const html = `<div style="max-height:60vh;overflow:auto"><table class="admin-table"><thead><tr>
      <th>Txn</th><th>Amount</th><th>Tag</th><th>Source</th><th>Date</th>
    </tr></thead><tbody>`
      + rows.map(t => `<tr>
        <td style="font-family:monospace">${t.transaction_number.slice(0,8)}…</td>
        <td>KES ${t.amount.toFixed(2)}</td>
        <td>${t.tag}</td>
        <td>${t.source || '—'}</td>
        <td class="text-sm text-muted">${formatDate(t.created_at)}</td>
      </tr>`).join('')
      + `</tbody></table></div>`;
    openModal(`Transactions — ${userName}`, html);
  } catch (error) {
    showNotification(error.message || 'Unable to load transactions', 'error');
  }
}

/**
 * View user payments in modal
 */
async function viewUserPayments(userId, userName) {
  try {
    const res = await API.get(`/admin-panel/users/${userId}/payments`);
    const rows = res.data || [];
    const refundBtn = (p) => p.is_refunded 
      ? '<span class="text-sm text-muted">Refunded</span>'
      : (CURRENT_ADMIN_ROLE ? `<button class="btn btn-sm btn-danger" onclick="refundPayment(${userId},'${p.transaction_id}')">Refund</button>` : '');

    const html = `<div style="max-height:60vh;overflow:auto"><table class="admin-table"><thead><tr>
      <th>Payment</th><th>Amount</th><th>Type</th><th>Balance After</th><th>Time</th><th>Refund</th>
    </tr></thead><tbody>`
      + rows.map(p => `<tr id="pay-row-${p.transaction_id}">
        <td style="font-family:monospace">${p.transaction_id.slice(0,8)}…</td>
        <td>KES ${p.amount.toFixed(2)}</td>
        <td>${p.doc_type}</td>
        <td>KES ${p.balance_after.toFixed(2)}</td>
        <td class="text-sm text-muted">${formatDate(p.payment_time)}</td>
        <td>${refundBtn(p)}</td>
      </tr>`).join('')
      + `</tbody></table></div>`;
    openModal(`Payments — ${userName}`, html);
  } catch (error) {
    showNotification(error.message || 'Unable to load payments', 'error');
  }
}

/**
 * Issue refund for a payment
 */
async function refundPayment(userId, transactionId) {
  if (!confirm('Issue refund for this payment?')) return;
  try {
    const res = await API.post(`/admin-panel/users/${userId}/refund`, { payment_id: transactionId });
    showNotification(res.message || 'Refunded', 'success');
    viewUserPayments(userId, '');
  } catch (error) {
    showNotification(error.message || 'Refund failed', 'error');
  }
}

/**
 * Debounced user search
 */
function debouncedUserSearch(e) {
  const val = e.target.value;
  const main = document.getElementById('admin-content');
  main._lastSearch = val;
  if (_userSearchTimer) clearTimeout(_userSearchTimer);
  _userSearchTimer = setTimeout(() => renderUsers(main), 350);
}

/**
 * Clear user search
 */
function clearUserSearch() {
  const main = document.getElementById('admin-content');
  main._lastSearch = '';
  document.getElementById('user-search').value = '';
  renderUsers(main);
}

/**
 * Create new user
 */
async function createUser() {
  const errorEl = document.getElementById('create-user-error');
  errorEl.style.display = 'none';
  const body = {
    name: document.getElementById('new-user-name').value,
    username: document.getElementById('new-user-username').value,
    email: document.getElementById('new-user-email').value,
    password: document.getElementById('new-user-password').value,
    role_tag: document.getElementById('new-user-role').value,
    region: document.getElementById('new-user-region').value,
  };

  try {
    await API.post('/admin-panel/users', body);
    showTab('users', document.querySelector('.admin-nav-item:nth-child(2)'));
  } catch (err) {
    errorEl.textContent = err.message || 'Unable to create user.';
    errorEl.style.display = 'block';
  }
}

/**
 * Disable user
 */
async function disableUser(id) {
  if (!confirm('Disable this user?')) return;
  try {
    await API.post(`/admin-panel/users/${id}/disable`);
    showTab('users', document.querySelector('.admin-nav-item:nth-child(2)'));
  } catch (error) {
    showNotification(error.message || 'Failed to disable user', 'error');
  }
}

/**
 * Enable user
 */
async function enableUser(id) {
  try {
    await API.post(`/admin-panel/users/${id}/enable`);
    showTab('users', document.querySelector('.admin-nav-item:nth-child(2)'));
  } catch (error) {
    showNotification(error.message || 'Failed to enable user', 'error');
  }
}

/**
 * Delete user
 */
async function deleteUser(id, name) {
  if (!confirm(`Permanently delete user "${name}"? This cannot be undone.`)) return;
  try {
    await API.delete(`/admin-panel/users/${id}`);
    showTab('users', document.querySelector('.admin-nav-item:nth-child(2)'));
  } catch (error) {
    showNotification(error.message || 'Failed to delete user', 'error');
  }
}
