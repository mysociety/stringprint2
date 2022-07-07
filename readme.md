# Stringprint2 

Stringprint is a better way of publishing longform content on the internet. It aims to fill a gap in the lack of tools for longform publishing aimed at the policy/research community. The goal is to create more accessible and readable documents than the common reliance on PDF (while accepting that PDFs are part of common workflows and will also need to be provided). 

Features:
* Generate TOC and navigation from header structure. 
* Stringprint takes markdown/html or a Word document and publishes the content as an accessible webpage.
* Responsive design to make it easy to read on mobile devices. 
* Outputs additional formats such as: .mobi, .epub and a low formatting version for slow connections or long term compatibility. 
* Creates a navigation structure and uses a deep linking system so each paragraph can be individually linked and shared.
* Creates a link for each pargraph with a social preview of that paragraph. This is robust against changes to order and (to an extent) corrections to the text. 
* Outputs as a static site to reduce hosting requirements. 
* Smart concealment and reveal of notes and footnotes.

# Setup

Stringprint is intended to be paired with a folder containg the source materials.

Temporary note: Amazon have removed the download link for kindlegen. You need to find `kindlegen_linux_2.6_i386_v2_9.tar.gz` and put it at `_dependencies/kindlegen_linux_2.6_i386_v2_9.tar.gz` before running setup if you want to generate .mobi files.

That sourcefile will contain a `vagrantfile` that will do the below automatically, but to maintain a seperate stringprint2 folder following the following instructions:

- Configure `stringprint/conf/config.yaml` from config-example.yaml
- For the `storage_dir` put the path to the source documents folder
- `publish_dir` can be configured to point to a local directory if you want to output the site directly rather than as a zip (can be blank otherwise). 
- This can also be extended to connect to multiple source folders (to keep different orgs/project settings seperate). 

# Command line

There is a basic command line tool to manage document commands. 

This can either be run as `script/shell`.

Commands can also be passed as arguments e.g. `script/shell setdoc:document-slug process publish continue` will process and render the document and keep the shell up for future commands.

All comments that can be applied to a single document can be called without arguments and will be applied to currently selected doc. Multiple slugs can be given as arguments to do several docs, or 'all' will iterate through all unloaded docs. So `render all` will render all documents in the current organisation.

Shell commands:

- `listorgs` - lists all registered orgs
- `listdocs` - lists all documents in current org
- `setdoc` - sets a document as the current document (will accept the folder name or the number assigned against it in listdocs)
- `setorg` - sets an org as the current document
- `loadall` - reprocesses all docs in current org (useful for startups)
- `loadunloaded` - loads all unloaded documents (useful when populating new documents)
- `load`/`process` - processes document ready for preview. 
- `convertword` - creates document.md from (assumed to be) the only docx document in the document folder and separates tables and images into assets folder. Optional ‘demote’ keyword will lower all header - levels (string print assumes section headers are H2). 
- `mergepdf` - merges cover.pdf and contents.pdf (ignoring front page) into a single pdf for upload. 
- `pdfpng` - creates an image version of cover.pdf and a thumbnail version for upload. 
- `render` - renders the document out to the render folder location (if the org publish_dir setting is not configured, defaults to `'_publish` in the source directory).
- `renderzip` - renders a zip file back to the document folder. 
- `preprocess` - runs any preprocess scripts configured for the org or document
- `process` - load and processs the source files (includes 'preprocess' steps unless 'no-preprocess' added)
- `publish` - runs any publish scripts configured for the org or document. WIll also renderzip unless 'no-render-zip' is added as an argument. 
  `[command]` - run a defined commaand for that document or org.
- `quit` - exits


# config and structure

An source repositiory is meant to contain all documents being rendered for a single organisation. It expects the following structure. 

- `_conf/settings.yaml` - contains the org level settings and defaults
- `_docs` - contains all documents (in seperate folders) that belong to an organisation. 
- `_static` - optional, allows additional static files or scss files to be added. 
- `_templates` - optional, allows overriding or extending the default stringprint templates


`_conf/settings.yaml` should contain items like the below:

```
name: Climate Assembly UK
slug: cauk
twitter: NetZeroUK
ga_code: 
ga_cookies: false
publish_root: http://127.0.0.1:5000/
icon: images/mysociety_icon.png
include_favicon: false
orglinks:
  Climate Assembly:
    link: https://www.climateassembly.uk/
    order: 0
default_values:
    cite_as: '{{article.authors}}'
    byline: 'by {{article.authors}}'
commands:
	publish: 'python publish.py {{article.slug}}'
```
Several properties are important, for instance, `publish_root` tells a document where it expects to be published, which is important for creating correctly formatted social cards). Others have default values or can be ignored. 

- `twitter` - setting a twitter account here will give access to analytics of uses of a link in twitter. 
- `ga_code` and `ga_cookies` - set the google analytics code and if it 
- `orglinks` - defines links that should be included in the 'org' dropdown in the top right. This can also be done in templating. 
- `icon` - The icon for the 'org' dropdown in the top right. This can also be done in templating. 
- `default_values` configures what are default values for articles, which may either be set values, or constructed from other properties of an article. 

New variables can be arbitrarily entered, and these will be avaliable in the template as `{{article.org.variable_name}}`. 


## Document configuration

A document folder is expected under `_docs`, where the folder name will be the slug. 

The minimum required files are a settings.yaml and a source document, but this folder is also likely to include a header image, processing scripts, pdf versions or additional assets. 

A document settings.yaml may look like this:

```
title: The path to net zero
subtitle: Climate Assembly UK Full report
short_title: Path to net zero
description: Climate Assembly UK will bring together people from all walks to life to discuss how the UK can reduce greenhouse gas emissions to net zero by 2050.
copyright: ''
authors: Climate Assembly UK
file_source: document.md
publish_date: 2018-07-16
multipage: false
display_notes: true
display_footnotes_at_foot: true
pdf: 2020.07.14-CAUK-Report-001.pdf
header:
  location: cover.png
  size: 6
commands:
  preprocess: python convert.py
copy_files:
  - extra_pdf.pdf
```

The following are accepted config options (which may also be specified through the org default values):

- `title` - main title of the document
- `short_title` - Several words for top left of nav bar. 
- `file_source` - source document (typically `document.md`)
- `publish_date` - `yyyy-mm-dd`

Additional details:

- `subtitle` - subtitle for below the title. Optional, if there is a : or ? in the title, text after this will be assumed to be a subtitle.
- `description` - description added to social share. 
- `copyright` - copyright info. 
- `authors`  - credited authors. 
- `cite_as` - used when construction citation (may want to reverse John Smith to Smith, J)
- `byline` - used in main version, but not simpler formats (which use authors). 

Display options:

- `multipage` - default false, true renders each section on a seperate page (
- `display_notes` - if notes/asides are displayed by default.
- `display_footnotes_at_foot` - if the footnotes are displayed at the end of a document, if using named footnotes, may not want to. 
- `display_toc` - display the table of contents when a page loads (default false)

Format options:

- `pdf` - name of a pdf version in the document folder (will be copied into rendered folder)
- `pdf_location` - url of a PDF to link to elsewhere
- `kindle_location` - location of a kindle file elsewhere to replace local link (if for instance, avaliable on Amazon)
- `copy_files` - additional files to be copied from the source folder to the rendered directory/zip.

Image options:

- `book_cover` - portrait image to use as front cover of kindle book (the `pdfpng` shell command will create one from `cover.pdf`)
- `header` - image to use as the main image of the document. The subproperty `size` is a score out of 12 for how much of the screen it should take up. 


## Expected source format

The source file is expected to be markdown or html, with a few differences. 

Encapsulating a paragraph in `[[` `]]` will signal it is a note or an aside, which can be hidden or expanded by default. 

Footnotes follow the extended syntax [here](https://www.markdownguide.org/extended-syntax/#footnotes) where a reference is marked by `[^1]` and the full text is:

`[^1]: This is the text of the footnote.`

To do a named footnote (Harvard style), add the extra words to the reference with a `||` seperator, for instance `[^1||Brown(2018)]. 

Images and tables are expected to be seperated into the `assets` folder of a document and referenced by `[asset:image-asset-1]`.  If using the inbuilt `convertword` function this will be done automatically. 

Using `[header-asset:image-asset-1]` will intergrate with the section-anchor for that section. There can only be one section-anchor per section. 

The source file will accept html and carry through classes to the final version. Elements that will be carried across are: `p`, `ul`,`ol`, `h1`, `h2`, `h3`, `h4`, `h5`, `blockquote`, `table`.

### Assets

Assets like tables, images and charts are stored in the `_docs/doc_slug/assets` folder and referenced in `assets/assets.yaml`.

This is formatted in the following way:

```
- table-asset-1:
    content_type: table
    type: xls
    caption: ''
- image-asset-1:
    content_type: image
    type: png
    caption: ''
```

Accepted assets are 'image', 'table', 'html'. 

Where the filename is expected to be `table-asset-1.xls`, `image-asset-1.png`, etc. 

Image assets are converted into different sizes and different formats for greater speed on different displays and browsers. 

Table assets are rendered as a bootstrap formatted table in the responsive version, and a plain table in the plain text and kindle versions. 

This is generally expected to be generated by a preprocessor rather than manually. 

[Possibly room for a tidy-up function that creates the assets.yml automatically from any files in this directory]

# Deep linking

Deep linking is when it is possible to link deep into a large document, as opposed to just to the document itself. 

In general this is technically easy to do, where each paragraph can be given a numbered ID and an anchor to make external links work. However, this assumes that the document, once created, does not change. 

An online document may want to be updated to contain new information, or to fix typos or add a new opening disclaimer. This would affect the paragraph order and make IDs link to the wrong place. 

In stringprint, for each paragraph (or top level html element like lists), there is a unique ID and link. The link is made up of a relative position and a set of keys made up from the content of a paragraph. 

The link generated is to a seperate html file that redirects the relevant anchor in the main document. This is to enable a social preview of the link that differs for each paragraph on a static site. 

Whenever the document is processed, the new paragraphs are compared against `_paragraphs.yaml`, which contains all previously rendered paragraph ids. Where old paragraphs no longer exist, they are linked to their most appropriate current replacement.

When a document is rendered, all paragraphs are screenshotted (using an optional `screenshot.scss` stylesheet) so these images can be used as social previews. All old paragraph ids are rendered with the details of their modern replacements. 

While there is some javascript processing of the keys to find the best match, this is relatively redundant under this approach and links will be matched correctly without javascript on. 

# Commands

Both org and doc config files can specify additional commands that transform the input or the output.

The anticipated (but not required) commands are `preprocess` and `publish`. Any additional commands configured can be run in the same way on the shell. 

This is assuming that documents will be passed from outside sources and need additional work to be acceptable to stringprint, and automating the process speeds up the work of revisions. Similarly, it assumes any automatable publication processs differs by org, and should not be in the core. 

An org-level defined command will apply to all docs in that org, but one defined in a document will only apply to that document. 

The default working directory for an org level command is the top level of the source repository, while for the doc-level it is the document folder. Similar to default values, these can use template language to access properties of the article or org - for instance: `python publish.py {{article.slug}}`.

# Templating and formatting

An org directory can contain optional `_static` and `_templates` folders.

In relative terms static files in the `_static` directory will be located in `/static/orgs/ORG_SLUG/` if new files need to be referenced in templates or css. For example, a `_static/images/demo.jpg` will be reference `{% static 'orgs/ORG_SLUG/images/demo.jpg' %}`.

## SASS

Stringprint will prefer sass files and templates in these directories when rendering documents from that org. 

The current sass styling can be found in `stringprint2/web/scss` - `main.scss` contains instructions on overriding or adding things to the format. 

There is additional `screenshot.scss` that removes some elements of the UI to take nicer screenshots of paragraphs. 

There is an optional dark mode (currently not included) in `scss/stringprint/._darkmode.scss`.

## Django templates

Creating an `_templates/ink/article_main.html` will let you override aspects of the main page template:

For instance, the following adjusts the google fonts used and adds a new footer to the page. 

```
{% extends 'ink/article_main.html' %}

{% block fonts %}
	<link rel="preconnect" href="https://fonts.gstatic.com/" crossorigin>
    <link href='https://fonts.googleapis.com/css?family=PT+Sans:400,700|PT+Serif:400,700&amp;display=swap' rel='stylesheet' type='text/css'>
{% endblock %}

{% block footer %}
	<p>This is a custom footer </p>
{% endblock %}

```

Configured empty blocks are:

- `extra_head` - any extra settings/styles for the head of the page. 
- `footer` - at bottom of body. 
- `org_links` - configure org_links in template.
- `mobile_org_links` - configure org_links in template (mobile menu).
- `extra_js` - link to extra javscript file to be included in the compile. 
- `code` - add new JS code at the bottom of the page. 

Populated blocks (where you'll need to consult the original templates to adjust the contents) are:

- `fonts` - define google fonts
- `title` - Page title
- `subtitle` - Page subtitle
- `byline` - Author byline
- `other_formats` - links to the alternate formats of the documents
- `nav_buttons` - change the search, TOC and download buttons
- `nav` - replace the entire nav block
- `facebook` - replace the social sharing settings. 
- `previous_section` - replace link to previous section (if multipage)
- `next_section` - replace link to next section (if multipage)

