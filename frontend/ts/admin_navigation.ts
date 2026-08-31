function collapseTarget(control: HTMLElement): HTMLElement | null {
  const selector = control.getAttribute("data-target");
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
  "[data-toggle='collapse'][data-target]",
)) {
  control.addEventListener("click", (event) => {
    event.preventDefault();
    const target = collapseTarget(control);
    if (target === null) {
      return;
    }
    const expanded = target.classList.toggle("in");
    control.setAttribute("aria-expanded", String(expanded));
    target.setAttribute("aria-expanded", String(expanded));
  });
}
