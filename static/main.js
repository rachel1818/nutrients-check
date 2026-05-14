/* Nutrient Check — main.js */
document.addEventListener("DOMContentLoaded", () => {
  initCursor();
  initAutocomplete();
  initSearchValidation();
  initShowMore();
  initRdaBars();
  initCardAnimations();
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
  const interactiveSelector = "a, button, input, select, textarea, label, [role='button'], [role='option'], .food-card, .category-pill, .show-more-btn";
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
    "rgba(194, 113, 79, 0.45)",   // terracotta
    "rgba(74, 124, 89, 0.28)",    // olive
    "rgba(194, 113, 79, 0.14)",   // faint terracotta
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

/* ─── 3. "Show more" foods ──────────────────────────────────────────────── */
function initShowMore() {
  const btn = document.getElementById("show-more-foods");
  const list = document.getElementById("food-list");
  if (!btn || !list) return;

  btn.addEventListener("click", async () => {
    const nutrientId = btn.dataset.nutrientId;
    const offset = parseInt(btn.dataset.offset, 10);
    const originalText = btn.textContent;
    btn.textContent = "Loading...";
    btn.disabled = true;

    try {
      const res = await fetch(`/api/nutrients/${nutrientId}/foods?offset=${offset}&limit=10`);
      const data = await res.json();
      appendFoodCards(data.items, list);
      const newOffset = offset + data.items.length;
      btn.dataset.offset = newOffset;

      if (data.items.length < 10 || newOffset >= data.total) {
        btn.remove();
      } else {
        btn.textContent = originalText;
        btn.disabled = false;
      }
    } catch (_) {
      btn.textContent = originalText;
      btn.disabled = false;
    }
  });
}

function appendFoodCards(foods, list) {
  foods.forEach((food, i) => {
    const li = document.createElement("li");
    li.className = "food-card";
    li.style.animationDelay = `${i * 60}ms`;
    li.innerHTML = `
      <h4>${escHtml(food.food_name)}</h4>
      <div class="food-amount">${food.amount} ${escHtml(food.unit)}</div>
      <div class="food-serving">${escHtml(food.serving_size)}</div>
      ${food.bioavailability_note ? `<div class="food-note">${escHtml(food.bioavailability_note)}</div>` : ""}
      ${food.preparation_note ? `<div class="food-note">Prep: ${escHtml(food.preparation_note)}</div>` : ""}
      <div class="food-source">
        <a href="${escHtml(food.source.url)}" target="_blank" rel="noopener" class="source-link">
          ${escHtml(food.source.name)}
        </a>
      </div>
    `;
    list.appendChild(li);
  });
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

/* ─── 5. Card entrance animations ──────────────────────────────────────── */
function initCardAnimations() {
  const cards = document.querySelectorAll(".food-card");
  cards.forEach((card, i) => {
    card.style.animationDelay = `${i * 60}ms`;
  });
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
