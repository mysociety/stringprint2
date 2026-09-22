# Opening Section

An ordinary opening paragraph of the kitchen sink document.[^1]

## A Titled Paragraph

This paragraph carries the h2 above it as its title.

### A Third Level Title
#### A Fourth Level Straight After

Two headings in a row, which forces a title-only paragraph to be emitted.

An unordered list follows:

*   first list item
*   second list item

And an ordered list:

1.  first numbered item
2.  second numbered item

> Two quote blocks separated only by a blank line.

> Markdown merges these into a single blockquote element.

A plain paragraph closing the merged block quote.

> The first of two genuinely adjacent blockquotes.

<!-- -->

> The second of two genuinely adjacent blockquotes.

A plain paragraph closing the adjacent block quote run.

# Assets and Markers

Inline image asset here.

[asset:image-one]

A second image asset.

[asset:image-two]

A table asset built from a spreadsheet.

[asset:table-one]

A table with no header row.

[asset:table-no-header-one]

A raw html asset.

[asset:html-one]

A reference to an asset that does not exist.

[asset:does-not-exist]

[header-asset:image-two]

This paragraph is tagged.[tag:mytag]

This paragraph has a named paragraph marker.[para:mypara]

This paragraph carries a printed page marker[page:12] mid-sentence.

[catchup: A short catchup line for readers arriving mid-document.]

A paragraph containing ""a double quoted span"" in the middle of it.

A paragraph with a literal html attribute <span data-empty="">carrying an empty value</span> inline.

A paragraph with smart quotes: “curly double” and ’curly single’ characters.

A link to [the opening section](#opening-section) elsewhere in the document.

A raw html table follows.

<table>
<tr><th>Heading A</th><th>Heading B</th></tr>
<tr><td>Cell one</td><td>Cell two</td></tr>
</table>

# Notes and Asides

[[A single paragraph aside, complete in itself.]]

Text before a multi paragraph aside.

[[
__A multi paragraph aside__

The middle paragraph of the aside.

The closing paragraph of the aside.
]]

An aside whose closing marker trails the final line.

[[
An aside closed on the same line as its text.]]

A paragraph before a lone opening marker.

[[

An aside opened by a marker on its own line.

]]

# Footnotes

A paragraph with a numbered footnote reference.[^2]

A paragraph with a starred footnote reference.[^*]

A paragraph with a named footnote reference.[^scotedit]

A paragraph with a footnote that carries its own label.[^3]

# Duplicate Headings

## Repeated Heading

The first paragraph under a repeated heading.

## Repeated Heading

The second paragraph under a repeated heading, which forces anchor dedupe.

## Repeated Heading

The third paragraph under a repeated heading.

[^1]: The first footnote, attached to the opening paragraph.
[^2]: The second footnote, which contains [a link](https://example.invalid/one).
[^*]: A footnote referenced by a star rather than a number.
[^scotedit]: A footnote referenced by name.
[^3]: Labelled Footnote||The content of a footnote that carries its own label.
