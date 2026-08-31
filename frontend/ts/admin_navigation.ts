function collapseTarget(control: HTMLElement): HTMLElement | null {
  const selector = control.getAttribute("data-bs-target");
  if (selector === null) {
    return null;
  }
  try {
    return document.querySelector<HTMLElement>(selector);
  } catch {
    return null;
  }
}

for (const control of document.querySelectorAll<HTMLElement>(
  "[data-bs-toggle='collapse'][data-bs-target]",
)) {
  control.addEventListener("click", (event) => {
    event.preventDefault();
    const target = collapseTarget(control);
    if (target === null) {
      return;
    }
    const expanded = target.classList.toggle("show");
    control.setAttribute("aria-expanded", String(expanded));
    target.setAttribute("aria-expanded", String(expanded));
  });
}
