interface SearchPage {
  title: string;
  text: string;
  tags: string;
  url: string;
}

interface SearchIndex {
  pages: SearchPage[];
}

declare const publicationSearchIndex: SearchIndex;

const resultsPerPage = 7;

function decodeSearchText(value: string): string {
  const textarea = document.createElement("textarea");
  textarea.innerHTML = value;
  return textarea.value;
}

function normalizedSearchTerms(query: string): string[] {
  return query
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .filter((term) => term.length > 0);
}

function termOccurrences(value: string, term: string): number {
  let count = 0;
  let position = value.indexOf(term);
  while (position !== -1) {
    count += 1;
    position = value.indexOf(term, position + term.length);
  }
  return count;
}

function searchPages(query: string): SearchPage[] {
  const terms = normalizedSearchTerms(query);
  return publicationSearchIndex.pages
    .map((page) => {
      const title = decodeSearchText(page.title).toLocaleLowerCase();
      const searchableText = decodeSearchText(
        `${page.text} ${page.tags}`,
      ).toLocaleLowerCase();
      const matches = terms.every(
        (term) => title.includes(term) || searchableText.includes(term),
      );
      const score = terms.reduce(
        (total, term) =>
          total +
          termOccurrences(title, term) * 5 +
          termOccurrences(searchableText, term),
        0,
      );
      return { page, matches, score };
    })
    .filter((result) => result.matches)
    .sort((left, right) => right.score - left.score)
    .map((result) => result.page);
}

function resultExcerpt(page: SearchPage, query: string): string {
  const words = page.text.trim().split(/\s+/);
  const terms = normalizedSearchTerms(query);
  const firstMatch = words.findIndex((word) =>
    terms.some((term) => word.toLocaleLowerCase().includes(term)),
  );
  const start = Math.max(0, firstMatch - 8);
  const excerpt = words.slice(start, start + 25).join(" ");
  return start > 0 ? `…${excerpt}` : excerpt;
}

function appendResult(
  container: HTMLElement,
  page: SearchPage,
  query: string,
): void {
  const title = document.createElement("div");
  title.className = "publication-search-result-title";
  const link = document.createElement("a");
  link.href = page.url;
  link.textContent = decodeSearchText(page.title);
  title.append(link);

  const text = document.createElement("div");
  text.className = "publication-search-result-text";
  text.textContent = decodeSearchText(resultExcerpt(page, query));
  container.append(title, text);
}

function appendPagination(
  container: HTMLElement,
  resultCount: number,
  currentPage: number,
  renderPage: (page: number) => void,
): void {
  const pageCount = Math.ceil(resultCount / resultsPerPage);
  if (pageCount < 2) {
    return;
  }
  const footer = document.createElement("div");
  footer.className = "publication-search-pagination";
  const list = document.createElement("ul");
  list.className = "publication-search-pages";
  for (let page = 0; page < pageCount; page += 1) {
    const item = document.createElement("li");
    if (page === currentPage) {
      item.className = "current";
      item.textContent = String(page + 1);
    } else {
      const link = document.createElement("a");
      link.href = "#";
      link.textContent = String(page + 1);
      link.addEventListener("click", (event) => {
        event.preventDefault();
        renderPage(page);
      });
      item.append(link);
    }
    list.append(item);
  }
  footer.append(list);
  container.append(footer);
}

const searchForm = document.querySelector<HTMLFormElement>(
  "#publication-search-form",
);
const searchInput = document.querySelector<HTMLInputElement>(
  "#publication-search-input",
);
const searchContent = document.querySelector<HTMLElement>(
  "#publication-search-results",
);

if (searchForm !== null && searchInput !== null && searchContent !== null) {
  const renderResults = (query: string, page = 0): void => {
    searchContent.replaceChildren();
    if (query.trim().length < 3) {
      const warning = document.createElement("div");
      warning.className = "publication-search-warning";
      warning.textContent = "Search terms must contain at least three characters.";
      searchContent.append(warning);
      return;
    }

    const results = searchPages(query);
    const count = document.createElement("div");
    count.className = "publication-search-result-count";
    count.textContent = `${results.length} result${results.length === 1 ? "" : "s"}`;
    searchContent.append(count);
    for (const result of results.slice(
      page * resultsPerPage,
      (page + 1) * resultsPerPage,
    )) {
      appendResult(searchContent, result, query);
    }
    appendPagination(searchContent, results.length, page, (selectedPage) => {
      renderResults(query, selectedPage);
      window.scrollTo({ top: searchContent.offsetTop - 30 });
    });
  };

  searchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = searchInput.value.trim();
    const url = new URL(window.location.href);
    url.searchParams.set("q", query);
    history.replaceState(undefined, "", url);
    renderResults(query);
  });

  const initialQuery = new URLSearchParams(window.location.search).get("q");
  if (initialQuery !== null) {
    searchInput.value = initialQuery;
    renderResults(initialQuery);
  }
}
