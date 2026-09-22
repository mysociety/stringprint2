"use strict";
function visible(element) {
    return !element.hidden && getComputedStyle(element).display !== "none";
}
function setVisible(element, show) {
    element.hidden = !show;
    if (!show) {
        element.style.display = "none";
    }
    else if (element instanceof HTMLTableRowElement) {
        element.style.display = "table-row";
    }
    else if (element instanceof HTMLAnchorElement ||
        element instanceof HTMLSpanElement) {
        element.style.display = "inline";
    }
    else {
        element.style.display = "block";
    }
}
function toggleVisible(element) {
    const show = !visible(element);
    setVisible(element, show);
    return show;
}
function refreshNavigation() {
    window.setTimeout(() => {
        refreshSectionTracking();
    }, 500);
}
function scrollIntoReadingPosition(element) {
    const bounds = element.getBoundingClientRect();
    if (bounds.top < 0 || bounds.bottom > window.innerHeight) {
        window.scrollTo({
            top: window.scrollY + bounds.top - window.innerHeight / 3,
            behavior: "smooth",
        });
    }
}
document.querySelector("#master_expand")?.addEventListener("click", (event) => {
    event.preventDefault();
    hide_state = !Boolean(hide_state);
    const show = !hide_state;
    for (const element of document.querySelectorAll(".extended-row, .extended")) {
        setVisible(element, show);
    }
    for (const link of document.querySelectorAll(".expand-link")) {
        setVisible(link, hide_state);
    }
    const label = document.querySelector("#master_expand_link");
    if (label !== null) {
        label.textContent = hide_state ? "Show All Notes" : "Hide All Notes";
    }
});
document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
        return;
    }
    const link = target.closest(".expand-footnotes, .hide-footnotes, .expand-link, .hide-link");
    if (link === null) {
        return;
    }
    event.preventDefault();
    if (link.classList.contains("expand-footnotes")) {
        const id = link.id;
        const footnotes = document.querySelector(`#f${id}.footnotes`);
        if (footnotes === null) {
            return;
        }
        const show = toggleVisible(footnotes);
        refreshNavigation();
        const paragraphId = link.getAttribute("name");
        const paragraph = paragraphId === null
            ? null
            : document.getElementById(paragraphId);
        if (show && paragraph !== null) {
            scrollIntoReadingPosition(paragraph);
        }
        send_ga("Show Footnote", id);
        return;
    }
    if (link.classList.contains("hide-footnotes")) {
        const footnotes = link.closest(".footnotes");
        if (footnotes !== null) {
            toggleVisible(footnotes);
            refreshNavigation();
        }
        return;
    }
    if (link.classList.contains("expand-link")) {
        const id = link.id.substring(1);
        setVisible(link, false);
        const row = document.querySelector(`[data-paragraph-order="${CSS.escape(id)}"].extended-row`);
        const note = document.querySelector(`#g${id}.extended`);
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
    const row = document.querySelector(`[data-paragraph-order="${CSS.escape(id)}"].extended-row`);
    const note = document.querySelector(`#g${id}.extended`);
    const expandLink = document.querySelector(`#e${id}.expand-link`);
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
    const row = target.closest("[data-paragraph-order]");
    const citeLink = document.querySelector("#paragraph-cite-link");
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
