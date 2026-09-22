interface Window {
  gtag?: (...arguments_: unknown[]) => void;
}

declare function changeSelected(
  id: string,
  title: string,
  noHash?: boolean,
): void;

function metadata(name: string): string {
  return (
    document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.content ?? ""
  );
}

function send_ga(action: string, value: string | null = null): void {
  window.gtag?.("event", "stringprint_event", {
    action,
    label: metadata("slug"),
    value,
  });
}

for (const link of document.querySelectorAll<HTMLAnchorElement>("a.nav-link")) {
  link.addEventListener("click", () => {
    send_ga("Mobile Menu Click", link.href);
  });
}

for (const link of document.querySelectorAll<HTMLAnchorElement>("a.search_link")) {
  link.addEventListener("click", () => {
    send_ga("Search");
  });
}

for (const link of document.querySelectorAll<HTMLAnchorElement>("a.alt_link")) {
  link.addEventListener("click", () => {
    send_ga(`Alt Format - ${link.getAttribute("type") ?? ""}`);
  });
}

for (const link of document.querySelectorAll<HTMLAnchorElement>("a.top-nav-item")) {
  link.addEventListener("mouseup", () => {
    send_ga("Top Nav Click", link.href);
    const sectionId = link.getAttribute("section");
    if (sectionId === null) {
      return;
    }
    const title =
      document.querySelector<HTMLElement>(
        `#s${sectionId}.section-anchor h1`,
      )?.textContent ?? "";
    changeSelected(sectionId, title, true);
  });
}
