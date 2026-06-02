document.addEventListener('DOMContentLoaded', () => {
  const modal             = document.getElementById('introModal');
  const closeBtn          = document.getElementById('closeModal');
  const contactModal      = document.getElementById('contactModal');
  const closeContactModal = document.getElementById('closeContactModal');
  const openContactBtn    = document.getElementById('openContactBtn');
  const navNavigationBtn  = document.getElementById('nav-navigation');

  if (!sessionStorage.getItem('visited')) {
    if (modal) modal.style.display = 'flex';
    sessionStorage.setItem('visited', 'true');
  }

  if (closeBtn) closeBtn.addEventListener('click', () => modal.style.display = 'none');
  if (navNavigationBtn) navNavigationBtn.addEventListener('click', () => { if (modal) modal.style.display = 'flex'; });
  if (openContactBtn && contactModal) openContactBtn.addEventListener('click', () => contactModal.style.display = 'flex');
  if (closeContactModal) closeContactModal.addEventListener('click', () => contactModal.style.display = 'none');
  if (contactModal) contactModal.addEventListener('click', e => { if (e.target === contactModal) contactModal.style.display = 'none'; });
});
