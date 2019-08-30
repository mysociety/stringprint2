# Stringprint2

Stringprint is a tool to convert markdown documents into responsive html, plain(ish) html, and kindle. mobi formats. 


## Setup

Stringprint is intended to be paired with a folder containg the source materials.

Configure `conf/config.yaml` from config-example.yaml

- Create keys using URLs provided. 
- For the `storage_dir` put the path to the source documents folder
- `publish_dir` can be configured to point to a local directory if you want to output the site directly rather than as a zip (can be blank otherwise). 
- This can also be extended to connect to multiple source folders (to keep different orgs/project settings seperate). 

## Loading existing document

- ‘vagrant up’ in the stringprint2 directory. 
- If that all goes fine ‘script/shell’ to get to basic interface.
- ‘listdocs’ will show all the docs currently in the source repo
- ‘loadall’ to populate. 
- Navigate to 192.168.0.1:8000 in a browser on host machine to see a preview of these documents (script/server will start a server - debug using ‘python3 manage.py runserver 0.0.0.0:8000’). 

## Creating new document

- Create a new folder in source repo folder (new folder name will be the slug) and copy the settings.yaml from a similar document. 
- Either place a markdown file in the document and reference it in the settings (document.md is the usual name) or, put any word document in that folder.
- (Optionally) put two pdfs in the folder, called cover.pdf and contents.pdf
- `vagrant up` in stringprint2, then open the shell and set the document to this document. 
- `convertword` will convert the word document into a document.md and extract tables and images as assets. Examine and adjust the document.md
- If you have pdf files, `pdfpng` will create an image version of the cover that can be referenced as the kindle book cover in settings.yaml (and creates a thumbnail for upload).
- ‘mergepdf’ will create a pdf to upload.
- If using the mySociety repo site, create a new ResearchItem and upload the pdf as an output now. Reference the url of the output and the slug in the relevant options in settings.yaml. 
- `process` will import and process the document. 
- Running script/server will create a local server: 127.0.0.1:8001 will then allow you to preview the new document. 

## Rendering a document
- Have a local server running (`script/server`) (required for image generation)
- Using the shell, `setdoc` to the document in question. 
- Then `process` regenerates from the source document (optional if already loaded)
- `renderzip` will export a zip file back to the source directory
- This can then be uploaded through the zip archive setting on the repo site. 

## Command line

There is a basic command line tool to manage document commands. 

This can either be run in the vagrant as `Python3 shell.py` or `script/shell`

Commands can also be passed as arguments e.g. `Python3 shell.py setdoc:document-slug process renderzip continue`will process and render the document and keep the shell up for future commands.

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
- `render` - renders the document out to the render folder location (less expected to be used)
- `renderzip` - renders a zip file back to the document folder. 
- `quit` - exits
