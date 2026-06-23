/**
 * Admin Dashboard Core Module
 * Handles tab navigation, modals, and shared utilities
 */

let _activeTab = 'overview';
const CURRENT_ADMIN_ROLE = document.querySelector('[data-admin-role]')?.dataset.adminRole || '';

/**
 * Switch between dashboard tabs
 */
async function showTab(tab, el) {
  _activeTab = tab;
  document.querySelectorAll('.admin-nav-item').forEach(b => b.classList.remove('active'));
  el?.classList.add('active');
  const main = document.getElementById('admin-content');
  main.innerHTML = '<div class="spinner-wrap"><div class="spinner"></div></div>';

  try {
    if (tab === 'overview') await renderOverview(main);
    if (tab === 'users') await renderUsers(main);
    if (tab === 'revenue') await renderRevenue(main);
    if (tab === 'doc-stats') await renderDocStats(main);
    if (tab === 'content') renderContent(main);
    if (tab === 'pricing') await renderPricing(main);
  } catch (error) {
    main.innerHTML = `<div class="alert alert-error">Error loading ${tab}: ${error.message}</div>`;
  }
}

/**
 * Close modal
 */
function closeModal() {
  const modal = document.getElementById('admin-modal');
  if (modal) {
    modal.classList.remove('visible');
    document.getElementById('admin-modal-body').innerHTML = '';
  }
}

/**
 * Open modal with title and HTML content
 */
function openModal(title, html) {
  const modal = document.getElementById('admin-modal');
  if (modal) {
    document.getElementById('admin-modal-title').textContent = title;
    document.getElementById('admin-modal-body').innerHTML = html;
    modal.classList.add('visible');
  }
}

/**
 * Format currency for display
 */
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-KE', {
    style: 'currency',
    currency: 'KES',
  }).format(amount);
}

/**
 * Format date/time for display
 */
function formatDate(dateString, style = 'short') {
  return new Date(dateString).toLocaleString('en-KE', {
    dateStyle: style,
    timeStyle: 'short',
  });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const initialTab = document.querySelector('.admin-nav-item.active');
  if (initialTab) {
    showTab('overview', initialTab);
  }
});
