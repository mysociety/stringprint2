"use strict";
function setExpanded(toggle, expanded) {
    toggle.setAttribute("aria-expanded", String(expanded));
}
function closeDropdown(dropdown) {
    dropdown.querySelector(".dropdown-menu")?.classList.remove("show");
    const toggle = dropdown.querySelector(".dropdown-toggle");
    if (toggle !== null) {
        setExpanded(toggle, false);
    }
}
function closeDropdowns(except = null) {
    for (const dropdown of document.querySelectorAll(".dropdown")) {
        if (dropdown !== except) {
            closeDropdown(dropdown);
        }
    }
}
for (const toggle of document.querySelectorAll("[data-menu-toggle]")) {
    toggle.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const dropdown = toggle.closest(".dropdown");
        if (dropdown === null) {
            return;
        }
        const menu = dropdown.querySelector(".dropdown-menu");
        if (menu === null) {
            return;
        }
        const expand = !menu.classList.contains("show");
        closeDropdowns(dropdown);
        menu.classList.toggle("show", expand);
        setExpanded(toggle, expand);
    });
}
for (const item of document.querySelectorAll(".dropdown-menu a")) {
    item.addEventListener("click", () => {
        const dropdown = item.closest(".dropdown");
        if (dropdown !== null) {
            closeDropdown(dropdown);
        }
    });
}
const mobileToggle = document.querySelector("#mobile-menu-toggle");
const mobileNavigation = document.querySelector("#navbarSupportedContent");
function closeMobileNavigation() {
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
for (const link of document.querySelectorAll(".mobile-menu-list > li > a")) {
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
