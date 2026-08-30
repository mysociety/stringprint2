# stringprint2 feature inventory

What this application does, where each behaviour lives, and what the test suite
pins. Written as the reference point for the Python 3.14 / Django 5.2 upgrade:
the suite's job is to make that upgrade a diff you can reason about, and this
document's job is to say what the suite is and is not watching.

Line references are to the tree as it stands on Django 2.2.25 / Python 3.8.

## Running the tests

```bash
cd stringprint2
python -m pytest                # default: no sass, no browser, no network (~16s)
python -m pytest -m ""          # everything, including the external tier (~70s)
python -m pytest -m external    # only the external tier
```

Markers: `external` (needs a binary or the network, deselected by default),
`needs_sass`, `needs_chrome`, `needs_network`, `slow`.

Dependencies are declared in both `pyproject.toml` files. In a container built
before they were added: `pip install "pytest~=7.4" "pytest-django~=4.5"`.

The suite points the app at `tests/fixtures/doc_source` via `STRINGPRINT_CONFIG`
(see [Settings bootstrap](#settings-bootstrap)). It copies that tree to a
temporary directory first, because processing writes `_paragraphs.yaml` back
into the document folder. Nothing the suite does touches the working tree; the
only files written inside the repo are `static/CACHE` and `static/COMPILED`
during the bake tests, both of which are gitignored.

## Pipeline

The canonical order, from `SPPrompt.do_process` (`__main__.py:514`):

| # | Step | Entry point |
|---|---|---|
| 1 | Run the document's preprocess command | `Article.run_command` (`models.py:1260`) |
| 2 | Read `settings.yaml` | `Article.load_from_yaml` (`models.py:378`) |
| 3 | Read `assets/assets.yaml`, build derived images | `Article.import_assets` (`models.py:569`) |
| 4 | Read the markdown source | `Article.load_from_file` (`models.py:1358`) |
| 5 | Parse into the Section/Graf tree | `Article.process` → `Version.process` → `deepink.process_ink` |
| 6 | Update the stable paragraph anchors | `Version.update_paragraph_links` (`models.py:2062`) |

Then, separately: `Article.render` bakes the static site, `create_ebook` builds
the epub, and `create_kindle` builds the mobi (out of scope — see below).

There are no Django management commands. Everything is a `do_*` method on
`SPPrompt` in `__main__.py`, dispatched by `cmd.Cmd`.

**`__main__.py` must never be imported by a test.** At module level it calls
`load_org_details()` (which writes to the database) and `do_startserver()`
(which spawns a `runserver` subprocess) — `__main__.py:786-791`. Its helpers are
reachable through `stringprint.tools.preprocessing` instead.

## Settings bootstrap

`proj/settings.py` reads a YAML config **at import time**, copies every
top-level key into module globals, and derives `STATICFILES_DIRS`,
`ORG_TEMPLATE_DIRS` and `TEMPLATES[0]["DIRS"]` from
`ORGS[<slug>]["storage_dir"]` there and then.

`STRINGPRINT_CONFIG` overrides the config file path. When it is unset the
behaviour is exactly as before: use `proj/conf/config.yaml`, seeding it from
`config-example.yaml` on first run. `MEDIA_ROOT` also reads from the config,
with the same default as before; its trailing separator is load-bearing,
because `create_responsive` and `create_tiny` build paths by concatenation
(`models.py:1546`, `1621`).

`proj/test_settings.py` layers test-only overrides on top. Two matter:

- `STATIC_PRECOMPILER_DISABLE_AUTO_COMPILE` plus `COMPRESS_ENABLED = False`
  mean the default suite needs neither `sass` nor `npx`. The bake tests turn
  both back on.
- `TEMPLATES[0]["OPTIONS"]["debug"]` has to be set explicitly, because
  `settings.py` captures `DEBUG` by value when it builds `TEMPLATES` — before
  its own later `DEBUG = True` reassignment.

## Feature coverage

### Configuration

| Feature | Implementation | Tests |
|---|---|---|
| Config file override | `proj/settings.py` | `config/test_settings_bootstrap.py` |
| Org settings → model | `Organisation.load_from_yaml:162` | `config/test_organisation_load.py` |
| Org links, ordering | `Organisation.org_links_ordered:194` | `config/test_organisation_load.py` |
| Storage/publish/template dirs | `Organisation` properties `:122-136` | `config/test_organisation_load.py` |
| Org SCSS discovery | `Organisation.org_scss:145` | `config/test_organisation_load.py` |
| Doc settings → model | `Article.load_from_yaml:378` | `config/test_article_load_from_yaml.py` |
| Legacy alias `sections_over_pages`→`multipage` | `models.py:392` | `config/test_article_load_from_yaml.py` |
| Legacy alias `pdf`→`pdf_file` | `models.py:397` | `config/test_article_load_from_yaml.py` |
| Org `default_values` templating | `models.py:403` | `config/test_article_load_from_yaml.py` |
| Empty value suppresses an org default | `models.py:403` | `config/test_article_load_from_yaml.py` |
| Unknown keys → `extra_values`, pruning | `models.py:383,411` | `config/test_article_load_from_yaml.py` |
| Header image, `size: background` → −1 | `models.py:418` | `config/test_article_load_from_yaml.py` |
| Book cover | `models.py:440` | `config/test_article_load_from_yaml.py` |
| `production_url` default | `models.py:448` | `config/test_article_load_from_yaml.py` |
| Migrations apply; custom fields round-trip | `stringprint/migrations/` | `config/test_migrations.py` |

### Assets

| Feature | Implementation | Tests |
|---|---|---|
| `assets.yaml` → `Asset` rows | `Article.import_assets:569` | `config/test_import_assets.py` |
| `content_type: image` | `models.py:606` | `config/test_import_assets.py` |
| `content_type: table` | `models.py:626` | `config/test_import_assets.py` |
| `content_type: table-no-header` | `models.py:585` | `config/test_import_assets.py` |
| `content_type: html` | `models.py:628` | `config/test_import_assets.py` |
| `alt_text` falls back to `caption` when **absent** | `models.py:594` | `config/test_import_assets.py` |
| `longdesc` → markdown | `models.py:597` | `config/test_import_assets.py` |
| Responsive variants (768–1920) + webp | `HeaderMixin.create_responsive:1561` | `config/test_import_assets.py` |
| Tiny variant (offline PIL fallback) | `HeaderMixin.create_tiny:1529` | `config/test_import_assets.py` |
| Ratio / average colour | `models.py:1458,1469` | `config/test_import_assets.py` |
| Spreadsheet → chart columns | `Chart.load_from_file:125` | `unit/test_charts_display.py` |
| Percent / currency / `split[` / year columns | `Column.__init__:44` | `unit/test_charts_display.py` |
| Table rendering | `Chart.render_html_table:198` | `unit/test_charts_display.py` |

### Markdown parsing

Every construct below is exercised by `tests/fixtures/doc_source/_docs/kitchen-sink/document.md`.

| Construct | Handler | Tests |
|---|---|---|
| `# H1` → section | `deepink.py:1027` | `pipeline/test_process_ink_structure.py` |
| `##`/`###`/`####` → graf title | `deepink.py:1000` | `pipeline/test_process_ink_structure.py` |
| Consecutive headings → title-only graf | `deepink.py:1009` | `pipeline/test_process_ink_structure.py` |
| Duplicate heading anchors (`_1`, `_2`) | `get_anchor_offset:984` | `pipeline/test_process_ink_structure.py` |
| Paragraphs, `ul`, `ol` | `good_to_extract:953` | `pipeline/test_markdown_features.py` |
| Blockquotes, grouping | `Graf.block_start:825` | `pipeline/test_process_ink_structure.py` |
| Raw `<table>` HTML | `good_to_extract:953` | `pipeline/test_markdown_features.py` |
| Footnotes `[^1]`, `[^*]` | `Footnote:59`, `connect_to_footnote:602` | `pipeline/test_markdown_features.py`, `unit/test_deepink_footnote.py` |
| Labelled footnote (`Label\|\|content`) | `Footnote.set_content:79` | `unit/test_deepink_footnote.py` |
| Asides `[[ ]]`, all four graf types | `Graf.process:613` | `pipeline/test_process_ink_structure.py` |
| Lone `[[`, trailing `]]`, `]][[` | `deepink.py:1039`, `move_extended_close:879` | `pipeline/`, `unit/test_deepink_text_processors.py` |
| `[asset:slug]`, missing slug | `deepink.py:704` | `pipeline/test_markdown_features.py` |
| `[header-asset:slug]` | `deepink.py:691` | `pipeline/test_process_ink_structure.py` |
| `[tag:]`, `[para:]`, `[page:]` | `Graf.process:613` | `pipeline/test_process_ink_structure.py` |
| `[catchup: …]` | `deepink.py:1038` | `pipeline/test_process_ink_structure.py` |
| `""quoted""` and the `=""` escape | `deepink.py:663` | `pipeline/test_markdown_features.py` |
| Smart quotes | `quote_fix:867` | `unit/test_deepink_text_processors.py` |
| Paragraph keys, seeded and sequential | `RandomAssignment:32` | `unit/test_random_assignment.py` |

### Output

| Feature | Implementation | Tests |
|---|---|---|
| Article page, single and multipage | `ArticleView:250` | `render/test_article_view.py` |
| Org template override | `_get_template_path:392` | `render/test_article_view.py` |
| Open Graph / Twitter metadata | `social_settings:270` | `render/test_article_view.py` |
| `?screenshot` forces single page | `views.py:315` | `render/test_article_view.py` |
| Cross-chapter `#tag.` and `#anchor` rewriting | `Graf.display:764` | `render/test_article_view.py` |
| TOC JSON | `TOCView:129` | `render/test_other_views.py` |
| Plain text | `TextView:206` | `render/test_other_views.py` |
| Search page and index | `TipueSearchView`, `TipueContentView` | `render/test_other_views.py` |
| Kindle HTML / OPF / NCX templates | `KindleView:79` etc. | `render/test_other_views.py` |
| Epub chapter | `EbookChapterView:120` | `render/test_other_views.py` |
| Per-paragraph redirect page | `RedirectLink:396` | `render/test_other_views.py` |
| Static bake, file manifest | `Article.render:808` | `bake/test_render_bake.py` |
| Multipage chapter files | `models.py:987` | `bake/test_render_bake.py` |
| Compressed CSS/JS collected | `compression_callback:28` | `bake/test_render_bake.py` |
| Epub build | `create_ebook:1093` | `external/test_ebook.py` |
| Paragraph social cards | `export_paragraph_images:490` | `external/test_screenshots.py` |
| SCSS compilation | `CustomSCSS:39` | `external/test_scss_pipeline.py` |
| CSS minification, SVG-safe | `svg_safe:15` | `unit/test_compiler_svg_safe.py` |

### Preprocessing and commands

| Feature | Implementation | Tests |
|---|---|---|
| `module::` command form | `Article.run_command:1281` | `config/test_run_command.py` |
| Template + subprocess form | `Article.run_command:1303` | `config/test_run_command.py` |
| Org vs document command precedence | `models.py:1266` | `config/test_run_command.py` |
| `SectionDelete`, `SectionMove`, `TextSnip` | `preprocessing.py:65,132,190` | `external/test_preprocessing.py` |
| `]][[` separation | `general_find_replace:196` | `external/test_preprocessing.py` |
| PDF cover merge | `merge_pdfs:17` | `external/test_preprocessing.py` |
| `.docx` → markdown fixups | `word_convert.py` | `unit/test_word_convert.py` |
| Paragraph link persistence | `Version.load/save_paragraph_links:2033` | `config/test_paragraph_links.py` |
| Orphan re-anchoring | `Version.anchor_orphans:2120` | `config/test_paragraph_links.py` |

### Not covered

- **kindlegen / `create_kindle` / `renderkindle`.** The binary is unavailable
  and there is no plan to restore it. `Article.render` defaults `kindle=True`,
  so every bake test passes `kindle=False` — a permanent constraint, not a
  workaround.
- **Google Drive download** (`google_download.py`) — needs credentials.
- **Unsplash cookiecutter hook** (`_docs/_template/hooks/`) — lives in the
  document-source repo, needs `UNSPLASH_CLIENT_ID`.
- **A real headless-Chrome screenshot run.** `BAKE_SERVER` is a local variable
  inside `export_paragraph_images` (`models.py:508`), so there is no seam to
  point it at pytest's `live_server`. The surrounding logic is covered with a
  fake driver instead.
- **`frontend/` views** beyond the pagination helpers. Most of that module is
  already broken (see below) and unused by the CLI workflow.
- **TinyPNG's key-present branch** — only the offline PIL fallback runs.

## Defects fixed

Nine defects were repaired once the suite was in place to catch the fallout.
Each had been pinned by a test first, so the repair is visible as an xfail
turning into a real assertion.

| Defect | Where | Fix |
|---|---|---|
| `JsonBlockField(default={})` handed **every** instance the same dict — seven fields across four models. Rows still saved correctly, because whatever the shared dict held at `save()` was what got serialised, which is why it survived unnoticed; the damage was to any process holding several unsaved instances, which is what `loadall` and `loadunloaded` produce. | `models.py` ×7 | `default=dict`, plus migration `0042` |
| `HomeView.view` filtered `Article.objects.filter(public=True)`; there is no `public` field, so `/preview/` raised `FieldError`. | `views.py:76` | list all articles, newest first |
| `ink/base.html` included `ink/cookie.html`, which has never existed in this repository. Only `home.html` extends `base.html`, so this was the second reason the preview index 500'd. | `templates/ink/base.html:92` | include removed. Note `Organisation.ga_cookies` still has no template consumer |
| `AssetView.view`'s else branch read `charts = [charts]`, referencing the local before assignment, so any asset without a chart raised `UnboundLocalError`. Only table assets could be viewed. | `views.py:54` | `charts = []` |
| `ChartCollection.__init__` called `x.package_name()` on each chart, but `package_name` is a string attribute on `ChartType`, not a method on `Chart`. Any non-table chart raised `AttributeError`, so the collection only worked when it ended up empty. | `charts/display.py:36` | `Chart.package_name()` looks the type up in the registry and falls back to `corechart` |
| `GroupedPage.reasonable_range` computed `full_range / 2`, a float under Python 3, so `range()` rejected the bounds. Every branch except the short-paginator early return was dead. | `frontend/views.py:45` | floor division |
| Footnote definitions were matched with `\[\^[0-9\*]+\]\:` — digits and stars only — while the *reference* syntax has always allowed names. A named footnote such as `[^scotedit]` parsed as a reference and then never picked up its content. At least one production document uses this. | `deepink.py:604` | regex widened to letters, underscore and hyphen |
| The autoprefixer pass never ran. `postcss-cli` and `autoprefixer` were installed globally but `postcss` itself was an unmet peer dependency, so `npx postcss --use autoprefixer` exited `ERR_MODULE_NOT_FOUND` — and `compile_file` captured the return code without checking it, so published CSS was unprefixed and nothing said so. | `Dockerfile:14`, `compiler.py:99` | `postcss` added to the image; a non-zero exit now raises `StaticCompilationError`. `--no-map` added too, or postcss appends a base64 copy of every stylesheet to itself |
| `makemigrations --check` had been failing: migration `0005` recorded the chart column as `charts.fields.ChartField` while `models.py` imports it as `stringprint2.charts.fields.ChartField` — an artefact of the doubled path making one module importable under two names. | `migrations/0005` | recorded in migration `0042` |

Fixing the image build means the base image needs a rebuild and a SHA bump
before the autoprefixer change takes effect in CI; until then `compile_file`
raises rather than silently producing unprefixed CSS, which is the point.

## Known defects

Still outstanding. Each one reachable by a test is pinned, with a
`strict=True` xfail wherever the code can actually be executed, so the test
flips to a failure the moment it is repaired.

| # | Defect | Where | Pinned by |
|---|---|---|---|
| 1 | `render_bootstrap_table`'s `if no_header` block sits **inside** the row loop, inserting the header once and then an empty list for every remaining row. The equivalent in `render_html_table` is correctly outside. | `charts/display.py:188` | `unit/test_charts_display.py` |
| 2 | `Footnote.note_count` and `Footnote.all` are class attributes. `process_ink` resets the first and never the second, so the registry grows for the life of the process — and `connect_to_footnote` scans it for an empty-content entry with a matching ref, so one document's unresolved footnote can capture a later document's definition. | `deepink.py:60-61` | `unit/test_deepink_footnote.py`, `conftest.py` autouse reset |
| 3 | `Article.render` mutates six settings (`MEDIA_URL`, `SITE_ROOT`, `STATIC_URL`, `COMPRESS_URL`, `DEBUG`, `COMPRESS_ENABLED`) and sets `baking` on the instance, restoring none of them. | `models.py:872-878,955` | `bake/test_render_bake.py`, `conftest.py` autouse restore |
| 4 | `Asset.get_chart_image` calls `contents.decode("base64")` on a `str` (impossible since Python 2) and uses `find_element_by_id` (removed in Selenium 4). | `models.py:2314` | `external/test_known_broken.py` |
| 5 | `Article.authenticate` references an `Access` model that does not exist. | `models.py:656` | `external/test_known_broken.py` (xfail) |
| 6 | `frontend/views.py` calls `trigger_reprocess`, `trigger_render`, `trigger_source_import` and a `downloads` relation, none of which exist on `Article`. | `frontend/views.py` | not pinned |
| 7 | `preprocessing.py` defines `SectionMove` **twice**. The first is shadowed and would raise `AttributeError` on construction — its `__post_init__` reads `self.before`, which is not one of its fields. | `preprocessing.py:88,132` | `external/test_preprocessing.py` |
| 8 | `run_command` splits the rendered command on single spaces with no quoting, so any templated value containing a space becomes several argv entries, and an unresolved variable leaves an empty one. | `models.py:1313` | `config/test_run_command.py` |
| 9 | `script/manage` resolves to `stringprint2/stringprint2/stringprint2/manage.py` — one level too deep. The devcontainer `postCreateCommand` uses it. | `script/manage` | not pinned |
| 10 | `docker-compose.yml` mounts the config one directory above where `settings.py` reads it, leaving empty directories on disk. `STRINGPRINT_CONFIG` is now the supported way to inject it. | `docker-compose.yml` | not pinned |
| 11 | `do_process` tests `"--no-preprocess" in refresh`, but `.github/workflows/updater.yml` passes `no-preprocess`, so the preprocess step runs regardless. | `__main__.py:519` | not pinned |
| 12 | `remove_supports` returns its argument on the first line; the rest of the body is unreachable. | `word_convert.py:361` | `unit/test_word_convert.py` |
| 13 | `fix_markdown` indexes `text[pos + 2]` with no bounds check, so a document ending in `__` raises `IndexError`. | `word_convert.py:97` | `unit/test_word_convert.py` |
| 14 | Dead modules: `tools/charts.py`, `tools/serial.py`, `tools/footnote_convert.py`. `frontend/migrations` 0002 and 0004 create `Download` and `TokenSetting`, since deleted. | — | `external/test_known_broken.py` |


## Upgrade risk register

Ordered by how likely each is to stop the upgrade dead.

1. **Tuples in `TEMPLATES[0]["DIRS"]`.** `ORG_TEMPLATE_DIRS` holds
   `(namespace, path)` pairs, which only work because `proj.loaders.NamespaceAwareLoader`
   unpacks them. Django validates `TEMPLATES` harder with each release, and this
   fails at `django.setup()` — taking the whole suite down at collection. Keep
   `config/test_settings_bootstrap.py` runnable on its own as the first
   diagnostic. `STATICFILES_DIRS` uses the same prefix-tuple form.
2. **`django.conf.urls.url`**, removed in Django 4.0, used by `proj/urls.py` and
   throughout `useful_inkleby`.
3. **`django_compressor 2.2` and `django-static-precompiler 2.1`.** Neither
   supports Django 5.2. The whole bake tier depends on them.
4. **The three git-pinned forks** — `useful_inkleby@d2`,
   `django-pipeline-csscompressor`, `python-unsplash`. `useful_inkleby` supplies
   the view framework, the serialisers and both custom model fields; it has no
   maintained Django 5 story and will need forking.
5. **`selenium 3.13`** — `find_element_by_*` removed in Selenium 4.
6. **`Pillow 8.3.2`** — `Image.BICUBIC` and `ANTIALIAS` removed in Pillow 10
   (`create_responsive` uses `BICUBIC`).
7. **`xlrd 1.2`** — `.xls` support; 190 production assets are `.xls`.
8. **`Markdown 2.6.8`** — the parser is invoked with no extensions, so a bump
   changes graf HTML. `pipeline/test_markdown_features.py` is the tripwire.
9. **`webptools 0.0.2`** ships its own `cwebp`; `create_responsive` raises
   `ValueError` if it produces nothing, which would fail every image test at
   once. `config/test_cwebp_available.py` is named first so the cause is
   obvious.
10. **Invalid escape sequences** (`"\d"`, `"\("`, `"\_"`) across
    `word_convert.py`, `views.py`, `footnote_convert.py` and `useful_inkleby`.
    Currently `DeprecationWarning`; a `SyntaxWarning` now and an error later.
11. **Import-time side effects in `__main__.py`** — a classic 3.14 breakage
    surface, and the reason no test may import it.
12. **`pytest-django` needs ≥ 4.9 for Django 5.2**; the pins here are `^4.5`.

## Appendices

### A. Document `settings.yaml` keys

Frequency across the 66 production documents in the parent repository, and
which fixture document exercises each.

| Key | Count | Fixture |
|---|---|---|
| `title`, `short_title`, `description`, `byline`, `authors`, `cite_as`, `file_source`, `publish_date`, `sections_over_pages`, `display_notes`, `display_footnotes_at_foot`, `repo_slug` | 66 | all four |
| `header` | 65 | all but `minimal-doc` |
| `book_cover` | 55 | `kitchen-sink` |
| `copyright` | 53 | `kitchen-sink`, `legacy-doc`, `multipage-doc` |
| `seed` | 52 | `kitchen-sink` (−1), `legacy-doc` (13) |
| `subtitle` | 40 | `kitchen-sink`, `multipage-doc` |
| `pdf` → `pdf_file` | 38 | `kitchen-sink` |
| `commands` | 38 | `kitchen-sink` |
| `google_doc_url` | 34 | `kitchen-sink` |
| `pdf_location` | 28 | `legacy-doc` |
| `unsplash_title_image_url` | 25 | `kitchen-sink` |
| `bottom_iframe` (always empty, to suppress the org default) | 4 | `legacy-doc`, `multipage-doc` |
| `skip_epub` | 2 | `legacy-doc`, `multipage-doc` |
| `files` | 1 | `legacy-doc` |

`header` sub-keys: `location` (65), `size` (65), then the Unsplash hook's
`alt_text`/`source_url`/`credit`/`description` (24 each) and `unsplash_id` (22).
`size` is `6` in 64 documents and `4` in one; the loader also accepts
`background`, which becomes −1 (`multipage-doc` covers that).

Model fields no production document sets, and which the fixtures therefore do
not exercise: `current_version`, `kindle_location`, `first_section_name`,
`needs_processing`, `reprocess_source`, `display_toc`, `include_citation`.

### B. `assets.yaml`

474 assets across 65 files. Keys: `content_type` (474), `type` (474),
`caption` (474), `alt_text` (234), `longdesc` (6).

`content_type`: `image` 274, `table` 198, `html` 2. `table-no-header` is
supported by the loader but unused in production — the fixture covers it anyway.

`type`: `png` 236, `xls` 190, `jpeg` 30, `xlsx` 8, `jpg` 8, `html` 2.

The file on disk must be named `<slug>.<type>` in the assets directory.

### C. Org `_conf/settings.yaml`

`name`, `twitter`, `ga_code`, `ga_cookies`, `publish_root`, `icon`,
`include_favicon`, `orglinks` (name → `{link, order}`), `commands` (name →
shell string or `module::` path), `default_values` (name → Django template
rendered against the document's own settings). Anything else lands in
`extra_values`, which `Organisation.__init__` splats onto the instance.

### D. External dependencies

| Dependency | Used by | Marker | Present in the image |
|---|---|---|---|
| `sass` | `CustomSCSS` | `needs_sass` | yes |
| `npx` + `postcss` + `autoprefixer` | `CustomSCSS` | `needs_sass` | yes (`postcss` added to the image) |
| `chromedriver` + `google-chrome` | `export_paragraph_images` | `needs_chrome` | yes (faked in tests) |
| `cwebp` | `create_responsive` | — | bundled inside `webptools` |
| PyMuPDF | `merge_pdfs`, `pdf_page_to_png` | `external` | yes |
| `geckodriver` | `Asset.get_chart_image` | — | **no** (and the code is broken anyway) |
| `kindlegen` | `create_kindle` | — | **no**, and out of scope |
| Google Drive API | `google_download.py` | `needs_network` | needs `GDRIVE_SERVICE_USER` |
| TinyPNG API | `create_tiny` | `needs_network` | offline fallback used |

### E. Fixture documents

`tests/fixtures/doc_source/` mirrors the shape of a real document-source
repository. Binary fixtures are generated by `tests/fixtures/make_binaries.py`,
which reproduces them byte for byte — `python tests/fixtures/make_binaries.py --check`
asserts that, so drift is detectable.

| Document | Covers |
|---|---|
| `minimal-doc` | the absent-everything paths: required keys only, no `header`, no `assets/` directory at all, no `_paragraphs.yaml`, no `production_url` |
| `kitchen-sink` | the full modern key set, all four asset content types, and every markdown construct |
| `legacy-doc` | `seed: 13`, `pdf_location`, empty `bottom_iframe`, `files`, `skip_epub`, `[page:N]` markers, and stale paragraph links plus previously rendered link files, so orphan re-anchoring runs |
| `multipage-doc` | `sections_over_pages`, `header.size: background`, `display_notes: false`, duplicate section names, and cross-chapter `[tag:]` and `#anchor` links |
