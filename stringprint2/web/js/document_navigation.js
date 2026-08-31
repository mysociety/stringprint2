"use strict";
var current_section = "";
let selectedSectionId = "";
let lastSectionId = 1;
const defaultPastSections = 1;
let trackingFrame = null;
function navigationMetadata(name) {
    return (document.querySelector(`meta[name="${name}"]`)?.content ?? "");
}
function elementIsVisible(element) {
    return !element.hidden && getComputedStyle(element).display !== "none";
}
function setMenuLink(link, target) {
    if (link === null) {
        return;
    }
    link.hidden = target === null;
    if (target !== null) {
        link.href = target.href;
    }
}
function set_mobile_link(id) {
    const paragraph = document.querySelector(`[data-paragraph-order="${CSS.escape(id)}"]`);
    if (paragraph === null) {
        return;
    }
    const citationUrl = paragraphCitationUrl(paragraph.id);
    for (const mobileLink of document.querySelectorAll(".mobile-header-link")) {
        mobileLink.href = citationUrl;
        mobileLink.dataset.paragraphOrder = id;
        mobileLink.dataset.displayTag = paragraph.dataset.displayTag ?? "";
    }
}
function adjustMenus(id = lastSectionId, future = 6, past = defaultPastSections) {
    const sectionId = typeof id === "number" ? id : Number.parseInt(id, 10);
    if (!Number.isFinite(sectionId)) {
        return;
    }
    lastSectionId = sectionId;
    future = Math.max(0, future);
    past = Math.max(0, past);
    const firstVisible = sectionId - past;
    const lastVisible = sectionId + future;
    for (const item of document.querySelectorAll(".top-menu-item, .dropdown")) {
        const itemId = Number.parseInt(item.getAttribute("item") ?? "", 10);
        const normalizedId = itemId === 0 ? 1 : itemId;
        item.classList.toggle("hide-item", normalizedId <= firstVisible || normalizedId > lastVisible);
    }
    const previousTarget = sectionId > 0 && firstVisible > 0
        ? document.querySelector(`a[section="${firstVisible}"]`)
        : null;
    const nextTarget = document.querySelector(`a[section="${firstVisible + 2}"]`);
    setMenuLink(document.querySelector("#menu-prev"), previousTarget);
    setMenuLink(document.querySelector("#menu-next"), nextTarget);
    const homeLink = document.querySelector("#home-link");
    if (homeLink === null) {
        return;
    }
    const homeLeft = homeLink.getBoundingClientRect().left;
    const overlaps = [...document.querySelectorAll(".top-menu-item")]
        .filter(elementIsVisible)
        .some((item) => item.getBoundingClientRect().right > homeLeft - 30);
    if (homeLeft > window.innerWidth - 50 || overlaps) {
        if (past > 1) {
            adjustMenus(sectionId, future, past - 1);
        }
        else if (future > 0) {
            adjustMenus(sectionId, future - 1, past);
        }
    }
}
function fitMobileTitle(title, toggle) {
    let fontSize = 14;
    title.style.fontSize = `${fontSize}pt`;
    if (toggle === null) {
        return;
    }
    while (title.getBoundingClientRect().top < toggle.getBoundingClientRect().top &&
        fontSize > 4) {
        fontSize -= 2;
        title.style.fontSize = `${fontSize}pt`;
    }
}
function changeSelected(id, suppliedTitle, noHash = false) {
    const title = suppliedTitle.split(":")[0]?.trim() || navigationMetadata("short_title");
    current_section = title;
    const mobileTitle = document.querySelector("#mobile-title");
    if (mobileTitle !== null) {
        mobileTitle.textContent = title;
        fitMobileTitle(mobileTitle, document.querySelector("#mobile-menu-toggle"));
    }
    for (const item of document.querySelectorAll("li.active")) {
        item.classList.remove("active");
    }
    document.querySelector(`#menu-${CSS.escape(id)}`)?.classList.add("active");
    document
        .querySelector(`#caret-menu-${CSS.escape(id)}`)
        ?.classList.add("active");
    const anchor = document.querySelector(`#a${CSS.escape(id)}.anchor`);
    if (!noHash) {
        harmlessHashChange(anchor?.getAttribute("name") ?? undefined);
    }
    adjustMenus(id);
    const paragraphId = document
        .querySelector(`#a${CSS.escape(id)}.linkable`)
        ?.getAttribute("first_graf");
    if (paragraphId !== null && paragraphId !== undefined) {
        set_mobile_link(paragraphId);
    }
}
function refreshSectionTracking() {
    if (trackingFrame !== null) {
        return;
    }
    trackingFrame = window.requestAnimationFrame(() => {
        trackingFrame = null;
        const anchors = [
            ...document.querySelectorAll(".section-anchor"),
        ].filter(elementIsVisible);
        let selected = anchors[0];
        for (const anchor of anchors) {
            if (anchor.getBoundingClientRect().top <= 80) {
                selected = anchor;
            }
            else {
                break;
            }
        }
        const id = selected?.id.startsWith("s") ? selected.id.substring(1) : "";
        if (!id || id === selectedSectionId) {
            return;
        }
        selectedSectionId = id;
        if (page_loaded) {
            changeSelected(id, selected?.textContent ?? "");
        }
    });
}
window.addEventListener("scroll", refreshSectionTracking, { passive: true });
window.addEventListener("resize", () => {
    adjustMenus();
    refreshSectionTracking();
});
adjustMenus();
set_mobile_link("1");
refreshSectionTracking();
