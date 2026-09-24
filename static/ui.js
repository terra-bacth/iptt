/* ==========================================================================
   IPTT Cinematic UI Engine v12
   - Dual Theme (Cinematic Obsidian Dark / Enterprise Crisp Light)
   - Spotlight Command Palette (⌘K / Ctrl+K)
   - Smooth Animated Collapsibles
   - Real-time Table Filtering
   - Responsive Glass Navigation
   - Accessible Micro-interactions
   ========================================================================== */

(() => {
  'use strict';

  /* ==========================================================================
     1. THEME ENGINE (Dark / Light with LocalStorage persistence)
     ========================================================================== */
  const THEME_KEY = 'iptt-theme';

  function getPreferredTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    // Default to cinematic dark, or system preference
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
    document.querySelectorAll('.iptt-theme-toggle').forEach(btn => {
      btn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
      btn.setAttribute('title', theme === 'dark' ? 'Switch to Enterprise Light mode' : 'Switch to Cinematic Dark mode');
      btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    });
  }

  let lastToggleTime = 0;
  function toggleTheme() {
    const now = Date.now();
    if (now - lastToggleTime < 250) return;
    lastToggleTime = now;
    const current = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
  }

  // Expose globally for inline event handlers and external callers
  window.ipttToggleTheme = toggleTheme;
  window.toggleTheme = toggleTheme;
  window.applyTheme = applyTheme;

  // Apply immediately on load
  const initialTheme = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
  applyTheme(initialTheme);

  // Re-sync all buttons once DOM is fully parsed
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      applyTheme(document.documentElement.getAttribute('data-theme') || getPreferredTheme());
    });
  }

  // Global click event delegation for ALL theme toggles anywhere in the DOM (top-nav, login, etc.)
  document.addEventListener('click', e => {
    const btn = e.target.closest('.iptt-theme-toggle');
    if (btn) {
      e.preventDefault();
      toggleTheme();
    }
  });

  /* ==========================================================================
     2. NAVIGATION & RESPONSIVE DRAWER
     ========================================================================== */
  const currentPath = location.pathname.replace(/\/$/, '') || '/';

  document.querySelectorAll('.top-nav').forEach((nav, index) => {
    nav.setAttribute('role', 'navigation');
    nav.setAttribute('aria-label', 'Primary');

    // Highlight active link
    nav.querySelectorAll('a:not(.iptt-brand)').forEach(link => {
      try {
        const linkPath = new URL(link.href).pathname.replace(/\/$/, '') || '/';
        if (linkPath === currentPath) {
          link.setAttribute('aria-current', 'page');
        }
      } catch (e) {}
    });

    // Mobile drawer toggle
    const menuToggle = nav.querySelector('.iptt-menu-toggle');
    const navItems = nav.querySelector('.iptt-nav-items, .nav-links');
    if (menuToggle && navItems) {
      menuToggle.addEventListener('click', () => {
        const isOpen = navItems.classList.toggle('iptt-nav-open');
        menuToggle.setAttribute('aria-expanded', String(isOpen));
      });
    }
  });

  /* ==========================================================================
     3. COMMAND PALETTE (⌘K / Ctrl+K)
     ========================================================================== */
  const ALL_COMMANDS = [
    { title: 'Home Workspace', category: 'Navigation', icon: '🏠', url: '/home' },
    { title: 'Programmes Portfolio', category: 'Navigation', icon: '📦', url: '/programmes' },
    { title: 'Governance Dashboard', category: 'Dashboards', icon: '📊', url: '/dashboard' },
    { title: 'Circle Intelligence', category: 'Dashboards', icon: '🌍', url: '/circle-dashboard' },
    { title: 'Security Credentials', category: 'Settings', icon: '🔒', url: '/profile' },
    { title: 'User Management', category: 'Admin', icon: '👥', url: '/users', adminOnly: true },
    { title: 'Audit Logs', category: 'Admin', icon: '📜', url: '/audit-logs', adminOnly: true },
    { title: 'Toggle Cinematic / Light Theme', category: 'Actions', icon: '🌓', action: toggleTheme },
    { title: 'Sign Out Session', category: 'Account', icon: '🚪', url: '/logout' }
  ];

  let dynamicCommands = [];
  let dynamicLoaded = false;

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  async function loadSearchIndex() {
    if (dynamicLoaded) return;
    try {
      const res = await fetch('/api/search-index');
      if (res.ok) {
        const items = await res.json();
        if (Array.isArray(items)) {
          dynamicCommands = items;
          dynamicLoaded = true;
          if (cmdkBackdrop && cmdkBackdrop.classList.contains('open')) {
            updateFilteredCommands();
            renderCommandList();
          }
        }
      }
    } catch (e) {}
  }

  function getAvailableCommands() {
    const nav = document.querySelector('.top-nav');
    const role = (nav?.getAttribute('data-user-role') || '').toLowerCase();
    const hasAdminLinks = !!document.querySelector('a[href="/users"], a[href="/audit-logs"]');
    const isAdmin = role === 'admin' || hasAdminLinks;

    const base = ALL_COMMANDS.filter(cmd => !cmd.adminOnly || isAdmin);
    return [...base, ...dynamicCommands];
  }

  let cmdkBackdrop = null;
  let cmdkInput = null;
  let cmdkList = null;
  let selectedIndex = 0;
  let filteredCommands = [];

  function updateFilteredCommands() {
    const q = (cmdkInput?.value || '').toLowerCase().trim();
    const available = getAvailableCommands();
    if (!q) {
      filteredCommands = [...available];
    } else {
      filteredCommands = available.filter(c =>
        c.title.toLowerCase().includes(q) ||
        (c.category && c.category.toLowerCase().includes(q)) ||
        (c.description && c.description.toLowerCase().includes(q))
      );
    }
    selectedIndex = 0;
  }

  function createCommandPalette() {
    if (document.querySelector('.iptt-cmdk-backdrop')) return;

    cmdkBackdrop = document.createElement('div');
    cmdkBackdrop.className = 'iptt-cmdk-backdrop';
    cmdkBackdrop.setAttribute('role', 'dialog');
    cmdkBackdrop.setAttribute('aria-modal', 'true');
    cmdkBackdrop.setAttribute('aria-label', 'Command Palette');

    cmdkBackdrop.innerHTML = `
      <div class="iptt-cmdk-modal">
        <div class="iptt-cmdk-input-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input type="text" class="iptt-cmdk-input" placeholder="Search programmes, projects, tools... (Esc to close)" autocomplete="off" spellcheck="false">
        </div>
        <div class="iptt-cmdk-list" role="listbox"></div>
        <div class="iptt-cmdk-footer">
          <span>Navigate with <kbd>↑</kbd> <kbd>↓</kbd></span>
          <span>Select with <kbd>Enter</kbd></span>
        </div>
      </div>
    `;

    document.body.appendChild(cmdkBackdrop);
    cmdkInput = cmdkBackdrop.querySelector('.iptt-cmdk-input');
    cmdkList = cmdkBackdrop.querySelector('.iptt-cmdk-list');

    // Click outside to close
    cmdkBackdrop.addEventListener('click', e => {
      if (e.target === cmdkBackdrop) closeCommandPalette();
    });

    // Search filter
    cmdkInput.addEventListener('input', () => {
      updateFilteredCommands();
      renderCommandList();
    });

    // Keyboard navigation
    cmdkInput.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % Math.max(1, filteredCommands.length);
        highlightSelectedItem();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + filteredCommands.length) % Math.max(1, filteredCommands.length);
        highlightSelectedItem();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        executeSelectedItem();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        closeCommandPalette();
      }
    });
  }

  function renderCommandList() {
    if (!cmdkList) return;
    if (filteredCommands.length === 0) {
      cmdkList.innerHTML = `<div style="padding:24px; text-align:center; color:var(--muted); font-size:13px">No commands, projects, or programmes found</div>`;
      return;
    }

    cmdkList.innerHTML = filteredCommands.map((cmd, i) => `
      <div class="iptt-cmdk-item ${i === selectedIndex ? 'selected' : ''}" role="option" data-index="${i}">
        <div class="iptt-cmdk-item-left">
          <span style="font-size: 16px; line-height: 1; flex-shrink: 0;">${cmd.icon}</span>
          <div style="display: flex; flex-direction: column; gap: 2px; min-width: 0;">
            <strong style="color: var(--text); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(cmd.title)}</strong>
            ${cmd.description ? `<span style="font-size: 11px; color: var(--muted);">${escapeHtml(cmd.description)}</span>` : ''}
          </div>
        </div>
        <span class="iptt-cmdk-item-badge badge-${(cmd.category || '').toLowerCase()}">${cmd.category}</span>
      </div>
    `).join('');

    cmdkList.querySelectorAll('.iptt-cmdk-item').forEach(el => {
      el.addEventListener('click', () => {
        selectedIndex = parseInt(el.getAttribute('data-index'), 10);
        executeSelectedItem();
      });
      el.addEventListener('mouseenter', () => {
        selectedIndex = parseInt(el.getAttribute('data-index'), 10);
        highlightSelectedItem();
      });
    });
  }

  function highlightSelectedItem() {
    if (!cmdkList) return;
    const items = cmdkList.querySelectorAll('.iptt-cmdk-item');
    items.forEach((item, i) => {
      item.classList.toggle('selected', i === selectedIndex);
      if (i === selectedIndex) {
        item.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  function executeSelectedItem() {
    const cmd = filteredCommands[selectedIndex];
    if (!cmd) return;
    closeCommandPalette();
    if (cmd.action) {
      cmd.action();
    } else if (cmd.url) {
      location.href = cmd.url;
    }
  }

  function openCommandPalette() {
    createCommandPalette();
    loadSearchIndex();
    cmdkBackdrop.classList.add('open');
    updateFilteredCommands();
    cmdkInput.value = '';
    renderCommandList();
    setTimeout(() => cmdkInput.focus(), 50);
  }

  function closeCommandPalette() {
    if (cmdkBackdrop) cmdkBackdrop.classList.remove('open');
  }

  // Global Shortcut listener (⌘K / Ctrl+K / /)
  window.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      if (cmdkBackdrop && cmdkBackdrop.classList.contains('open')) {
        closeCommandPalette();
      } else {
        openCommandPalette();
      }
    } else if (e.key === 'Escape' && cmdkBackdrop && cmdkBackdrop.classList.contains('open')) {
      closeCommandPalette();
    }
  });

  // Wire trigger buttons
  document.querySelectorAll('.iptt-cmdk-trigger').forEach(btn => {
    btn.addEventListener('click', e => {
      e.preventDefault();
      openCommandPalette();
    });
  });

  /* ==========================================================================
     4. SMOOTH ANIMATED COLLAPSIBLE SECTIONS
     ========================================================================== */
  let lastCollapsibleToggle = 0;

  function doCollapsibleToggle(header, content, icon) {
    if (!content) return;
    const now = Date.now();
    if (now - lastCollapsibleToggle < 180) return;
    lastCollapsibleToggle = now;

    const isOpen = content.classList.toggle('active');
    if (header) {
      header.classList.toggle('active', isOpen);
      header.setAttribute('aria-expanded', String(isOpen));
      if (!icon) icon = header.querySelector('.collapsible-icon, .toggle-icon');
      if (icon) {
        icon.textContent = isOpen ? '−' : '+';
        icon.style.transform = isOpen ? 'rotate(180deg)' : 'none';
      }
    }
  }

  function setupCollapsible(header, content, icon) {
    if (!header || !content) return;
    header.setAttribute('role', 'button');
    header.setAttribute('tabindex', '0');
    header.setAttribute('aria-expanded', content.classList.contains('active') ? 'true' : 'false');

    // Remove inline onclick to completely prevent double-firing
    if (header.hasAttribute('onclick')) {
      header.removeAttribute('onclick');
    }

    header.addEventListener('click', (e) => {
      e.preventDefault();
      doCollapsibleToggle(header, content, icon);
    });

    header.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        doCollapsibleToggle(header, content, icon);
      }
    });
  }

  document.querySelectorAll('.collapsible-header, .section-header').forEach(h => {
    const id = h.getAttribute('onclick')?.match(/toggleSection\(['"]([^'"]+)['"]\)/)?.[1];
    let content = id ? document.getElementById(id) : h.nextElementSibling;
    if (!content || (!content.classList.contains('collapsible-content') && !content.classList.contains('section-content'))) {
      content = h.parentElement?.querySelector('.collapsible-content, .section-content') || h.nextElementSibling;
    }
    const icon = h.querySelector('.collapsible-icon, .toggle-icon');
    setupCollapsible(h, content, icon);
  });

  // Global toggleSection backwards compatibility
  window.toggleSection = function(target) {
    let section = null;
    let header = null;

    if (typeof target === 'string') {
      section = document.getElementById(target);
      header = section?.previousElementSibling?.classList.contains('collapsible-header')
        ? section.previousElementSibling
        : document.querySelector(`[onclick*="${target}"], [data-target="${target}"]`);
    } else if (target instanceof HTMLElement) {
      section = target;
      header = target.previousElementSibling;
    }

    if (!section) return;
    const icon = header ? header.querySelector('.collapsible-icon, .toggle-icon') : null;
    doCollapsibleToggle(header, section, icon);
  };

  /* ==========================================================================
     5. UNIVERSAL REAL-TIME TABLE SEARCH
     ========================================================================== */
  document.querySelectorAll('input[data-table-target]').forEach(input => {
    const tableId = input.getAttribute('data-table-target');
    const table = document.getElementById(tableId);
    if (!table) return;

    input.addEventListener('input', e => {
      const q = e.target.value.toLowerCase().trim();
      const rows = table.querySelectorAll('tbody tr, tr:not(:first-child)');
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });
    });
  });

  /* ==========================================================================
     6. RESPONSIVE TABLE WRAPPER
     ========================================================================== */
  document.querySelectorAll('table').forEach(table => {
    const parent = table.parentElement;
    if (parent.classList.contains('iptt-table-scroll')) return;
    const wrapper = document.createElement('div');
    wrapper.className = 'iptt-table-scroll';
    table.before(wrapper);
    wrapper.appendChild(table);
  });

  /* ==========================================================================
     7. ANIMATED PROGRESS BARS & SCROLL REVEAL
     ========================================================================== */
  if ('IntersectionObserver' in window) {
    const barObserver = new IntersectionObserver((entries, obs) => {
      entries.forEach(e => {
        if (!e.isIntersecting) return;
        const bar = e.target;
        const targetWidth = bar.style.width;
        if (!targetWidth || targetWidth === '0%' || targetWidth === '0px' || parseFloat(targetWidth) === 0) {
          bar.style.width = '0%';
          obs.unobserve(bar);
          return;
        }
        bar.style.width = '0%';
        void bar.offsetWidth; // trigger reflow
        bar.style.width = targetWidth;
        obs.unobserve(bar);
      });
    }, { threshold: 0.15 });

    document.querySelectorAll('.progress-bar').forEach(b => barObserver.observe(b));
  }

  // 5d. Scroll-reveal enhancement with guaranteed fallback
  const revealables = document.querySelectorAll('.iptt-reveal');
  const reveal = el => el.classList.add('iptt-reveal-in');
  if ('IntersectionObserver' in window) {
    const obs = new IntersectionObserver((entries, o) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          reveal(e.target);
          o.unobserve(e.target);
        }
      });
    });
    revealables.forEach(el => obs.observe(el));
  } else {
    revealables.forEach(reveal);
  }
  setTimeout(() => revealables.forEach(reveal), 1200);

  // Preload search index in background if top nav is present
  if (document.querySelector('.top-nav')) {
    setTimeout(loadSearchIndex, 100);
  }

  // Generic Show More toggle helper
  window.toggle = function(id) {
    const el = document.getElementById('more-' + id);
    if (!el) return;
    const isHidden = el.style.display === 'none';
    el.style.display = isHidden ? 'block' : 'none';
  };

  /* ==========================================================================
     8. SEGMENTED TABS CONTROLLER (Deep-linking & Accessible Switching)
     ========================================================================== */
  function initSegmentedTabs() {
    const tabGroups = document.querySelectorAll('.iptt-segmented-tabs-wrapper');
    if (!tabGroups.length) return;

    tabGroups.forEach(wrapper => {
      const tabs = wrapper.querySelectorAll('.iptt-tab-btn');
      tabs.forEach(tab => {
        tab.addEventListener('click', e => {
          e.preventDefault();
          const targetId = tab.dataset.tabTarget;
          if (!targetId) return;

          // Activate clicked tab button
          tabs.forEach(t => {
            t.classList.remove('active');
            t.setAttribute('aria-selected', 'false');
          });
          tab.classList.add('active');
          tab.setAttribute('aria-selected', 'true');

          // Activate matching pane
          const parentContainer = wrapper.parentElement;
          const panes = parentContainer.querySelectorAll('.iptt-tab-pane');
          panes.forEach(pane => {
            if (pane.id === targetId) {
              pane.classList.add('active');
            } else {
              pane.classList.remove('active');
            }
          });

          // Trigger resize event to re-layout any charts inside the active tab
          window.dispatchEvent(new Event('resize'));

          // Sync URL hash for deep-linking
          if (history.replaceState) {
            history.replaceState(null, '', '#' + targetId);
          }
        });
      });
    });

    function syncTabFromHash() {
      const hash = (location.hash || '').replace(/^#/, '');
      if (hash) {
        const activeTab = document.querySelector(`.iptt-tab-btn[data-tab-target="${hash}"]`);
        if (activeTab) {
          activeTab.click();
        }
      }
    }

    syncTabFromHash();
    window.addEventListener('hashchange', syncTabFromHash);
  }

  /* ==========================================================================
     9. QUICK KPI & SECTION NAVIGATION ENGINE
     ========================================================================== */
  window.ipttSwitchTab = function(targetId) {
    if (!targetId) return;
    const cleanId = targetId.replace(/^#/, '');
    const tabBtn = document.querySelector(`.iptt-tab-btn[data-tab-target="${cleanId}"]`);
    if (tabBtn) {
      tabBtn.click();
    }
    setTimeout(() => {
      const pane = document.getElementById(cleanId);
      if (pane) {
        pane.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 50);
  };

  window.ipttToggleFloatingNav = function() {
    const dock = document.getElementById('floatingQuickNav');
    const menu = document.getElementById('floatingQuickNavMenu');
    const btn = dock?.querySelector('.floating-quicknav-btn');
    if (!menu) return;
    const isOpen = menu.classList.toggle('open');
    if (btn) btn.setAttribute('aria-expanded', String(isOpen));
  };

  window.ipttCloseFloatingNav = function() {
    const menu = document.getElementById('floatingQuickNavMenu');
    const dock = document.getElementById('floatingQuickNav');
    const btn = dock?.querySelector('.floating-quicknav-btn');
    if (menu) menu.classList.remove('open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  };

  document.addEventListener('click', e => {
    const dock = document.getElementById('floatingQuickNav');
    if (dock && !dock.contains(e.target)) {
      window.ipttCloseFloatingNav();
    }
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSegmentedTabs);
  } else {
    initSegmentedTabs();
  }

})();
