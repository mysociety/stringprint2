# stringprint2 feature inventory

This is the current behavior and test coverage for Python 3.14 and Django 5.2.
Implementation references name modules and entry points rather than line numbers.
Historical defects are recorded below with their resolution; passing tests should
assert the intended behavior rather than preserve an acknowledged defect.

## Running verification

From the engine repository:

```bash
poetry run pytest                         # default suite: no external tools/network
poetry run pytest -m external              # external integrations and browser checks
poetry run pytest -m "" --create-db        # all tiers, rebuilding the test database
poetry run pytest tests/config/test_migrations.py --create-db
npm run check
npm run build
```

The document-source repository supplies Ruff, strict mypy, and CI configuration:

```bash
poetry run ruff check .
poetry run mypy
poetry run python -m stringprint2.configuration .
```

Tests use a disposable copy of `tests/fixtures/doc_source`, including separate
media and static build directories. Publication processing can write paragraph
links and image derivatives without changing authored fixtures or real reports.
The fixture binary generator supports `python tests/fixtures/make_binaries.py --check`.

The `external` marker excludes integrations from the default run. `needs_sass`,
`needs_chrome`, `needs_network`, and `slow` describe additional requirements.
A mocked subprocess test does not establish that the corresponding external
program is installed or functional.

## Publication pipeline

The CLI and authenticated management interface delegate to the same typed
publication operations and services:

| Stage | Implementation | Coverage |
|---|---|---|
| Discover configured publications | `services/publication_catalog.py` | service and web catalog tests |
| Validate repository, organisation, publication, and assets | `configuration/models.py`, `loaders.py`, `validator.py` | `tests/configuration/`, configuration bootstrap tests |
| Load settings, aliases, defaults, header/cover actions | `services/publication_loading.py`, model adapters | `tests/config/`, service loading tests |
| Run configured preprocessing | `services/configured_commands.py`, `tools/preprocessing.py` | command, workflow, Word, and preprocessing tests |
| Load authored Markdown | `services/publication_sources.py` | source and pipeline tests |
| Import images, spreadsheets, and HTML | `services/asset_importing.py`, `Article.import_assets` | asset configuration and rendering tests |
| Compile sections, paragraphs, references, notes, and assets | `tools/deepink.py:process_ink` | `tests/pipeline/`, parser unit tests |
| Reconcile stable paragraph identifiers | `services/paragraph_links.py` | paragraph link, orphan, redirect, and map tests |
| Render preview and search | `stringprint/views.py`, publication templates | `tests/render/`, real-browser tests |
| Bake web output into sibling staging | `services/web_rendering.py`, `static_rendering.py` | service atomicity tests and `tests/bake/` |
| Produce EPUB or optional MOBI | `services/ebook_rendering.py`, `kindle_rendering.py` | EPUB integration; Kindle staging with a fake generator |
| Archive and publish | `services/publication_archiving.py`, publication operations | archive, workflow, and permission tests |

Configuration is validated with Pydantic. Unsupported keys are errors; documented
legacy aliases and organisation defaults are applied explicitly. Publication
values crossing service boundaries use typed records or models.

`__main__.py` is importable without starting the server, worker, or command loop.
Executing the console starts services according to CLI options. Process modifiers
accept both the documented `--no-preprocess` spelling and the legacy
`no-preprocess` form.

Configured commands support `module::` callables and quoted command strings.
Command strings render without HTML escaping, are parsed into argv with
`shlex.split`, and run without a shell. Quote interpolated values that must remain
one argument, for example `python script.py "{{article.title}}"`. Missing template
values and malformed quoting fail before subprocess execution.

## Outputs and frontend behavior

Web baking defaults to `kindle=False`, `epub=True`, and `plain=True`.
`skip_epub: true` suppresses automatically generated EPUB output. An explicit
EPUB operation remains available. MOBI generation is opt-in and requires a working
`KINDLEGEN_LOC` or `kindlegen` executable. Its absence does not prevent normal
web output. Download links for optional formats reflect files generated in the
current build.

The renderer uses a copy of the publication for transient flags and compressed
asset collection. Build URLs and output availability travel through template
context. The publication `compress` tag, loaded from `publication_assets`, forces
compression only for baked contexts. Web and Kindle rendering do not assign
global Django settings. Custom publication templates containing compression blocks
should load `publication_assets` as the built-in publication templates do.

Whole web builds replace the destination only after successful staging. Individual
static writes are atomic. Failed builds preserve the previous publication.

First-party JavaScript is strict TypeScript in `frontend/ts/`, compiled into static
JavaScript. Publication interactions use native DOM APIs: navigation overflow,
dropdowns, paragraph links, citations, notes, and search. The publication and
management layouts use Bootstrap 5. No first-party runtime requires jQuery,
Waypoints, Tipue, or Trumbowyg.

The browser suite exercises desktop and mobile preview navigation, dropdown
alignment and Escape handling, TOC styling, search layout and behavior, and
publication screenshots. Bake tests additionally check relative links, copied CSS
and JavaScript, optional output files, repeated builds, and failure isolation.

## Tables and serialization

`table_files.py:DataTable` reads CSV, legacy XLS, and XLSX. New Word table assets
are XLSX, written with openpyxl. Legacy XLS remains readable through xlrd.
`stringprint-migrate-tables` migrates declared XLS assets and their manifests,
with `--keep-xls` available when the original files should be retained.

Table rendering supports a header row or treats that row as ordinary data when
headers are disabled. Headerless Bootstrap output does not insert empty rows,
including for spreadsheets with only one row.

`serialization.py` owns the existing text-backed JSON representation. Registered
Section/Graf/Footnote/Chart/Column objects retain their historical serialized shape.
All historical field imports use the project-owned implementation. The
`useful_inkleby` package and its inert migration mixins are removed.

Migration tests cover a clean database, schema drift, custom-field round trips,
and upgrading populated pre-upgrade state without changing stored JSON bytes.

## Management interface and legacy URLs

See [management-operations.md](management-operations.md) for operation states,
permissions, worker ownership, cancellation, retry, retention, and diagnosis.

Management lives at `/manage/`. Django login and organisation membership protect
actions; mutating operation routes require POST and CSRF protection. The CLI
supervises the preview server and one worker. Foreground and queued operations
share per-publication locks under the repository's `.stringprint/locks/` directory.

The old dashboard, document list, and browser-upload URLs redirect to the current
catalog. Legacy publish and reupload URLs redirect to the selected publication's
management page after checking organisation membership. They do not create
database-only documents or invoke removed import queues. Source authoring remains
in repository files and CLI workflows. Document and organisation settings and
header-image forms remain available; header changes invoke existing derivative
methods directly. Unknown URLs return 404.

## Previously documented defects

| Original issue | Current resolution and regression coverage |
|---|---|
| Shared mutable JSON field defaults | Callable defaults; per-instance defaults and migration tests |
| Preview index queried a removed field / missing cookie include | Corrected preview view and template; rendering tests |
| Non-chart assets and chart package lookup failed | Corrected chart/view adapters; chart and asset tests |
| Pagination used Python 3 floating-point division | Integer bounds; pagination unit tests |
| Named footnotes did not receive definitions | Named definition recognition; unit and pipeline tests |
| Headerless Bootstrap tables inserted extra rows | Promote the first row once; empty-data regression |
| Footnotes leaked across publications | One registry per compilation; consecutive/interleaved compilation tests |
| Web/Kindle builds leaked settings and instance flags | Per-render context and copied publication state; success, failure, and repeat-build tests |
| Retired access, download, and source-import APIs remained callable | Unused access API removed; superseded screens redirect; permission and upload tests |
| Duplicate SectionMove and unreachable remove_supports | Removed; retained preprocessing and Word conversion tests |
| Configured commands split quoted values incorrectly | Explicit argv parsing and unresolved-value errors; command regressions |
| Engine script/manage used the wrong directory depth | Root-aware Poetry launcher; command-forwarding regression |
| Updater no-preprocess was ineffective | CLI modifier normalization and standard workflow spelling; actual command-dispatch regression |
| Word input ending with emphasis markers raised IndexError | Bounds checks; malformed-emphasis tests |
| Obsolete chart/serialization/footnote script modules remained | Unreferenced modules and tests that merely preserved their existence removed |
| Autoprefixer failure was ignored | Missing tooling or nonzero compilation fails visibly; SCSS integration tests |

## Remaining integration limits

- A real MOBI build is not verified by the default suite. Kindle service tests use
  an injected generator; an installed binary must be checked separately.
- Google Drive downloads require credentials and network access. Configuration
  and preprocessing tests do not establish access to remote documents.
- TinyPNG's remote API branch requires credentials; the offline image path is
  tested.
- Per-paragraph image-export rules use a fake browser for detailed filtering
  and crop tests. The real-browser suite additionally exports one social card
  from the live preview using an explicit preview origin and current paragraph
  selectors; it does not visually compare every generated card.
- External Sass/PostCSS and browser tests require their executables. Skipped
  integration tests should be reported as skipped, not treated as proof of
  compatibility.
