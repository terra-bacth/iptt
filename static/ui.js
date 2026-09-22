/* IPTT Cinematic UI v10 — progressive enhancements, no business logic */
(() => {
  const path = location.pathname.replace(/\/$/, '') || '/';
  // NAV — aria + toggle
  document.querySelectorAll('.top-nav').forEach((nav, index) => {
    nav.setAttribute('role', 'navigation');
    nav.setAttribute('aria-label', 'Primary');
    const anchors = Array.from(nav.querySelectorAll('a'));
    anchors.forEach(link => {
      if (!link.classList.contains('iptt-brand') && new URL(link.href).pathname.replace(/\/$/, '') === path) {
        link.setAttribute('aria-current', 'page');
      }
    });
    let items = nav.querySelector('.iptt-nav-items, .nav-links');
    if (!items) {
      const links = anchors.filter(l => !l.classList.contains('iptt-brand'));
      if (!links.length) return;
      items = document.createElement('div');
      links[0].before(items);
      links.forEach(l => items.append(l));
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
    const brand = nav.querySelector(':scope > .iptt-brand, :scope > .app-title, :scope > div:first-child, :scope > strong, :scope > b');
    if (brand) { brand.after(button); } else { nav.append(button); }
    const close = () => { items.classList.remove('iptt-nav-open'); button.setAttribute('aria-expanded', 'false'); };
    button.addEventListener('click', () => {
      const open = items.classList.toggle('iptt-nav-open');
      button.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('keydown', e => { if (e.key === 'Escape' && items.classList.contains('iptt-nav-open')) { close(); button.focus(); } });
    nav.classList.add('iptt-nav-ready');
  });

  // TABLES — scroll wrapper
  document.querySelectorAll('table').forEach(table => {
    const parent = table.parentElement;
    if (parent.classList.contains('iptt-table-scroll')) return;
    const overflow = getComputedStyle(parent).overflowX;
    const wrapper = ['auto','scroll'].includes(overflow) ? parent : document.createElement('div');
    if (wrapper !== parent) { wrapper.className = 'iptt-table-scroll'; table.before(wrapper); wrapper.append(table); }
    wrapper.tabIndex = 0;
    wrapper.setAttribute('role','region');
    const section = table.closest('section, .section-card, .report-card, .dashboard-card');
    const heading = section?.querySelector('h2, h3, .section-title');
    wrapper.setAttribute('aria-label', `${(heading?.textContent||'Data table').trim().slice(0,60)} — scroll horizontally`);
  });

  // ACCESSIBILITY — labels
  document.querySelectorAll('input, select, textarea').forEach((field, i) => {
    if (['hidden','submit','button','reset'].includes(field.type) || field.labels?.length || field.hasAttribute('aria-label') || field.hasAttribute('aria-labelledby')) return;
    const label = field.closest('.form-group')?.querySelector('label:not([for])');
    if (label) { if (!field.id) field.id = `iptt-field-${i}`; label.htmlFor = field.id; return; }
    const name = field.name?.replace(/_/g,' ') || field.getAttribute('placeholder') || field.type || 'Field';
    field.setAttribute('aria-label', name.charAt(0).toUpperCase()+name.slice(1));
  });

  // CINEMATIC COLLAPSIBLE — smooth grid animation, keeps legacy toggleSection working
  const enhanceCollapsible = (header, content, icon) => {
    if (!header || !content) return;
    header.setAttribute('role','button');
    header.setAttribute('tabindex','0');
    header.setAttribute('aria-expanded', content.classList.contains('active') ? 'true' : 'false');
    const toggle = () => {
      const isOpen = content.classList.toggle('active');
      header.classList.toggle('active', isOpen);
      header.setAttribute('aria-expanded', String(isOpen));
      if (icon) { icon.textContent = isOpen ? '−' : '+'; icon.style.transform = isOpen ? 'rotate(180deg)' : 'none'; }
      // legacy icon handling
      const legacyIcon = document.getElementById('icon-'+content.id);
      if (legacyIcon && legacyIcon!==icon) legacyIcon.textContent = isOpen ? '−' : '+';
    };
    header.addEventListener('click', toggle);
    header.addEventListener('keydown', e => { if (e.key==='Enter' || e.key===' ') { e.preventDefault(); toggle(); } });
  };
  document.querySelectorAll('.collapsible-header, .section-header').forEach(h => {
    const id = h.getAttribute('onclick')?.match(/toggleSection\(['\"]([^'\"]+)['\"]\)/)?.[1];
    let content = id ? document.getElementById(id) : h.nextElementSibling;
    if (!content || !content.classList.contains('collapsible-content') && !content.classList.contains('section-content')) {
      // fallback: next sibling with those classes
      content = h.parentElement?.querySelector('.collapsible-content, .section-content') || h.nextElementSibling;
    }
    const icon = h.querySelector('.collapsible-icon, .toggle-icon');
    enhanceCollapsible(h, content, icon);
  });
  // global toggleSection for inline onclick compatibility — now cinematic
  window.toggleSection = function(sectionId){
    const section = document.getElementById(sectionId);
    const icon = document.getElementById('icon-'+sectionId);
    if (!section) return;
    const header = section.previousElementSibling?.classList.contains('collapsible-header') || section.previousElementSibling?.classList.contains('section-header') ? section.previousElementSibling : document.querySelector(`[onclick*="${sectionId}"]`);
    const isOpen = section.classList.toggle('active');
    if (header) { header.classList.toggle('active', isOpen); header.setAttribute('aria-expanded', String(isOpen)); }
    if (icon) icon.textContent = isOpen ? '−' : '+';
  };

  // PROGRESS BARS — grow on view
  if ('IntersectionObserver' in window) {
    const bars = document.querySelectorAll('.progress-bar');
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        const bar = e.target;
        bar.style.transform = 'scaleX(0)';
        bar.getBoundingClientRect();
        bar.style.transform = '';
        bar.style.animation = 'none';
        bar.getBoundingClientRect();
        bar.style.animation = '';
        obs.unobserve(bar);
      });
    }, {threshold:0.2});
    bars.forEach(b => obs.observe(b));
  }

  // SCROLL REVEAL — refined
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduceMotion && 'IntersectionObserver' in window) {
    const selector = '.section-card, .dashboard-card, .report-card, .kpi-card, .programme-card, .project-card, .step-card, .section';
    const candidates = [...document.querySelectorAll(`#iptt-main ${selector.split(',').map(s=>`:scope ${s}`).join(',')}`)]
      .filter(el => el.getBoundingClientRect().top > window.innerHeight * 0.85);
    candidates.forEach(el => el.classList.add('iptt-reveal'));
    const revealables = document.querySelectorAll('.iptt-reveal');
    if (revealables.length) {
      document.documentElement.classList.add('iptt-js');
      const reveal = el => el.classList.add('iptt-reveal-in');
      const observer = new IntersectionObserver((entries, o) => {
        entries.forEach(entry => { if (!entry.isIntersecting) return; reveal(entry.target); o.unobserve(entry.target); });
      }, {rootMargin:'0px 0px -10% 0px', threshold:0.06});
      revealables.forEach(el => observer.observe(el));
      setTimeout(() => revealables.forEach(reveal), 3200);
    }
  }

  // SKIP LINK
  document.querySelector('.iptt-skip')?.addEventListener('click', e => {
    const main = document.querySelector('#iptt-main');
    const target = main?.querySelector('h1, h2') || main;
    if (target) { e.preventDefault(); target.tabIndex = -1; target.focus(); target.scrollIntoView({block:'start'}); }
  });

  // Add subtle parallax to welcome banner
  const banner = document.querySelector('.welcome-banner');
  if (banner && !reduceMotion) {
    window.addEventListener('scroll', () => {
      const y = window.scrollY * 0.12;
      banner.style.transform = `translateY(${Math.min(y, 12)}px)`;
    }, {passive:true});
  }
})();
