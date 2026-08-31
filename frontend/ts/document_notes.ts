declare let hide_state: boolean | string;

declare function send_ga(action: string, value?: string | null): void;
declare function set_mobile_link(id: string): void;
declare function refreshSectionTracking(): void;

function visible(element: HTMLElement): boolean {
  return !element.hidden && getComputedStyle(element).display !== "none";
}

function setVisible(element: HTMLElement, show: boolean): void {
  element.hidden = !show;
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

for (const anchor of document.querySelectorAll<HTMLElement>(".noscript-anchor")) {
  anchor.remove();
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

for (const link of document.querySelectorAll<HTMLAnchorElement>(
  ".expand-footnotes",
)) {
  link.addEventListener("click", (event) => {
    event.preventDefault();
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
  });
}

for (const link of document.querySelectorAll<HTMLAnchorElement>(
  ".hide-footnotes",
)) {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const footnotes = link.closest<HTMLElement>(".footnotes");
    if (footnotes !== null) {
      toggleVisible(footnotes);
      refreshNavigation();
    }
  });
}

for (const link of document.querySelectorAll<HTMLAnchorElement>(".expand-link")) {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const id = link.id.substring(1);
    setVisible(link, false);
    const row = document.querySelector<HTMLElement>(`#r${id}.extended-row`);
    const note = document.querySelector<HTMLElement>(`#g${id}.extended`);
    if (row !== null) {
      setVisible(row, true);
    }
    if (note !== null) {
      setVisible(note, true);
    }
    refreshNavigation();
    send_ga("Show Note", id);
  });
}

for (const link of document.querySelectorAll<HTMLAnchorElement>(".hide-link")) {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    const id = link.id.substring(1);
    const row = document.querySelector<HTMLElement>(`#r${id}.extended-row`);
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
}

for (const row of document.querySelectorAll<HTMLElement>(".content-row")) {
  row.addEventListener("mouseenter", () => {
    const id = row.id.substring(1);
    if (!id) {
      return;
    }
    for (const link of document.querySelectorAll<HTMLElement>(
      ".cite-link:not(.manual_paragraph)",
    )) {
      setVisible(link, false);
    }
    const citeLink = document.querySelector<HTMLElement>(`#c${id}.cite-link`);
    if (citeLink !== null) {
      setVisible(citeLink, true);
    }
    set_mobile_link(id);
  });
}
