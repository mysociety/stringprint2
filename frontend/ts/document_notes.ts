declare var hide_state: boolean | string;

declare function send_ga(action: string, value?: string | null): void;
declare function set_mobile_link(id: string): void;
declare function refreshSectionTracking(): void;

function visible(element: HTMLElement): boolean {
  return !element.hidden && getComputedStyle(element).display !== "none";
}

function setVisible(element: HTMLElement, show: boolean): void {
  element.hidden = !show;
  if (!show) {
    element.style.display = "none";
  } else if (element instanceof HTMLTableRowElement) {
    element.style.display = "table-row";
  } else if (
    element instanceof HTMLAnchorElement ||
    element instanceof HTMLSpanElement
  ) {
    element.style.display = "inline";
  } else {
    element.style.display = "block";
  }
}

function toggleVisible(element: HTMLElement): boolean {
  const show = !visible(element);
  setVisible(element, show);
  return show;
}

function refreshNavigation(): void {
  window.setTimeout(() => {
    refreshSectionTracking();
  }, 500);
}

function scrollIntoReadingPosition(element: HTMLElement): void {
  const bounds = element.getBoundingClientRect();
  if (bounds.top < 0 || bounds.bottom > window.innerHeight) {
    window.scrollTo({
      top: window.scrollY + bounds.top - window.innerHeight / 3,
      behavior: "smooth",
    });
  }
}

document.querySelector<HTMLElement>("#master_expand")?.addEventListener(
  "click",
  (event) => {
    event.preventDefault();
    hide_state = !Boolean(hide_state);
    const show = !hide_state;
    for (const element of document.querySelectorAll<HTMLElement>(
      ".extended-row, .extended",
    )) {
      setVisible(element, show);
    }
    for (const link of document.querySelectorAll<HTMLElement>(".expand-link")) {
      setVisible(link, hide_state);
    }
    const label = document.querySelector<HTMLElement>("#master_expand_link");
    if (label !== null) {
      label.textContent = hide_state ? "Show All Notes" : "Hide All Notes";
    }
  },
);

document.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) {
    return;
  }
  const link = target.closest<HTMLAnchorElement>(
    ".expand-footnotes, .hide-footnotes, .expand-link, .hide-link",
  );
  if (link === null) {
    return;
  }
  event.preventDefault();

  if (link.classList.contains("expand-footnotes")) {
    const id = link.id;
    const footnotes = document.querySelector<HTMLElement>(`#f${id}.footnotes`);
    if (footnotes === null) {
      return;
    }
    const show = toggleVisible(footnotes);
    refreshNavigation();
    const paragraphId = link.getAttribute("name");
    const paragraph =
      paragraphId === null
        ? null
        : document.getElementById(paragraphId);
    if (show && paragraph !== null) {
      scrollIntoReadingPosition(paragraph);
    }
    send_ga("Show Footnote", id);
    return;
  }
  if (link.classList.contains("hide-footnotes")) {
    const footnotes = link.closest<HTMLElement>(".footnotes");
    if (footnotes !== null) {
      toggleVisible(footnotes);
      refreshNavigation();
    }
    return;
  }

  if (link.classList.contains("expand-link")) {
    const id = link.id.substring(1);
    setVisible(link, false);
    const row = document.querySelector<HTMLElement>(
      `[data-paragraph-order="${CSS.escape(id)}"].extended-row`,
    );
    const note = document.querySelector<HTMLElement>(`#g${id}.extended`);
    if (row !== null) {
      setVisible(row, true);
    }
    if (note !== null) {
      setVisible(note, true);
    }
    refreshNavigation();
    send_ga("Show Note", id);
    return;
  }

  const id = link.id.substring(1);
  const row = document.querySelector<HTMLElement>(
    `[data-paragraph-order="${CSS.escape(id)}"].extended-row`,
  );
  const note = document.querySelector<HTMLElement>(`#g${id}.extended`);
  const expandLink = document.querySelector<HTMLElement>(`#e${id}.expand-link`);
  if (row !== null) {
    setVisible(row, false);
  }
  if (note !== null) {
    setVisible(note, false);
  }
  if (expandLink !== null) {
    setVisible(expandLink, true);
  }
  refreshNavigation();
});

document.addEventListener("pointerover", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) {
    return;
  }
  const row = target.closest<HTMLElement>("[data-paragraph-order]");
  const citeLink = document.querySelector<HTMLAnchorElement>(
    "#paragraph-cite-link",
  );
  if (row === null || citeLink === null || row.contains(citeLink)) {
    return;
  }
  const order = row.dataset.paragraphOrder;
  if (order === undefined) {
    return;
  }
  citeLink.href = paragraphCitationUrl(row.id);
  citeLink.dataset.paragraphOrder = order;
  citeLink.dataset.displayTag = row.dataset.displayTag ?? "";
  row.prepend(citeLink);
  setVisible(citeLink, true);
  set_mobile_link(order);
});
