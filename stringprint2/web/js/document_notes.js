"use strict";
function visible(element) {
    return !element.hidden && getComputedStyle(element).display !== "none";
}
function setVisible(element, show) {
    element.hidden = !show;
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
for (const anchor of document.querySelectorAll(".noscript-anchor")) {
    anchor.remove();
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
for (const link of document.querySelectorAll(".expand-footnotes")) {
    link.addEventListener("click", (event) => {
        event.preventDefault();
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
    });
}
for (const link of document.querySelectorAll(".hide-footnotes")) {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        const footnotes = link.closest(".footnotes");
        if (footnotes !== null) {
            toggleVisible(footnotes);
            refreshNavigation();
        }
    });
}
for (const link of document.querySelectorAll(".expand-link")) {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        const id = link.id.substring(1);
        setVisible(link, false);
        const row = document.querySelector(`#r${id}.extended-row`);
        const note = document.querySelector(`#g${id}.extended`);
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
for (const link of document.querySelectorAll(".hide-link")) {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        const id = link.id.substring(1);
        const row = document.querySelector(`#r${id}.extended-row`);
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
}
for (const row of document.querySelectorAll(".content-row")) {
    row.addEventListener("mouseenter", () => {
        const id = row.id.substring(1);
        if (!id) {
            return;
        }
        for (const link of document.querySelectorAll(".cite-link:not(.manual_paragraph)")) {
            setVisible(link, false);
        }
        const citeLink = document.querySelector(`#c${id}.cite-link`);
        if (citeLink !== null) {
            setVisible(citeLink, true);
        }
        set_mobile_link(id);
    });
}
