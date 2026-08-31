function setExpanded(toggle: HTMLElement, expanded: boolean): void {
  toggle.setAttribute("aria-expanded", String(expanded));
}

function closeDropdown(dropdown: HTMLElement): void {
  dropdown.querySelector<HTMLElement>(".dropdown-menu")?.classList.remove("show");
  const toggle = dropdown.querySelector<HTMLElement>(".dropdown-toggle");
  if (toggle !== null) {
    setExpanded(toggle, false);
  }
}

function closeDropdowns(except: HTMLElement | null = null): void {
  for (const dropdown of document.querySelectorAll<HTMLElement>(".dropdown")) {
    if (dropdown !== except) {
      closeDropdown(dropdown);
    }
  }
}

for (const toggle of document.querySelectorAll<HTMLButtonElement>(
  "[data-menu-toggle]",
)) {
  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const dropdown = toggle.closest<HTMLElement>(".dropdown");
    if (dropdown === null) {
      return;
    }
    const menu = dropdown.querySelector<HTMLElement>(".dropdown-menu");
    if (menu === null) {
      return;
    }
    const expand = !menu.classList.contains("show");
    closeDropdowns(dropdown);
    menu.classList.toggle("show", expand);
    setExpanded(toggle, expand);
  });
}

for (const item of document.querySelectorAll<HTMLAnchorElement>(
  ".dropdown-menu a",
)) {
  item.addEventListener("click", () => {
    const dropdown = item.closest<HTMLElement>(".dropdown");
    if (dropdown !== null) {
      closeDropdown(dropdown);
    }
  });
}

const mobileToggle = document.querySelector<HTMLButtonElement>(
  "#mobile-menu-toggle",
);
const mobileNavigation = document.querySelector<HTMLElement>(
  "#navbarSupportedContent",
);

function closeMobileNavigation(): void {
  mobileNavigation?.classList.remove("show");
  if (mobileToggle !== null) {
    setExpanded(mobileToggle, false);
  }
}

mobileToggle?.addEventListener("click", (event) => {
  event.stopPropagation();
  const expand = !mobileNavigation?.classList.contains("show");
  mobileNavigation?.classList.toggle("show", expand);
  setExpanded(mobileToggle, expand);
});

for (const link of document.querySelectorAll<HTMLAnchorElement>(
  ".mobile-menu-list > li > a",
)) {
  link.addEventListener("click", closeMobileNavigation);
}

document.body.addEventListener("click", () => {
  closeDropdowns();
  closeMobileNavigation();
});

mobileNavigation?.addEventListener("click", (event) => {
  event.stopPropagation();
});


document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDropdowns();
    closeMobileNavigation();
  }
});
