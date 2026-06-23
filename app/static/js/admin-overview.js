/**
 * Admin Dashboard Overview, Revenue, and Statistics Module
 */

/**
 * Render overview dashboard with key metrics
 */
async function renderOverview(main) {
  try {
    const [ov, ds] = await Promise.all([
      API.get('/admin-panel/overview'),
      API.get('/admin-panel/doc-stats'),
    ]);
    const d = ov.data;
    
    const topSubjects = (ds.data || []).slice(0, 6).map((r, i, arr) => `
      <div class="mini-bar">
        <span style="flex:1;color:var(--gray-700)">${r.subject} ${r.grade}</span>
        <span class="badge badge-blue">${r.system}</span>
        <strong style="width:30px;text-align:right">${r.count}</strong>
        <div class="mini-bar-inner"><div class="mini-bar-fill" style="width:${Math.round(r.count/arr[0].count*100)}%"></div></div>
      </div>`).join('') || '<p class="text-sm text-muted">No data yet.</p>';

    const roleDistribution = Object.entries(d.role_counts || {}).map(([tag, count]) => `
      <div class="mini-bar">
        <span style="flex:1;color:var(--gray-700);text-transform:capitalize">${tag}</span>
        <strong>${count}</strong>
      </div>`).join('');

    main.innerHTML = `
      <h1>📊 Overview <span class="badge badge-blue">${CURRENT_ADMIN_ROLE}</span></h1>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-val">${d.total_users}</div>
          <div class="stat-label">Total Users</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">${d.total_docs_generated.toLocaleString()}</div>
          <div class="stat-label">Docs Generated</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">KES ${d.actual_revenue.toLocaleString()}</div>
          <div class="stat-label">Actual Revenue</div>
        </div>
        <div class="stat-card">
          <div class="stat-val">KES ${d.potential_revenue.toLocaleString()}</div>
          <div class="stat-label">Wallet Balances</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem">
        <div class="card">
          <div class="card-title"><div class="card-icon">📈</div>Top Generated Subjects</div>
          ${topSubjects}
        </div>
        <div class="card">
          <div class="card-title"><div class="card-icon">👥</div>Role Distribution</div>
          ${roleDistribution}
          <hr>
          <div style="font-size:12px;color:var(--gray-500);margin-top:8px">
            Total deposited: <strong>KES ${d.total_deposited.toLocaleString()}</strong><br>
            Spent on docs: <strong>KES ${d.actual_revenue.toLocaleString()}</strong>
          </div>
        </div>
      </div>`;
  } catch (error) {
    main.innerHTML = `<div class="alert alert-error">Failed to load overview: ${error.message}</div>`;
  }
}

/**
 * Render revenue dashboard with daily activity chart
 */
async function renderRevenue(main) {
  try {
    const [ov, daily, txns] = await Promise.all([
      API.get('/admin-panel/overview'),
      API.get('/admin-panel/revenue/daily?days=30'),
      API.get('/admin-panel/transactions?per_page=30'),
    ]);
    const d = ov.data;
    const maxIn = Math.max(...(daily.data || []).map(x => x.in || 0), 1);

    const dailyChart = (daily.data || []).map(day => {
      const h = Math.round((day.in || 0) / maxIn * 70);
      return `<div title="${day.date}\nIn: KES ${day.in || 0}\nOut: KES ${day.out || 0}"
        style="flex:0 0 18px;display:flex;flex-direction:column;align-items:center;gap:2px">
        <div style="width:14px;background:var(--blue-500);border-radius:2px 2px 0 0;height:${h}px"></div>
        <div style="font-size:8px;color:var(--gray-400);transform:rotate(-45deg);margin-top:2px">${day.date.slice(5)}</div>
      </div>`;
    }).join('');

    const transactionRows = (txns.data || []).map(t => `
      <tr>
        <td class="text-sm text-muted" style="font-family:monospace">${t.transaction_number.slice(0,8)}…</td>
        <td>${t.user || '—'}</td>
        <td><span class="badge ${t.tag === 'in' ? 'badge-green' : 'badge-amber'}">${t.tag === 'in' ? 'Deposit' : 'Payment'}</span></td>
        <td class="text-sm text-muted">${t.source || '—'}</td>
        <td style="font-weight:600">KES ${t.amount.toFixed(2)}</td>
        <td class="text-sm text-muted">${formatDate(t.created_at, 'medium')}</td>
      </tr>`).join('');

    main.innerHTML = `
      <h1>💰 Revenue</h1>
      <div class="rev-grid">
        <div class="rev-card">
          <div class="rev-val" style="color:var(--green-600)">KES ${d.actual_revenue.toLocaleString()}</div>
          <div class="rev-label">Actual Revenue (document payments)</div>
          <div class="rev-bar-bg"><div class="rev-bar" style="background:var(--green-600);width:${Math.round(d.actual_revenue/Math.max(d.total_deposited,1)*100)}%"></div></div>
        </div>
        <div class="rev-card">
          <div class="rev-val" style="color:var(--blue-600)">KES ${d.total_deposited.toLocaleString()}</div>
          <div class="rev-label">Total Wallet Deposits</div>
          <div class="rev-bar-bg"><div class="rev-bar" style="width:100%"></div></div>
        </div>
        <div class="rev-card">
          <div class="rev-val" style="color:var(--amber-600)">KES ${d.potential_revenue.toLocaleString()}</div>
          <div class="rev-label">Wallet Balances (Potential Revenue)</div>
          <div class="rev-bar-bg"><div class="rev-bar" style="background:var(--amber-600);width:${Math.round(d.potential_revenue/Math.max(d.total_deposited,1)*100)}%"></div></div>
        </div>
      </div>
      <div class="card" style="margin-bottom:1.25rem">
        <div class="card-title"><div class="card-icon">📅</div>Daily Activity (Last 30 days)</div>
        <div style="display:flex;align-items:flex-end;gap:4px;height:80px;overflow-x:auto">
          ${dailyChart}
        </div>
      </div>
      <div class="card" style="padding:0;overflow-x:auto">
        <div class="card-title" style="padding:1rem 1.25rem;border-bottom:1px solid var(--gray-200);margin:0">
          <div class="card-icon">🧾</div>All Transactions
        </div>
        <table class="admin-table">
          <thead><tr>
            <th>Ref</th><th>User</th><th>Type</th><th>Source</th><th>Amount</th><th>Date</th>
          </tr></thead>
          <tbody>${transactionRows}</tbody>
        </table>
      </div>`;
  } catch (error) {
    main.innerHTML = `<div class="alert alert-error">Failed to load revenue data: ${error.message}</div>`;
  }
}

/**
 * Render document generation statistics
 */
async function renderDocStats(main) {
  try {
    const res = await API.get('/admin-panel/doc-stats');
    const max = res.data[0]?.count || 1;
    
    const statsRows = (res.data || []).map(r => `
      <tr>
        <td style="font-weight:500">${r.subject}</td>
        <td>${r.grade}</td>
        <td><span class="badge badge-blue">${r.system}</span></td>
        <td><strong>${r.count}</strong></td>
        <td>
          <div class="mini-bar-inner" style="width:120px;flex:none">
            <div class="mini-bar-fill" style="width:${Math.round(r.count/max*100)}%"></div>
          </div>
        </td>
      </tr>`).join('') || '<tr><td colspan="5" class="text-muted" style="padding:2rem;text-align:center">No documents generated yet.</td></tr>';

    main.innerHTML = `
      <h1>📄 Document Generation Stats</h1>
      <div class="card" style="padding:0;overflow-x:auto">
        <table class="admin-table">
          <thead><tr>
            <th>Subject</th><th>Grade</th><th>System</th><th>Times Generated</th><th>Share</th>
          </tr></thead>
          <tbody>${statsRows}</tbody>
        </table>
      </div>`;
  } catch (error) {
    main.innerHTML = `<div class="alert alert-error">Failed to load statistics: ${error.message}</div>`;
  }
}
