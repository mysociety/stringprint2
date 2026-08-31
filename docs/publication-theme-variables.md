# Publication theme variables

Organisation publication themes may set the variables below before importing `stringprint/main`. These variables are owned by Stringprint and are the supported customisation API; themes should not override Bootstrap variables directly.

## Colours

| Variable | Purpose |
| --- | --- |
| `$stringprint-page-background` | Background outside the report content. |
| `$stringprint-content-background` | Background of report containers and content rows. |
| `$stringprint-content-color` | Default report text colour. |
| `$stringprint-link-color` | Default link colour. |
| `$stringprint-blockquote-background` | Blockquote background. |
| `$stringprint-blockquote-border` | Blockquote accent border. |
| `$stringprint-footnote-border` | Footnote container border. |
| `$stringprint-aside-border` | Extended/aside container border. |
| `$stringprint-divider-color` | Heading divider colour. |
| `$stringprint-highlight-background` | Highlighted paragraph background. |
| `$stringprint-navbar-color` | Navbar text and icon colour. |
| `$stringprint-navbar-background` | Navbar background and primary accent. |
| `$stringprint-navbar-border` | Navbar lower border. |
| `$stringprint-navbar-icon-color` | Header action-icon colour. |
| `$stringprint-navbar-active-color` | Active navigation text colour. |
| `$stringprint-navbar-active-background` | Active navigation background. |
| `$stringprint-table-heading-background` | Table heading background. |
| `$stringprint-table-heading-color` | Table heading text colour. |

## Typography and width

| Variable | Purpose |
| --- | --- |
| `$stringprint-body-font` | Publication body font stack. |
| `$stringprint-heading-font` | Heading font stack available to organisation themes. |
| `$stringprint-container-sm` | Container width from the small breakpoint. |
| `$stringprint-container-md` | Container width from the medium breakpoint. |
| `$stringprint-container-lg` | Container width from the large breakpoint. |
| `$stringprint-print-min-width` | Minimum body/container width used for print layout. |

## Compatibility

Existing variables such as `$page-background-color`, `$content-background-color`, `$navbar-accent-color`, `$table-head-bg`, and `$sansfont` remain accepted as compatibility inputs during the Bootstrap 5 migration. New and updated themes should use the `$stringprint-*` API.

The compatibility aliases are inputs only. Stringprint's own component styles consume the documented variables, and Bootstrap-specific aliases are confined to the SCSS integration layer.
