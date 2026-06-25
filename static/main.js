/* Nutrient Check — main.js */
document.addEventListener("DOMContentLoaded", () => {
  initCursor();
  initAutocomplete();
  initSearchValidation();
  initRdaBars();
  initCardAnimations();
  initCollapsibleToggles();
});

/* ─── 0. Custom dot cursor + water ripple ───────────────────────────────── */
function initCursor() {
  const dot = document.createElement("div");
  dot.className = "cursor-dot";
  document.body.appendChild(dot);

  // Move dot with mouse
  document.addEventListener("mousemove", (e) => {
    dot.style.left = e.clientX + "px";
    dot.style.top  = e.clientY + "px";
  });

  // Grow dot when hovering interactive elements
  const interactiveSelector = "a, button, input, select, textarea, label, [role='button'], [role='option'], .food-card, .category-pill, .cravings-toggle, .absorption-toggle, .toggle-card";
  document.addEventListener("mouseover", (e) => {
    if (e.target.closest(interactiveSelector)) {
      dot.classList.add("hovering");
    }
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.closest(interactiveSelector)) {
      dot.classList.remove("hovering");
    }
  });

  // Hide dot when mouse leaves the window
  document.addEventListener("mouseleave", () => { dot.style.opacity = "0"; });
  document.addEventListener("mouseenter", () => { dot.style.opacity = "1"; });

  // Water ripple on click
  document.addEventListener("click", (e) => {
    spawnRipple(e.clientX, e.clientY);
  });
}

function spawnRipple(x, y) {
  // Three concentric rings for a realistic water ripple
  const sizes   = [60, 120, 200];
  const delays  = [0, 80, 180];
  const colors  = [
    "rgba(42, 122, 75, 0.40)",
    "rgba(82, 184, 120, 0.25)",
    "rgba(42, 122, 75, 0.12)",
  ];

  sizes.forEach((size, i) => {
    setTimeout(() => {
      const ring = document.createElement("div");
      ring.className = "water-ripple";
      ring.style.cssText = `
        left: ${x}px;
        top: ${y}px;
        width: ${size}px;
        height: ${size}px;
        border: 2.5px solid ${colors[i]};
        background: transparent;
      `;
      document.body.appendChild(ring);
      // Remove after animation finishes
      ring.addEventListener("animationend", () => ring.remove());
    }, delays[i]);
  });
}

/* ─── 1. Autocomplete ───────────────────────────────────────────────────── */
function initAutocomplete() {
  const input = document.getElementById("nutrient-search");
  const dropdown = document.getElementById("suggest-list");
  if (!input || !dropdown) return;

  let items = [];
  let activeIndex = -1;
  let debounceTimer;

  input.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      const q = input.value.trim();
      if (q.length < 2) { closeDropdown(); return; }
      try {
        const res = await fetch(`/api/nutrients/suggest?q=${encodeURIComponent(q)}`);
        items = await res.json();
        renderDropdown(items);
      } catch (_) { closeDropdown(); }
    }, 200);
  });

  input.addEventListener("keydown", (e) => {
    if (!dropdown.classList.contains("open")) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      updateActive();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, -1);
      updateActive();
    } else if (e.key === "Enter") {
      if (activeIndex >= 0 && items[activeIndex]) {
        e.preventDefault();
        selectItem(items[activeIndex]);
      }
    } else if (e.key === "Escape") {
      closeDropdown();
    }
  });

  document.addEventListener("click", (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      closeDropdown();
    }
  });

  function renderDropdown(list) {
    dropdown.innerHTML = "";
    activeIndex = -1;
    if (!list.length) { closeDropdown(); return; }
    list.forEach((item, idx) => {
      const li = document.createElement("li");
      li.setAttribute("role", "option");
      li.setAttribute("id", `suggest-option-${idx}`);
      li.setAttribute("aria-selected", "false");
      li.innerHTML = `${escHtml(item.name)} <span class="autocomplete-category">${escHtml(item.category)}</span>`;
      li.addEventListener("click", () => selectItem(item));
      dropdown.appendChild(li);
    });
    dropdown.classList.add("open");
    input.setAttribute("aria-expanded", "true");
    input.setAttribute("aria-activedescendant", "");
  }

  function updateActive() {
    const opts = dropdown.querySelectorAll("li");
    opts.forEach((el, i) => {
      const selected = i === activeIndex;
      el.setAttribute("aria-selected", String(selected));
    });
    if (activeIndex >= 0 && opts[activeIndex]) {
      input.setAttribute("aria-activedescendant", opts[activeIndex].id);
      opts[activeIndex].scrollIntoView({ block: "nearest" });
    } else {
      input.setAttribute("aria-activedescendant", "");
    }
  }

  function selectItem(item) {
    input.value = item.name;
    closeDropdown();
    input.form && input.form.submit();
  }

  function closeDropdown() {
    dropdown.classList.remove("open");
    dropdown.innerHTML = "";
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-activedescendant", "");
    activeIndex = -1;
    items = [];
  }
}

/* ─── 2. Search form validation + loading spinner ───────────────────────── */
function initSearchValidation() {
  const form = document.getElementById("search-form");
  const btn = document.getElementById("search-btn");
  const input = document.getElementById("nutrient-search");
  const errorEl = document.getElementById("search-error");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    if (!input) return;
    if (input.value.trim().length < 2) {
      e.preventDefault();
      if (errorEl) {
        errorEl.textContent = "Please enter at least 2 characters.";
        errorEl.classList.add("visible");
      }
      return;
    }
    if (errorEl) errorEl.classList.remove("visible");
    if (btn) {
      btn.classList.add("loading");
      btn.disabled = true;
    }
  });

  if (input && errorEl) {
    input.addEventListener("input", () => {
      if (input.value.trim().length >= 2) errorEl.classList.remove("visible");
    });
  }
}

/* ─── 4. RDA bar animation (Intersection Observer) ─────────────────────── */
function initRdaBars() {
  const bars = document.querySelectorAll(".rda-bar");
  if (!bars.length || !window.IntersectionObserver) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("animate");
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.3 });

  bars.forEach((bar) => observer.observe(bar));
}

/* ─── 5. Micro-animations ───────────────────────────────────────────────── */
function initCardAnimations() {
  _slideFoodCards();
  _fadeColumns();
  _bouncePills();
  _glowCravingsDisclaimer();
}

/* Food cards slide in from the left, staggered 80 ms apart */
function _slideFoodCards() {
  const cards = document.querySelectorAll(".food-card");
  if (!cards.length || !window.IntersectionObserver) {
    // Fallback: show all immediately
    cards.forEach(c => c.classList.add("card-in"));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const card  = entry.target;
      const index = [...cards].indexOf(card);
      setTimeout(() => card.classList.add("card-in"), index * 80);
      observer.unobserve(card);
    });
  }, { threshold: 0.08 });
  cards.forEach(card => observer.observe(card));
}

/* Results columns fade up, each delayed 120 ms more than the previous */
function _fadeColumns() {
  const cols = document.querySelectorAll(".results-column");
  if (!cols.length || !window.IntersectionObserver) {
    cols.forEach(c => c.classList.add("col-in"));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const col   = entry.target;
      const index = [...cols].indexOf(col);
      setTimeout(() => col.classList.add("col-in"), index * 120);
      observer.unobserve(col);
    });
  }, { threshold: 0.04 });
  cols.forEach(col => observer.observe(col));
}

/* Cravings disclaimer glows once, only when it's actually scrolled into view
   (it starts inside a collapsed panel, so this fires the first time the user
   opens the section AND it's visible on screen — not just on click). */
function _glowCravingsDisclaimer() {
  const el = document.querySelector(".cravings-disclaimer");
  if (!el || !window.IntersectionObserver) {
    if (el) el.classList.add("glow-once");
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("glow-once");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.5 });
  observer.observe(el);
}

/* Category pills bounce in with staggered delay on the All Nutrients page */
function _bouncePills() {
  const pills = document.querySelectorAll(".category-pill");
  if (!pills.length) return;
  pills.forEach((pill, i) => {
    pill.classList.add("pill-init");
    pill.style.animationDelay = `${i * 38}ms`;
  });
}

/* ─── 6. Collapsible toggles (cravings, absorption helpers/blockers) ────── */
function initCollapsibleToggles() {
  document.querySelectorAll(".cravings-toggle, .absorption-toggle").forEach((btn) => {
    const content = document.getElementById(btn.getAttribute("aria-controls"));
    if (!content) return;

    function toggle() {
      const expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!expanded));
      content.hidden = expanded;
    }

    btn.addEventListener("click", toggle);

    // Clicking anywhere else in the card (not just the header button) also
    // opens/closes it — but let links inside the expanded content (source
    // links, etc.) work normally instead of toggling.
    const card = btn.closest(".results-column") || btn.parentElement;
    card.classList.add("toggle-card");
    card.addEventListener("click", (e) => {
      if (btn.contains(e.target)) return;
      if (e.target.closest("a")) return;
      toggle();
    });
  });

  // On laptop/desktop, "Foods That Provide This Nutrient" and "Role in the
  // Body" start expanded since there's room to show them right away; on
  // mobile every section starts collapsed (matches the existing 768px
  // breakpoint used elsewhere for the single-column layout).
  if (window.matchMedia("(min-width: 769px)").matches) {
    ["food-sources-toggle", "body-roles-toggle"].forEach((id) => {
      const btn = document.getElementById(id);
      if (!btn) return;
      const content = document.getElementById(btn.getAttribute("aria-controls"));
      if (!content) return;
      btn.setAttribute("aria-expanded", "true");
      content.hidden = false;
    });
  }
}

/* ─── Utilities ─────────────────────────────────────────────────────────── */
function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
