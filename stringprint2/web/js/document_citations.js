"use strict";
const monthNames = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sept",
    "Oct",
    "Nov",
    "Dec",
];
function citationMetadata(name) {
    return (document.querySelector(`meta[name="${name}"]`)?.content ?? "");
}
function currentDate() {
    const now = new Date();
    return `${now.getDate()} ${monthNames[now.getMonth()]}. ${now.getFullYear()}`;
}
function citationDialog(dialogTitle, link, paragraphId, paragraphTag) {
    const title = citationMetadata("short_title");
    const fullTitle = citationMetadata("full_title");
    const author = citationMetadata("cite_author");
    const year = citationMetadata("year");
    const organisation = citationMetadata("org");
    const section = current_section === title ? "" : current_section.trim();
    const sectionName = section ? `: ${section}` : "";
    const identifier = paragraphTag || paragraphId;
    let content = `Link : <a href="${link}">${title}${sectionName}, Paragraph ${identifier}</a>`;
    if (citationMetadata("include_citation") === "true") {
        content += `<br><br>Cite As:<br><span class="cite"> ${author} (${year}), <i>${fullTitle}</i>. [online] , ${organisation}. Paragraph: ${identifier}, Available at: ${link} [Accessed ${currentDate()}]</span>`;
    }
    Swal.fire({
        icon: "success",
        html: `<h4><b>${dialogTitle}</b></h4>${content}`,
        confirmButtonText: "OK",
    });
    send_ga("Generated Link", link);
}
for (const link of document.querySelectorAll(".cite-copy")) {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const href = link.href;
        const paragraphId = link.id.substring(1);
        const paragraphTag = link.getAttribute("para_tag") ?? "";
        void clipboard.copy(href).then(() => {
            citationDialog("Link added to Clipboard!", href, paragraphId, paragraphTag);
        }, () => {
            citationDialog("Copy Link From Below!", href, paragraphId, paragraphTag);
        });
    });
}
