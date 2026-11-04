# Stringprint2

Stringprint publishes long-form Markdown or Word-derived content as accessible
static websites, with stable paragraph links, navigation, notes, search, social
cards, and downloadable formats. Web builds generate EPUB by default. MOBI is
optional and requires an installed Kindle generator.

## Setup

The engine can be installed independently or used as a submodule of a publication
repository. It requires Python 3.14, Node.js, and the native tools exercised by the
integration suite.

From the engine checkout:

```sh
poetry install
npm ci
poetry run playwright install chromium
```

Create an application configuration file outside the engine, for example:

```yaml
SITE_NAME: Research publications
SECRET_KEY: replace-with-a-local-secret
ORGS:
  default:
    storage_dir: /absolute/path/to/document-repository
    publish_dir: /absolute/path/to/published-output
```

Then initialize and run it from any working directory using the installed commands:

```sh
export STRINGPRINT_CONFIG=/absolute/path/to/config.yaml
export STRINGPRINT_NODE_MODULES=/absolute/path/to/engine/node_modules
stringprint-manage migrate
stringprint
```

Use `poetry run` before these commands when using Poetry's environment. The source
repository's existing `script/setup`, `script/update`, `script/console`, and
`script/server` remain supported; `script/update` installs both locked toolchains.
Relative application-config paths resolve against the config file, not the shell's
working directory. The historical in-engine config file remains a fallback.

## Authoring and operations

A source repository contains:

- `_conf/settings.yaml`: organisation branding, defaults, and configured commands.
- `_docs/<slug>/settings.yaml`: publication configuration.
- `_docs/<slug>/document.md`: source text, or another configured `file_source`.
- `_docs/<slug>/assets/assets.yaml`: image, table, and HTML declarations.
- `_static/` and `_templates/`: optional organisation overrides.

Configuration keys are validated. See [configuration models](stringprint2/configuration/models.py)
for supported fields and [theme variables](docs/publication-theme-variables.md) for
stable SCSS customization. Unknown keys are errors; they are not arbitrary template
variables. New table assets use XLSX; existing XLS remains readable and can be
converted with `stringprint-migrate-tables`.

The browser management interface is at `/manage/`. It supports preview, processing,
rendering, archives, and explicitly enabled publishing. Publication, organisation,
and header settings are read-only: edit source files and reload them. Login and
organisation membership protect management actions.

The interactive shell provides `listorgs`, `setorg`, `listdocs`, `setdoc`, `load`,
`loadall`, `loadunloaded`, `process`, `preprocess`, `render`, `renderebook`,
`renderkindle`, `renderzip`, `publish`, `convertword`, `mergepdf`, `pdfpng`, and
`hero`. It also runs named configured commands. Existing command modifiers remain
supported, including `--no-preprocess`, `--no-refresh`, `--no-hero`,
`--no-thumbnail`, and `--no-render-zip`.

Commands can be supplied together:

```sh
stringprint --setdoc report-slug --process --no-preprocess --publish
stringprint --no-server --setdoc report-slug --process --no-preprocess
```

Web rendering and social-card capture require the preview server. The normal
console supervises that server and the operation worker. `--no-server` is useful
for processing-only commands. CLI publish executes preparation, archive creation,
and the configured publish command as one locked workflow. Browser publishing
uses the same workflow, with explicit optional media-preparation checkboxes.

See [management operations](docs/management-operations.md) for permissions,
cancellation, retry, retention, and diagnosis.

## Source conventions

Top-level H1 headings start publication sections; lower heading levels create
subsections. Ordinary paragraphs, lists, blockquotes, and tables are preserved.
`[[` and `]]` delimit expandable notes. Footnotes use `[^name]` references and
`[^name]: definition`; named citation text can use `[^name||Citation]`.
Assets are referenced as `[asset:asset-slug]`; `[header-asset:asset-slug]` attaches
an asset to a section header.

Paragraph identifiers are reconciled against `_paragraphs.yaml` across revisions.
That file is durable compatibility state: retaining it preserves old incoming
links even when paragraphs move or change.

Organisation and publication `commands` can specify quoted argv templates, such
as `python publish.py "{{article.slug}}"`, or existing `module::` preprocessors.
Commands execute without a shell; unresolved substitutions and failed processes
stop the operation.

## Development

```sh
poetry run ruff check .
poetry run mypy
poetry run pytest --create-db
npm run check
npm run build
poetry run pytest tests/bake tests/external -m "external and not needs_network"
```

The default Python suite excludes external integrations. Real browser checks need
Playwright Chromium; stylesheet checks need `npm ci`. Tests copy source fixtures
to temporary storage and isolate database/media/build state.

See [architecture and ownership](docs/architecture.md) for the module map,
configuration lifecycle, rendering contracts, and artifact policy, and the
[feature inventory](docs/feature-inventory.md) for behavior and test coverage.
