"use strict";
function metadata(name) {
    return (document.querySelector(`meta[name="${name}"]`)?.content ?? "");
}
function send_ga(action, value = null) {
    window.gtag?.("event", "stringprint_event", {
        action,
        label: metadata("slug"),
        value,
    });
}
for (const link of document.querySelectorAll("a.nav-link")) {
    link.addEventListener("click", () => {
        send_ga("Mobile Menu Click", link.href);
    });
}
for (const link of document.querySelectorAll("a.search_link")) {
    link.addEventListener("click", () => {
        send_ga("Search");
    });
}
for (const link of document.querySelectorAll("a.alt_link")) {
    link.addEventListener("click", () => {
        send_ga(`Alt Format - ${link.getAttribute("type") ?? ""}`);
    });
}
for (const link of document.querySelectorAll("a.top-nav-item")) {
    link.addEventListener("mouseup", () => {
        send_ga("Top Nav Click", link.href);
        const sectionId = link.getAttribute("section");
        if (sectionId === null) {
            return;
        }
        const title = document.querySelector(`#s${sectionId}.section-anchor h1`)?.textContent ?? "";
        changeSelected(sectionId, title, true);
    });
}
