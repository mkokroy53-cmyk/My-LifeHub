const immersiveNavigation = document.querySelector('[data-immersive-navigation]');
const navigationToggle = immersiveNavigation?.querySelector('[data-nav-toggle]');
const navigationScrim = document.querySelector('[data-nav-close]');
const navigationRoot = immersiveNavigation?.querySelector('[data-nav-root]');
const navigationBack = immersiveNavigation?.querySelector('[data-nav-back]');
const navigationTitle = immersiveNavigation?.querySelector('[data-nav-title]');
const navigationSections = immersiveNavigation?.querySelectorAll('[data-nav-section]') ?? [];
const themeToggles = document.querySelectorAll('[data-theme-toggle]');
const scrollTopButton = document.querySelector('[data-scroll-top]');
const scrollProgress = document.querySelector('[data-scroll-progress]');
const portfolioSections = [...document.querySelectorAll('.portfolio-page .pf-section[id]')];
const portfolioNavLinks = [...document.querySelectorAll('.portfolio-page .pf-nav a[href^="#"]')];
const parallaxTargets = [...document.querySelectorAll('[data-parallax]')].map((element) => {
    const bounds = element.getBoundingClientRect();
    return {
        element,
        startCenter: bounds.top + bounds.height / 2,
        strength: Number(element.dataset.parallax),
    };
});
const appShell = document.querySelector('.app-shell');

document.body.classList.add('motion-ready');

navigationSections.forEach((section, index) => {
    const panel = section.querySelector('.nav-section-links');
    const summary = section.querySelector('summary');
    if (!panel || !summary) return;
    panel.id = `navigation-level-${index + 1}`;
    summary.setAttribute('aria-controls', panel.id);
});

function setNavigationLevel(section = null) {
    const activeSection = section ?? [...navigationSections].find((item) => item.open);
    navigationRoot.hidden = false;
    navigationRoot.classList.toggle('has-active-section', Boolean(activeSection));
    navigationBack.hidden = !activeSection;
    navigationTitle.textContent = activeSection?.dataset.navSection ?? 'Explore';
    navigationSections.forEach((item) => {
        if (item !== activeSection) item.open = false;
        item.hidden = Boolean(activeSection && item !== activeSection);
        item.querySelector('summary')?.setAttribute('aria-expanded', String(item.open));
    });
}

function setNavigationOpen(isOpen) {
    if (isOpen) navigationSections.forEach((section) => { section.open = false; });
    immersiveNavigation.open = isOpen;
    document.body.classList.toggle('navigation-open', isOpen);
    navigationToggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
    navigationToggle.setAttribute('aria-expanded', String(isOpen));
    if (isOpen) {
        setNavigationLevel();
        requestAnimationFrame(() => navigationSections[0]?.querySelector('summary')?.focus());
    }
}

immersiveNavigation?.addEventListener('toggle', () => {
    document.body.classList.toggle('navigation-open', immersiveNavigation.open);
    navigationToggle.setAttribute('aria-label', immersiveNavigation.open ? 'Close navigation' : 'Open navigation');
    navigationToggle.setAttribute('aria-expanded', String(immersiveNavigation.open));
});

navigationSections.forEach((section) => {
    section.addEventListener('toggle', () => {
        if (!section.open) {
            setNavigationLevel();
            return;
        }
        navigationSections.forEach((otherSection) => {
            if (otherSection !== section) otherSection.open = false;
        });
        setNavigationLevel(section);
        requestAnimationFrame(() => section.querySelector('a')?.focus());
    });
});

navigationBack?.addEventListener('click', () => {
    navigationSections.forEach((section) => { section.open = false; });
    setNavigationLevel();
    navigationSections[0]?.querySelector('summary')?.focus();
});

navigationToggle?.addEventListener('click', (event) => {
    event.preventDefault();
    setNavigationOpen(!immersiveNavigation.open);
});

navigationScrim?.addEventListener('click', () => setNavigationOpen(false));

document.addEventListener('keydown', (event) => {
    if (!immersiveNavigation?.open) return;
    if (event.key === 'Tab') {
        const focusableItems = [...immersiveNavigation.querySelectorAll('summary, a[href], button:not([disabled])')]
            .filter((element) => !element.hidden && element.getClientRects().length > 0);
        const firstItem = focusableItems[0];
        const lastItem = focusableItems.at(-1);
        if (event.shiftKey && document.activeElement === firstItem) {
            event.preventDefault();
            lastItem?.focus();
        } else if (!event.shiftKey && document.activeElement === lastItem) {
            event.preventDefault();
            firstItem?.focus();
        }
        return;
    }
    if (event.key !== 'Escape') return;
    const currentSection = [...navigationSections].find((section) => section.open);
    if (currentSection) {
        currentSection.open = false;
        setNavigationLevel();
        navigationSections[0]?.querySelector('summary')?.focus();
    } else {
        setNavigationOpen(false);
        navigationToggle.focus();
    }
});

function setTheme(isDark) {
    document.body.classList.toggle('theme-dark', isDark);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', isDark ? '#080b1b' : '#f5f7f4');
    themeToggles.forEach((toggle) => {
        toggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
        toggle.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
    });
    try {
        localStorage.setItem('lifehub-theme-v2', isDark ? 'dark' : 'light');
    } catch {
        // Theme still works for this page when storage is unavailable.
    }
}

try {
    setTheme(localStorage.getItem('lifehub-theme-v2') !== 'light');
} catch {
    setTheme(true);
}

themeToggles.forEach((toggle) => {
    toggle.addEventListener('click', () => setTheme(!document.body.classList.contains('theme-dark')));
});

immersiveNavigation?.querySelectorAll('.nav-section-links a').forEach((link) => {
    link.addEventListener('click', (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const destination = new URL(link.href, window.location.href);
        if (destination.origin !== window.location.origin) return;
        event.preventDefault();
        document.body.classList.add('navigation-leaving');
        immersiveNavigation.open = false;
        const delay = prefersReducedMotion ? 0 : 150;
        window.setTimeout(() => { window.location.assign(destination.href); }, delay);
    });
});

const revealTargets = document.querySelectorAll(
    '.quick-section, .stats-section, .dashboard-block, .quote-panel, .schedule-panel, ' +
    '.library-card, .module-entry-card, .calendar-panel, .recurring-section, .money-summary, ' +
    '.private-file-row, .entry-detail-card, .welcome-band, .workspace-tile, .stat-card, ' +
    '.learning-hero, .learning-hub-card, .learning-stat-card, .learning-card, .assignment-card, ' +
    '.nb-hero, .nb-head, .nb-card, .nb-page-row, .nb-sheet, .class-notebook-hero, ' +
    '.class-note-page, .project-card, .projects-hero, .projects-stat-card, .diary-hero, ' +
    '.diary-stat-card, .diary-block, .diary-panel, .diary-pinned-card, .diary-row, ' +
    '.finance-heading, .finance-ledger, .learning-section-nav'
);

revealTargets.forEach((element, index) => {
    element.dataset.reveal = '';
    element.style.setProperty('--reveal-delay', `${Math.min(index % 5, 4) * 55}ms`);
});

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    revealTargets.forEach((element) => element.classList.add('is-visible'));
} else {
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            revealObserver.unobserve(entry.target);
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -24px 0px' });
    revealTargets.forEach((element) => revealObserver.observe(element));
}

function animateValue(element, target, duration = 650) {
    if (prefersReducedMotion || target <= 0) {
        element.textContent = String(target);
        return;
    }
    const start = performance.now();
    const tick = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - (1 - progress) ** 3;
        element.textContent = String(Math.round(target * eased));
        if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
}

const animatedTargets = document.querySelectorAll('.stat-card > strong');
if (animatedTargets.length && !prefersReducedMotion && 'IntersectionObserver' in window) {
    const counterObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            const target = Number.parseInt(entry.target.textContent, 10);
            if (Number.isFinite(target)) animateValue(entry.target, target);
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.5 });
    animatedTargets.forEach((element) => counterObserver.observe(element));
}

const progressBars = document.querySelectorAll('.progress-track');
if (!prefersReducedMotion && 'IntersectionObserver' in window) {
    const progressObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            const progress = Number(entry.target.dataset.progress);
            const fill = entry.target.querySelector('.progress-fill');
            if (!fill || !Number.isFinite(progress)) return;
            fill.style.width = '0%';
            requestAnimationFrame(() => {
                fill.style.width = `${progress}%`;
            });
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.5 });
    progressBars.forEach((progress) => progressObserver.observe(progress));
}

document.querySelectorAll('.toast').forEach((toast) => {
    if (!toast.classList.contains('toast-success') && !toast.classList.contains('toast-info')) return;
    window.setTimeout(() => {
        toast.classList.add('is-dismissing');
        window.setTimeout(() => toast.remove(), 220);
    }, 5200);
});

document.querySelectorAll('form[method="post"] button[type="submit"]').forEach((button) => {
    // Workspace forms manage their own submit state (and fall back to a native
    // POST), so disabling the button here would break that fallback.
    if (button.form?.classList.contains('workspace-form')) return;
    button.form?.addEventListener('submit', () => {
        button.classList.add('is-loading');
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;
    });
});

function updateScrollTopVisibility() {
    scrollTopButton?.classList.toggle('is-visible', window.scrollY > 480);
    const scrollableDistance = document.documentElement.scrollHeight - window.innerHeight;
    const progress = scrollableDistance > 0 ? Math.min(window.scrollY / scrollableDistance, 1) : 0;
    scrollProgress?.style.setProperty('--scroll-progress', String(progress));

    if (portfolioSections.length && portfolioNavLinks.length) {
        const headerOffset = document.querySelector('.pf-topbar')?.getBoundingClientRect().height ?? 0;
        const activeSection = portfolioSections.reduce((active, section) => {
            return section.getBoundingClientRect().top <= headerOffset + 120 ? section : active;
        }, null);
        portfolioNavLinks.forEach((link) => {
            const isActive = link.hash === (activeSection ? `#${activeSection.id}` : '');
            if (isActive) {
                link.classList.add('is-active');
                link.setAttribute('aria-current', 'location');
            } else {
                link.classList.remove('is-active');
                link.removeAttribute('aria-current');
            }
        });
    }
}

function updateScrollMotion() {
    if (prefersReducedMotion) return;
    parallaxTargets.forEach(({ element, startCenter, strength }) => {
        const bounds = element.getBoundingClientRect();
        const currentCenter = bounds.top + bounds.height / 2;
        const offset = Math.max(-32, Math.min(32, (startCenter - currentCenter) * strength));
        element.style.setProperty('--parallax-offset', `${offset.toFixed(2)}px`);
    });

    if (appShell) {
        const ambientOffset = Math.min(window.scrollY * 0.035, 54);
        appShell.style.setProperty('--ambient-offset', `${ambientOffset.toFixed(2)}px`);
    }
}

let scrollUpdatePending = false;
window.addEventListener('scroll', () => {
    if (scrollUpdatePending) return;
    scrollUpdatePending = true;
    window.requestAnimationFrame(() => {
        updateScrollTopVisibility();
        updateScrollMotion();
        scrollUpdatePending = false;
    });
}, { passive: true });
window.addEventListener('resize', () => {
    updateScrollTopVisibility();
    updateScrollMotion();
}, { passive: true });
updateScrollTopVisibility();
updateScrollMotion();
scrollTopButton?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' }));

/* ==========================================================================
   HISTORY NAVIGATION (back / forward)
   ========================================================================== */
const historyBackButton = document.querySelector('[data-history-back]');
const historyForwardButton = document.querySelector('[data-history-forward]');

historyBackButton?.addEventListener('click', () => {
    document.body.classList.add('history-leaving');
    window.history.back();
});

historyForwardButton?.addEventListener('click', () => {
    document.body.classList.add('history-leaving');
    window.history.forward();
});

/* Keyboard shortcuts: Alt+Left / Alt+Right */
document.addEventListener('keydown', (event) => {
    if (!event.altKey) return;
    if (event.key === 'ArrowLeft') {
        event.preventDefault();
        window.history.back();
    } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        window.history.forward();
    }
});

/* ==========================================================================
   POST/SAVE NAVIGATION
   A normal form POST follows the server's redirect with a *push*, so the
   just-submitted form stays in history and Back returns to the blank form.
   Instead we post with fetch, read the destination the server chose, and
   navigate with replace() — the form entry is overwritten, so Back goes to
   the page the writer came from rather than the form they already used.
   ========================================================================== */
document.querySelectorAll('form.workspace-form').forEach((form) => {
    if ((form.method || '').toLowerCase() !== 'post') return;

    form.addEventListener('submit', async (event) => {
        // Let the browser handle it if anything about fetch is unavailable.
        if (!window.fetch || !window.FormData) return;
        event.preventDefault();

        const submitter = form.querySelector('button[type="submit"], input[type="submit"]');
        submitter?.classList.add('is-loading');
        submitter?.setAttribute('aria-busy', 'true');

        try {
            const response = await fetch(form.action || window.location.href, {
                method: 'POST',
                body: new FormData(form),
                credentials: 'same-origin',
                redirect: 'follow',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });

            if (response.redirected && response.url) {
                // Saved successfully: replace the form's history entry.
                window.location.replace(response.url);
                return;
            }

            // Re-render errors in place (invalid form, 422/200 with errors).
            const html = await response.text();
            const parsed = new DOMParser().parseFromString(html, 'text/html');
            const replacement = parsed.querySelector('form.workspace-form');
            if (replacement) {
                form.replaceWith(document.adoptNode(replacement));
                window.scrollTo({ top: 0, behavior: 'auto' });
                return;
            }
            window.location.reload();
        } catch {
            submitter?.classList.remove('is-loading');
            submitter?.removeAttribute('aria-busy');
            form.submit(); // fall back to a normal POST
        }
    });
});

/* When a page is restored from the browser's back/forward cache, refresh it so
   a stale, already-submitted form is never shown again. */
window.addEventListener('pageshow', (event) => {
    if (event.persisted) window.location.reload();
});

/* ==========================================================================
   MIDNIGHT ROLLOVER
   Dates are rendered server-side in the visitor's timezone, so a page opened
   just before midnight would still show yesterday until reloaded. This watches
   for the local calendar day to change and reloads once, so "today", streaks
   and the calendar always agree with the real date the moment it ticks over.
   ========================================================================== */
(() => {
    const dateStamp = document.querySelector('[data-current-date]');
    if (!dateStamp) return;

    const todayKey = () => {
        const now = new Date();
        return `${now.getFullYear()}-${now.getMonth() + 1}-${now.getDate()}`;
    };

    let currentDay = todayKey();
    // Check every 20s: cheap, and catches the rollover within seconds.
    window.setInterval(() => {
        const nextDay = todayKey();
        if (nextDay === currentDay) return;
        currentDay = nextDay;
        window.location.reload();
    }, 20000);
})();

/* Reflect a subtle loading state while navigating between pages */
window.addEventListener('pageshow', () => document.body.classList.remove('history-leaving'));

/* ==========================================================================
   DIARY / LEARNING / QUOTE ENHANCEMENTS
   ========================================================================== */
document.querySelectorAll('[data-quote-refresh]').forEach((button) => {
    button.addEventListener('click', () => {
        button.classList.add('is-loading');
        window.location.href = button.dataset.quoteRefresh;
    });
});

document.querySelectorAll('[data-filter-select]').forEach((select) => {
    select.addEventListener('change', () => select.form?.submit());
});

/* Auto-grow diary textarea */
document.querySelectorAll('textarea[data-auto-grow]').forEach((textarea) => {
    const grow = () => {
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.max(textarea.scrollHeight, 180)}px`;
    };
    textarea.addEventListener('input', grow);
    grow();
});

/* Quote of the day — cycles through the saved quotes without a page reload */
document.querySelectorAll('[data-quote-shuffle]').forEach((button) => {
    const panel = button.closest('.quote-spotlight');
    const textNode = panel?.querySelector('.quote-text-inner');
    const authorNode = panel?.querySelector('.quote-spotlight-author');
    let quotes = [];

    const shuffleUrl = button.dataset.quoteShuffleUrl;
    if (!shuffleUrl) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const loadQuotes = () => {
        if (quotes.length) return Promise.resolve(quotes);
        return fetch(shuffleUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then((response) => (response.ok ? response.json() : null))
            .then((data) => {
                quotes = Array.isArray(data?.quotes) ? data.quotes : [];
                return quotes;
            })
            .catch(() => []);
    };

    const paint = (quote) => {
        if (!textNode || !quote) return;
        const apply = () => {
            textNode.textContent = quote.text;
            textNode.classList.remove('is-swapping');
            if (authorNode) authorNode.textContent = quote.author || 'Saved by you';
            if (!reducedMotion) {
                // Restart the entrance animation so every swap rises in cleanly.
                textNode.style.animation = 'none';
                void textNode.offsetWidth;
                textNode.style.animation = '';
            }
        };
        if (reducedMotion) { apply(); return; }
        textNode.classList.add('is-swapping');
        window.setTimeout(apply, 320);
    };

    const showAnother = () => {
        if (!textNode) return Promise.resolve();
        return loadQuotes().then((list) => {
            if (!list.length) return;
            const current = textNode.textContent.trim();
            const pool = list.filter((item) => item.text.trim() !== current);
            const candidates = pool.length ? pool : list;
            const choice = candidates[Math.floor(Math.random() * candidates.length)];
            paint(choice);
        });
    };

    button.addEventListener('click', () => {
        if (button.classList.contains('is-loading')) return;
        button.classList.add('is-loading');
        showAnother().finally(() => {
            window.setTimeout(() => button.classList.remove('is-loading'), 520);
        });
    });

    // Gentle auto-cycle: drifts to a new quote, but never fights the reader.
    const interval = Number(panel?.dataset.quoteAutocycle || 0);
    if (interval > 0 && !reducedMotion) {
        let timer = null;
        const start = () => {
            stop();
            timer = window.setInterval(() => {
                if (document.hidden || button.classList.contains('is-loading')) return;
                showAnother();
            }, interval);
        };
        const stop = () => {
            if (timer !== null) { window.clearInterval(timer); timer = null; }
        };
        // Pause while the reader is hovering, focused, or on another tab.
        panel?.addEventListener('mouseenter', stop);
        panel?.addEventListener('mouseleave', start);
        panel?.addEventListener('focusin', stop);
        panel?.addEventListener('focusout', start);
        document.addEventListener('visibilitychange', () => (document.hidden ? stop() : start()));
        // Only animate once the panel is actually on screen.
        if ('IntersectionObserver' in window) {
            new IntersectionObserver((entries) => {
                entries.forEach((entry) => (entry.isIntersecting ? start() : stop()));
            }, { threshold: .35 }).observe(panel);
        } else {
            start();
        }
    }
});

/* =====================================================================
   Public portfolio — sign-in overlay
   The portfolio is readable without an account; the credential form opens
   on demand. If a visitor was bounced here from a private URL, the modal
   opens automatically and ?next= returns them to where they were headed.
   ===================================================================== */
(() => {
    const overlay = document.querySelector('[data-login-overlay]');
    if (!overlay) return;

    const dialog = overlay.querySelector('.login-dialog');
    const openers = document.querySelectorAll('[data-login-open]');
    const closers = document.querySelectorAll('[data-login-close]');
    const backdrop = overlay.querySelector('[data-login-backdrop]');
    const usernameField = overlay.querySelector('input[name="username"]');
    let lastFocused = null;

    const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';

    const isOpen = () => !overlay.hasAttribute('hidden');

    function openLogin() {
        if (isOpen()) return;
        lastFocused = document.activeElement;
        overlay.removeAttribute('hidden');
        document.body.classList.add('login-open');
        // Focus the first empty field so the visitor can start typing at once.
        window.requestAnimationFrame(() => {
            const target = usernameField && !usernameField.value
                ? usernameField
                : overlay.querySelector(FOCUSABLE);
            target?.focus();
        });
    }

    function closeLogin() {
        if (!isOpen()) return;
        overlay.setAttribute('hidden', '');
        document.body.classList.remove('login-open');
        if (lastFocused && typeof lastFocused.focus === 'function') lastFocused.focus();
    }

    openers.forEach((button) => button.addEventListener('click', openLogin));
    closers.forEach((button) => button.addEventListener('click', closeLogin));
    backdrop?.addEventListener('click', closeLogin);

    // Escape closes; Tab is trapped inside the dialog while it is open.
    overlay.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { event.preventDefault(); closeLogin(); return; }
        if (event.key !== 'Tab' || !dialog) return;
        const items = Array.from(dialog.querySelectorAll(FOCUSABLE)).filter((el) => el.offsetParent !== null);
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });

    // Arrived from a private page while signed out — ask for credentials immediately.
    const bounced = document.body.dataset.portfolioLogin === '1';
    const hasError = document.querySelector('.login-dialog .form-alert');
    if (bounced || hasError) openLogin();
})();

/* =====================================================================
   Public portfolio — pop feature cards into view as they scroll
   ===================================================================== */
(() => {
    const revealItems = document.querySelectorAll([
        '.portfolio-page .pf-section-head',
        '.portfolio-page .pf-hero-copy',
        '.portfolio-page .pf-hero-portrait',
        '.portfolio-page .pf-about-grid',
        '.portfolio-page .pf-focus-tag',
        '.portfolio-page .pf-skill-card',
        '.portfolio-page .pf-work-card',
        '.portfolio-page .pf-design-showcase-head',
        '.portfolio-page .pf-design-card',
        '.portfolio-page .pf-contact-card',
    ].join(','));
    if (!revealItems.length) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || !('IntersectionObserver' in window)) return;

    document.body.classList.add('pf-reveal-ready');
    const reveal = (item) => item.classList.add('is-visible');

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            reveal(entry.target);
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

    // Each element gets the motion that suits its role: headings rise, cards
    // zoom, and paired columns slide in from their own side.
    const variantFor = (item) => {
        if (item.matches('.pf-section-head, .pf-about-lede, .pf-about-body, .pf-design-showcase-head')) return 'pf-reveal-rise';
        if (item.matches('.pf-skill-card, .pf-work-card, .pf-design-card, .pf-contact-card')) return 'pf-reveal-zoom';
        if (item.matches('.pf-hero-copy')) return 'pf-reveal-left';
        if (item.matches('.pf-hero-portrait')) return 'pf-reveal-right';
        return '';
    };

    revealItems.forEach((item) => {
        item.classList.add('pf-scroll-item');
        const variant = variantFor(item);
        if (variant) item.classList.add(variant);
        const siblingIndex = Array.prototype.indexOf.call(item.parentElement.children, item);
        item.style.setProperty('--pf-reveal-delay', `${Math.min(siblingIndex, 5) * 75}ms`);
        if (item.getBoundingClientRect().top < window.innerHeight) reveal(item);
        observer.observe(item);
    });
    updateScrollMotion();
})();

/* =====================================================================
   PORTFOLIO — IMMERSIVE SCROLL ENGINE
   One rAF loop drives every scroll-linked effect on the public page:
   layered parallax, scroll-driven transforms, the hero hand-off and the
   section scene changes. Everything is measured once per frame from
   getBoundingClientRect, so nothing depends on cached offsets going stale
   after a resize or a font swap.

   The whole module is inert unless the page is the portfolio, and it
   bails out entirely when the visitor prefers reduced motion.
   ===================================================================== */
(() => {
    const page = document.querySelector('.portfolio-page');
    if (!page) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) return;

    const hero = page.querySelector('.pf-hero');
    const sections = [...page.querySelectorAll('.pf-section')];
    const rotateTargets = [...page.querySelectorAll('[data-scroll-rotate]')];
    const zoomTargets = [...page.querySelectorAll('[data-scroll-zoom]')];
    const driftTargets = [...page.querySelectorAll('[data-scroll-drift]')];
    const portrait = page.querySelector('.pf-portrait-frame');
    const designCards = [...page.querySelectorAll('.pf-design-card')];
    const parallaxLayers = [...page.querySelectorAll('[data-parallax]')].map((element) => ({
        element,
        strength: Number(element.dataset.parallax) || 0,
    }));

    // How far an element has travelled through the viewport: 0 when its top
    // edge is at the bottom of the screen, 1 when its bottom edge has left.
    const progressOf = (element) => {
        const rect = element.getBoundingClientRect();
        const span = window.innerHeight + rect.height;
        if (span <= 0) return 0;
        return Math.min(1, Math.max(0, (window.innerHeight - rect.top) / span));
    };

    // -1 → +1 as the element crosses the middle of the screen.
    const centredOf = (element) => progressOf(element) * 2 - 1;

    let frame = 0;
    const render = () => {
        frame = 0;
        const viewport = window.innerHeight;

        // Hero hand-off: fully present at the top, receding as it leaves.
        if (hero) {
            const travelled = Math.min(1, Math.max(0, window.scrollY / Math.max(hero.offsetHeight * 0.9, 1)));
            page.style.setProperty('--pf-hero-fade', travelled.toFixed(3));
        }

        // Layered parallax. Each layer moves at its own rate, and the three
        // depth variables feed the ambient light so it drifts with the page.
        parallaxLayers.forEach(({ element, strength }) => {
            const offset = Math.max(-70, Math.min(70, -centredOf(element) * strength * 120));
            element.style.setProperty('--parallax-offset', `${offset.toFixed(2)}px`);
        });
        page.style.setProperty('--pf-depth-1', `${(window.scrollY * 0.06).toFixed(1)}px`);
        page.style.setProperty('--pf-depth-2', `${(window.scrollY * 0.12).toFixed(1)}px`);

        // Scroll-driven transforms.
        rotateTargets.forEach((element) => {
            const amount = Number(element.dataset.scrollRotate) || 0;
            element.style.setProperty('--scroll-rotate', (centredOf(element) * amount).toFixed(2));
        });
        zoomTargets.forEach((element) => {
            const amount = Number(element.dataset.scrollZoom) || 0;
            element.style.setProperty('--scroll-zoom', (centredOf(element) * amount).toFixed(3));
        });
        driftTargets.forEach((element) => {
            const amount = Number(element.dataset.scrollDrift) || 0;
            element.style.setProperty('--scroll-drift', (centredOf(element) * amount).toFixed(1));
        });

        if (portrait) {
            const tilt = centredOf(portrait);
            portrait.style.setProperty('--scroll-tilt', (tilt * 4).toFixed(2));
            portrait.style.setProperty('--scroll-sheen', ((tilt + 1) / 2).toFixed(3));
        }

        // Gallery cards lift and straighten as they approach the centre.
        designCards.forEach((card) => {
            const centred = centredOf(card);
            card.style.setProperty('--card-lift', (Math.abs(centred) * 14).toFixed(1));
            card.style.setProperty('--card-tilt', (centred * 1.6).toFixed(2));
        });

        // Section scene changes: a section is "in view" while it occupies the
        // middle band of the screen, which drives its glow and seam.
        sections.forEach((section) => {
            const rect = section.getBoundingClientRect();
            const inView = rect.top < viewport * 0.82 && rect.bottom > viewport * 0.18;
            section.classList.toggle('is-in-view', inView);
        });
    };

    const schedule = () => {
        if (frame) return;
        frame = window.requestAnimationFrame(render);
    };

    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule, { passive: true });
    window.addEventListener('load', schedule);
    render();

    // Pointer-tracked light on cards. Cheap: one listener per card, and the
    // values are only written while the pointer is actually over it.
    page.querySelectorAll('.pf-skill-card, .pf-work-card').forEach((card) => {
        card.addEventListener('pointermove', (event) => {
            const rect = card.getBoundingClientRect();
            card.style.setProperty('--pointer-x', `${event.clientX - rect.left}px`);
            card.style.setProperty('--pointer-y', `${event.clientY - rect.top}px`);
        }, { passive: true });
    });
})();
