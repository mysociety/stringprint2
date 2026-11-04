# Architecture and ownership

Stringprint has two repositories: the independently installable engine and a
publication source repository which pins the engine as a submodule. Python app
imports use `stringprint2.*`; historical `stringprint`, `frontend`, `charts`,
`proj`, and `publication_management` imports alias those same modules for existing
preprocessors. Django app labels and stored JSON type names remain unchanged.

## Entry points and configuration

- `stringprint` / `python -m stringprint2`: import-safe console entry point;
  `bootstrap.py` initializes Django explicitly before loading `cli.py`.
- `stringprint-manage`: Django management commands. `script/manage` and
  `stringprint2/manage.py` remain compatibility launchers.
- `stringprint-validate`: read-only source configuration validation.
- `stringprint-migrate-tables`: migration of legacy XLS assets to XLSX.

`STRINGPRINT_CONFIG` selects the application YAML file. Relative paths in that
file resolve against its directory. `configuration/runtime.py` validates it using
`RepositoryConfig`; settings are assigned explicitly, without injecting arbitrary
YAML into module globals. Caller-selected Django settings are respected.

New installations write database, media, and static build state below the source
repository's `.stringprint/`. `STRINGPRINT_STATE_DIR` overrides that state root.
Existing in-engine databases and media directories remain usable, and `MEDIA_ROOT`
in application YAML still overrides media storage. Migration to another state
location is an explicit operator action; startup does not move existing data.

Custom organisation and publication options remain in `extra_values`. Legacy
template attribute access falls back to that mapping; it does not inject keys
into the model's instance dictionary. Only explicitly supported authored fields
can receive historical overrides. Model methods and internal state retain their
normal meaning.

## Publication flow

| Responsibility | Owner |
| --- | --- |
| YAML validation | `configuration/` |
| Configuration-to-model assignments | `services/publication_loading.py` |
| Command resolution and subprocess invocation | `services/configured_commands.py` |
| Compile source to sections, references, and diagnostics | `services/document_compilation.py`, `stringprint/tools/deepink.py` |
| Compiled data and stable paragraph identities | `document_structure.py` |
| HTML and document navigation | `presentation/document.py`, `presentation/navigation.py` |
| Apply compiled data and active asset IDs | `Version.process` persistence adapter |
| Preserve paragraph link history | `services/paragraph_links.py` |
| Image derivatives | `services/image_derivatives.py` |
| Social-card screenshots and scoped browser lifetime | `services/paragraph_screenshots.py` |
| Fixed load/process/render/archive/publish operations | `services/publication_operations.py` |
| Foreground locks, queue, worker, cancellation, logs | `publication_management/` |
| Page presentation and shared render options | `stringprint/views.py`, `services/render_context.py` |
| Static, EPUB, Kindle and ZIP output | `services/*rendering.py`, `publication_archiving.py` |

The compiler accepts source text, a seed, and a slug-to-ID asset catalog. It
returns sections, referenced IDs, and diagnostics. It does not query or update
Django models. `Section`, `Graf`, and `Footnote` retain their historical serialized
representation in `document_structure.py`. The old `tools.deepink` imports
re-export the same classes. Legacy template methods delegate to presentation
helpers. `DocumentPresentation` owns a detached section tree, keeping rendering
annotations out of the compiled source objects. Parsing and paragraph hashing
remain in `tools/deepink.py`; no stored publication or paragraph ID migration is
required.

`Article.content()` is a read-only lookup. Source loading and processing call
`ensure_content()` explicitly. Missing content raises `Version.DoesNotExist`;
duplicate current versions raise `Version.MultipleObjectsReturned` without
removing any rows. Conflicts require explicit inspection and repair, never a
render-time cleanup.

Operation dispatch is an exhaustive selection over the validated request types.
There is no mutable handler registry. CLI commands share publication lookup,
output-path construction, and locked execution; rendering varies by format.

Both CLI and queued publish operations run preparation, archive rendering, and
the configured publish command under one publication lock. Preparation failures
stop the workflow. Hero and thumbnail regeneration are explicit request options:
the CLI keeps its existing enabled defaults and disabling flags; web operations
expose optional checkboxes and default to reusing existing media.

## Rendering

Publication views use ordinary Django `View` dispatch and explicit context
construction. Account pages also use Django views and explicit URL patterns;
the old hook framework and retired upload/edit forms are removed. Static baking invokes the
same publication views with a publication and `PublicationRenderContext` supplied
as view options; it does not manufacture nested view classes.

The render context owns output availability, sharing URL, bake mode, and collected
CSS/JavaScript dependencies. The publication compression tag collects URLs from
its rendered fragment, including cache hits, without mutating a model through a
global signal. Each page receives a detached model snapshot for legacy template
helpers; transient flags and presentation caches never belong to the caller's
persisted instance. A complete web build is staged before replacing output.

## Source authoring and derived state

Publication, organisation, and header settings screens are read-only. Edit the
repository files and reload/process to preview changes. Account credentials remain
editable through the normal account screens.

| Class | Examples | Policy |
| --- | --- | --- |
| Authored inputs | YAML, source Markdown, images, templates, SCSS | Version control |
| Durable compatibility state | `_paragraphs.yaml` | Preserve historical link mappings; never blanket-delete as a cache |
| Imported source snapshots | Downloaded Word/PDF files | Decide retention per source workflow |
| Reproducible outputs | Publication ZIPs, rendered sites, derived images | Future removal policy; existing tracked files are retained in this refactor |
| Local operational state | Database, logs, locks, compiled static files | `.stringprint/`, untracked |

`static_sources/` contains checked-in static assets; `web/` holds first-party SCSS
and compiled TypeScript; `vendor/` holds explicitly vendored assets. Django static
and compression output goes into `.stringprint/static`, never these source trees.
Tests use empty temporary output directories and read authored assets in place.

## Tooling and verification

The engine owns Ruff and mypy configuration plus Python and frontend dependencies.
Type checking is strict at declared service/configuration/management boundaries;
legacy model and parser bodies are not all strictly checked. The parent retains
its own repository script tests and production-corpus validation.

`npm ci` installs TypeScript, Sass, PostCSS, and Autoprefixer from the engine lock.
The compiler invokes those local executables and resolves the plugin's explicit
module entry point. Installed Python packages can use the toolchain from an engine
checkout through `STRINGPRINT_NODE_MODULES=/absolute/path/to/node_modules`.
Docker uses the same lockfile and sets that variable to its installed toolchain.
No build step implicitly downloads tools through `npx`.

Compatibility gates cover clean and populated migrations, paragraph keys, source
fixtures, CLI/worker operations, repeated and failed bakes, and desktop/mobile
browser behavior. See [feature inventory](feature-inventory.md) and
[management operations](management-operations.md) for coverage and integration
requirements. Credential-dependent integrations and a real Kindle generator are
separate from offline verification.
