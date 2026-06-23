/**
 * Admin Pricing Module
 */

/**
 * Render pricing management
 */
async function renderPricing(main) {
  try {
    const res = await API.get('/api/v1/pricing');
    const p = res.data;

    const priceInputs = ['pdf', 'docx', 'zip'].map(t => `
      <div class="form-group">
        <label class="form-label">${p[t]?.label || t.toUpperCase()} — Price (KES)</label>
        <input class="form-input" type="number" id="price-${t}" value="${p[t]?.price||0}" min="0" step="1">
      </div>`).join('');

    main.innerHTML = `
      <h1>🏷 Document Pricing</h1>
      <div class="card" style="max-width:460px">
        <div class="card-title">Set Download Prices</div>
        <p class="text-sm text-muted" style="margin-bottom:1rem">These amounts are deducted from user wallets on each document download.</p>
        <div id="pricing-saved" class="alert alert-success" style="display:none">Pricing saved successfully.</div>
        ${priceInputs}
        <button class="btn btn-primary" onclick="savePricing()">Save Pricing</button>
      </div>`;
  } catch (error) {
    main.innerHTML = `<div class="alert alert-error">Failed to load pricing: ${error.message}</div>`;
  }
}

/**
 * Save pricing changes
 */
async function savePricing() {
  const body = {
    pdf: parseFloat(document.getElementById('price-pdf').value) || 0,
    docx: parseFloat(document.getElementById('price-docx').value) || 0,
    zip: parseFloat(document.getElementById('price-zip').value) || 0,
  };
  try {
    await API.put('/api/v1/pricing', body);
    const el = document.getElementById('pricing-saved');
    if (el) {
      el.style.display = 'flex';
      setTimeout(() => el.style.display = 'none', 3000);
    }
    showNotification('Pricing saved!', 'success');
  } catch (error) {
    showNotification(error.message || 'Failed to save pricing', 'error');
  }
}
