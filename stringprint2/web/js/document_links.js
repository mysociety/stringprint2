"use strict";
var hide_state = true;
var page_loaded = false;
let currentlyMoving = false;
let draggingLink = false;
function showElement(element, show) {
    if (element !== null) {
        element.hidden = !show;
    }
}
function namedAnchor(name) {
    return ([...document.querySelectorAll("[name]")].find((element) => element.getAttribute("name") === name) ?? null);
}
function elementsWithAttributes(attributes) {
    return [...document.querySelectorAll("*")].filter((element) => Object.entries(attributes).every(([name, value]) => element.getAttribute(name) === value));
}
function scrollToElement(element, offset) {
    window.scrollTo({
        top: window.scrollY + element.getBoundingClientRect().top - offset,
    });
}
function highlightRow(id, duration) {
    const row = document.querySelector(`#r${CSS.escape(id)}.content-row`);
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
    const paragraphId = target.getAttribute("name");
    if (paragraphId === null) {
        return;
    }
    if (revealNotes && !currentlyMoving) {
        currentlyMoving = true;
        showElement(document.querySelector(`#r${CSS.escape(paragraphId)}.extended-row`), true);
        showElement(document.querySelector(`#g${CSS.escape(paragraphId)}.extended`), true);
        document
            .querySelector(`#c${CSS.escape(paragraphId)}.cite-link`)
            ?.classList.add("manual_paragraph");
    }
    scrollToElement(target, 60);
    highlightRow(paragraphId, internalMove ? 5000 : 20000);
    currentlyMoving = false;
    set_mobile_link(paragraphId);
    if (!page_loaded) {
        const sectionId = target.getAttribute("parent");
        if (sectionId !== null) {
            const title = document.querySelector(`#s${CSS.escape(sectionId)}.section-anchor h1`)?.textContent ?? "";
            changeSelected(sectionId, title, true);
        }
    }
}
function hashTargets(hash) {
    const parts = hash.replace(/^#/, "").split(".");
    if (parts[0] === "tag" && parts[1] !== undefined) {
        return [elementsWithAttributes({ tag: parts[1] })];
    }
    if (parts.length !== 5 && parts.length !== 6) {
        return [];
    }
    const [section, position, key, start, end, letter] = parts;
    if (section === undefined ||
        position === undefined ||
        key === undefined ||
        start === undefined ||
        end === undefined) {
        return [];
    }
    const targets = [
        elementsWithAttributes({ key }),
        elementsWithAttributes({ start_key: start, end_key: end }),
        elementsWithAttributes({ start_key: start, position_key: position }),
        elementsWithAttributes({ end_key: end, position_key: position }),
        elementsWithAttributes({ start_key: start }),
        elementsWithAttributes({ end_key: end }),
        elementsWithAttributes({ position_key: position, parent: section }),
        elementsWithAttributes({ section }),
    ];
    if (letter !== undefined) {
        targets.splice(1, 0, elementsWithAttributes({ letter_key: letter }));
    }
    return targets;
}
function gotoHash(hash, revealNotes = false) {
    send_ga("External Section Link", hash);
    const internalMove = hash.replace(/^#/, "").startsWith("tag.");
    for (const candidates of hashTargets(hash)) {
        if (candidates.length === 1 && candidates[0] !== undefined) {
            gotoTarget(candidates[0], internalMove ? false : revealNotes, internalMove);
            return;
        }
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
        gotoHash(link.hash.substring(1));
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
for (const link of document.querySelectorAll('a[href*="#"]:not([href="#"])')) {
    link.addEventListener("click", (event) => {
        localLinkHandler(link, event);
    });
}
document.body.addEventListener("touchstart", () => {
    draggingLink = false;
});
for (const link of document.querySelectorAll("a")) {
    link.addEventListener("touchmove", () => {
        draggingLink = true;
    });
}
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
    if (hash.includes(".")) {
        page_loaded = true;
        gotoHash(hash, true);
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
        gotoHash(location.hash);
    }
});
