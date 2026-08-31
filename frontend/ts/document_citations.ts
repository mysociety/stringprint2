interface ClipboardApi {
  copy: (value: string) => Promise<void>;
}

interface SweetAlertApi {
  fire: (options: {
    icon: "success";
    html: string;
    confirmButtonText: string;
  }) => void;
}

declare const clipboard: ClipboardApi;
declare const Swal: SweetAlertApi;
declare let current_section: string;
declare function send_ga(action: string, value?: string | null): void;

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
] as const;

function citationMetadata(name: string): string {
  return (
    document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)?.content ?? ""
  );
}

function currentDate(): string {
  const now = new Date();
  return `${now.getDate()} ${monthNames[now.getMonth()]}. ${now.getFullYear()}`;
}

function citationDialog(
  dialogTitle: string,
  link: string,
  paragraphId: string,
  paragraphTag: string,
): void {
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

for (const link of document.querySelectorAll<HTMLAnchorElement>(".cite-copy")) {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const href = link.href;
    const paragraphId = link.id.substring(1);
    const paragraphTag = link.getAttribute("para_tag") ?? "";
    void clipboard.copy(href).then(
      () => {
        citationDialog(
          "Link added to Clipboard!",
          href,
          paragraphId,
          paragraphTag,
        );
      },
      () => {
        citationDialog("Copy Link From Below!", href, paragraphId, paragraphTag);
      },
    );
  });
}
