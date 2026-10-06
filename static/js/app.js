const immersiveNavigation = document.querySelector('[data-immersive-navigation]');
const navigationToggle = immersiveNavigation?.querySelector('[data-nav-toggle]');
const navigationScrim = document.querySelector('[data-nav-close]');
const navigationRoot = immersiveNavigation?.querySelector('[data-nav-root]');
const navigationBack = immersiveNavigation?.querySelector('[data-nav-back]');
const navigationTitle = immersiveNavigation?.querySelector('[data-nav-title]');
const navigationSections = immersiveNavigation?.querySelectorAll('[data-nav-section]') ?? [];
const themeToggles = document.querySelectorAll('[data-theme-toggle]');
const scrollTopButton = document.querySelector('[data-scroll-top]');

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
    '.quick-section, .stats-section, .dashboard-block, .quote-panel, .schedule-panel, .library-card, .module-entry-card, .calendar-panel, .recurring-section, .money-summary, .private-file-row, .entry-detail-card'
);

revealTargets.forEach((element, index) => {
    element.dataset.reveal = '';
    element.style.setProperty('--reveal-delay', `${Math.min(index % 5, 4) * 55}ms`);
});

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    revealTargets.forEach((element) => element.classList.add('is-visible'));
} else {
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
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
    button.form?.addEventListener('submit', () => {
        button.classList.add('is-loading');
        button.setAttribute('aria-busy', 'true');
        button.disabled = true;
    });
});

function updateScrollTopVisibility() {
    scrollTopButton?.classList.toggle('is-visible', window.scrollY > 480);
}

window.addEventListener('scroll', updateScrollTopVisibility, { passive: true });
updateScrollTopVisibility();
scrollTopButton?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' }));