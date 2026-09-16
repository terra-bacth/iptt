/* Progressive presentation enhancements. No API calls or business actions. */
(() => {
  const path = location.pathname.replace(/\/$/, '') || '/';
  document.querySelectorAll('.top-nav').forEach((nav, index) => {
    nav.setAttribute('role', 'navigation');
    nav.setAttribute('aria-label', 'Primary');
    const anchors = Array.from(nav.querySelectorAll('a'));
    anchors.forEach(link => {
      if (!link.classList.contains('iptt-brand') && new URL(link.href).pathname.replace(/\/$/, '') === path) {
        link.setAttribute('aria-current', 'page');
      }
    });
    // Existing templates use both grouped and direct-child navigation links.
    let items = nav.querySelector('.nav-links');
    if (!items) {
      const links = anchors.filter(link => !link.classList.contains('iptt-brand'));
      if (!links.length) return;
      items = document.createElement('div');
      links[0].before(items);
      links.forEach(link => items.append(link));
    }
    items.classList.add('iptt-nav-items');
    items.id = `iptt-nav-${index}`;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'iptt-menu-toggle';
    button.textContent = 'Menu';
    button.setAttribute('aria-controls', items.id);
    button.setAttribute('aria-expanded', 'false');
    nav.insertBefore(button, nav.firstChild);
    // Keep the button on the right of the leading brand/title, never in front
    // of it. Templates use several lead elements: .iptt-brand, .app-title or a
    // plain <div>/<strong> holding the product name.
    const brand = nav.querySelector(
      ':scope > .iptt-brand, :scope > .app-title, :scope > div:first-child, :scope > strong, :scope > b'
    );
    if (brand) { brand.after(button); } else { nav.append(button); }
    const close = () => {
      items.classList.remove('iptt-nav-open');
      button.setAttribute('aria-expanded', 'false');
    };
    button.addEventListener('click', () => {
      const open = items.classList.toggle('iptt-nav-open');
      button.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('keydown', event => {
      if (event.key === 'Escape' && items.classList.contains('iptt-nav-open')) {
        close(); button.focus();
      }
    });
    nav.classList.add('iptt-nav-ready');
  });
  document.querySelectorAll('table').forEach(table => {
    // Preserve sticky/frozen table layouts that already have a scroll container.
    const parent = table.parentElement;
    if (parent.classList.contains('iptt-table-scroll')) return;
    const overflow = getComputedStyle(parent).overflowX;
    const wrapper = ['auto', 'scroll'].includes(overflow) ? parent : document.createElement('div');
    if (wrapper !== parent) {
      wrapper.className = 'iptt-table-scroll';
      table.before(wrapper); wrapper.append(table);
    }
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role', 'region');
    const section = table.closest('section, .section-card, .report-card');
    const heading = section?.querySelector('h2, h3');
    wrapper.setAttribute('aria-label', `${heading?.textContent.trim() || 'Data table'} — scroll horizontally for more columns`);
  });
  // Add explicit accessible names only where no existing label/name is present.
  document.querySelectorAll('input, select, textarea').forEach((field, index) => {
    if (['hidden', 'submit', 'button', 'reset'].includes(field.type) || field.labels?.length || field.hasAttribute('aria-label') || field.hasAttribute('aria-labelledby')) return;
    const label = field.closest('.form-group')?.querySelector('label:not([for])');
    if (label) {
      if (!field.id) field.id = `iptt-field-${index}`;
      label.htmlFor = field.id;
      return;
    }
    const name = field.name?.replace(/_/g, ' ') || field.getAttribute('placeholder') || field.type || 'Field';
    field.setAttribute('aria-label', name.charAt(0).toUpperCase() + name.slice(1));
  });
  document.querySelector('.iptt-skip')?.addEventListener('click', event => {
    const main = document.querySelector('#iptt-main');
    const target = main?.querySelector('h1, h2') || main;
    if (target) {
      event.preventDefault();
      target.tabIndex = -1;
      target.focus();
      target.scrollIntoView({block: 'start'});
    }
  });
})();
