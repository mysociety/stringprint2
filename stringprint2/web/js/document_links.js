"use strict";
var hide_state = true;
var page_loaded = false;
let currentlyMoving = false;
let draggingLink = false;
let paragraphMapPromise = null;
function showElement(element, show) {
    if (element !== null) {
        element.hidden = !show;
        element.style.display = show ? visibleDisplay(element) : "none";
    }
}
function visibleDisplay(element) {
    if (element instanceof HTMLTableRowElement) {
        return "table-row";
    }
    if (element instanceof HTMLAnchorElement || element instanceof HTMLSpanElement) {
        return "inline";
    }
    return "block";
}
function namedAnchor(name) {
    return ([...document.querySelectorAll("[name]")].find((element) => element.getAttribute("name") === name) ?? null);
}
function scrollToElement(element, offset) {
    window.scrollTo({
        top: window.scrollY + element.getBoundingClientRect().top - offset,
    });
}
function highlightRow(id, duration) {
    const row = document.querySelector(`[data-paragraph-order="${CSS.escape(id)}"]`);
    row?.classList.add("highlighted-content");
    window.setTimeout(() => {
        row?.classList.remove("highlighted-content");
    }, duration);
}
function harmlessHashChange(newHash) {
    const isIPad = /iPad/i.test(navigator.userAgent);
    if (currentlyMoving || isIPad) {
        return;
    }
    history.replaceState(undefined, "", newHash === undefined ? "#start" : `#${newHash}`);
}
function gotoTarget(target, revealNotes, internalMove = false) {
    const paragraphId = target.dataset.paragraphOrder;
    if (paragraphId === undefined) {
        return;
    }
    if (revealNotes && !currentlyMoving) {
        currentlyMoving = true;
        showElement(document.querySelector(`[data-paragraph-order="${CSS.escape(paragraphId)}"].extended-row`), true);
        showElement(document.querySelector(`#g${CSS.escape(paragraphId)}.extended`), true);
        const citeLink = document.querySelector("#paragraph-cite-link");
        if (citeLink !== null) {
            citeLink.href = paragraphCitationUrl(target.id);
            citeLink.dataset.paragraphOrder = paragraphId;
            citeLink.dataset.displayTag = target.dataset.displayTag ?? "";
            target.prepend(citeLink);
            citeLink.classList.add("manual_paragraph");
            showElement(citeLink, true);
        }
    }
    scrollToElement(target, 60);
    highlightRow(paragraphId, internalMove ? 5000 : 20000);
    currentlyMoving = false;
    set_mobile_link(paragraphId);
    if (!page_loaded) {
        const sectionId = target.dataset.section;
        if (sectionId !== undefined) {
            const title = document.querySelector(`#s${CSS.escape(sectionId)}.section-anchor h1`)?.textContent ?? "";
            changeSelected(sectionId, title, true);
        }
    }
}
function paragraphMap() {
    if (paragraphMapPromise === null) {
        const url = document.querySelector('meta[name="paragraph-map-url"]')?.content;
        paragraphMapPromise = url
            ? fetch(url).then(async (response) => {
                if (!response.ok) {
                    return {};
                }
                return (await response.json());
            })
            : Promise.resolve({});
    }
    return paragraphMapPromise;
}
async function gotoHash(hash, revealNotes = false) {
    send_ga("External Section Link", hash);
    const key = hash.replace(/^#/, "");
    const internalMove = key.startsWith("tag.");
    let target = document.getElementById(key);
    if (internalMove) {
        target = document.querySelector(`[data-paragraph-tag="${CSS.escape(key.substring(4))}"]`);
    }
    else if (target === null && key.split(".").length >= 5) {
        const compatibility = await paragraphMap();
        const currentKey = compatibility[key];
        target = currentKey === undefined ? null : document.getElementById(currentKey);
    }
    if (target !== null) {
        gotoTarget(target, internalMove ? false : revealNotes, internalMove);
    }
}
function localLinkHandler(link, event) {
    if (draggingLink ||
        link.classList.contains("cite-copy") ||
        link.pathname !== location.pathname ||
        link.hostname !== location.hostname) {
        return;
    }
    const parts = link.hash.split(".");
    if (parts[0]?.startsWith("#ref")) {
        event.preventDefault();
        const target = namedAnchor(parts[0].substring(1));
        const paragraphId = target?.id;
        if (paragraphId === undefined) {
            return;
        }
        const paragraph = document.getElementById(paragraphId);
        if (paragraph !== null) {
            scrollToElement(paragraph, 130);
            highlightRow(paragraphId, 2000);
        }
        showElement(document.querySelector(`#${CSS.escape(paragraphId)}.footnotes`), true);
        window.setTimeout(refreshSectionTracking, 500);
        return;
    }
    if (parts.length > 1) {
        event.preventDefault();
        void gotoHash(link.hash.substring(1));
        return;
    }
    const hash = link.hash.substring(1);
    const index = document.querySelector("#index-container");
    if (hash === "index") {
        event.preventDefault();
        send_ga("TOC View");
        showElement(index, true);
        refreshSectionTracking();
    }
    else if (index !== null && index.classList.contains("hide-index")) {
        showElement(index, false);
        refreshSectionTracking();
    }
    const target = namedAnchor(hash);
    if (target !== null) {
        event.preventDefault();
        scrollToElement(target, 30);
    }
}
document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const link = target.closest('a[href*="#"]:not([href="#"])');
    if (link !== null) {
        localLinkHandler(link, event);
    }
});
document.body.addEventListener("touchstart", () => {
    draggingLink = false;
});
document.body.addEventListener("touchmove", (event) => {
    if (event.target instanceof Element && event.target.closest("a") !== null) {
        draggingLink = true;
    }
});
window.addEventListener("load", () => {
    hide_state = document.querySelector('meta[name="hide_state"]')?.content !== "false";
    for (const element of document.querySelectorAll(".extended, .extended-row")) {
        showElement(element, !hide_state);
    }
    for (const link of document.querySelectorAll(".expand-link")) {
        showElement(link, hide_state);
    }
    const masterLabel = document.querySelector("#master_expand_link");
    if (masterLabel !== null) {
        masterLabel.textContent = hide_state ? "Show All Notes" : "Hide All Notes";
    }
    window.drawCharts?.();
    const hash = window.location.hash;
    if (hash === "#index") {
        showElement(document.querySelector("#index-container"), true);
        page_loaded = true;
        refreshSectionTracking();
        return;
    }
    if (hash.includes(".")) {
        void gotoHash(hash, true).finally(() => {
            page_loaded = true;
            refreshSectionTracking();
        });
        return;
    }
    if (hash && hash !== "#start") {
        const section = namedAnchor(hash.substring(1));
        const id = section?.id.startsWith("a") ? section.id.substring(1) : "";
        if (id) {
            const title = document.querySelector(`#s${CSS.escape(id)}.section-anchor h1`)?.textContent ?? "";
            changeSelected(id, title, true);
        }
    }
    page_loaded = true;
    refreshSectionTracking();
});
window.addEventListener("hashchange", () => {
    if (location.hash.includes(".")) {
        void gotoHash(location.hash);
    }
});
