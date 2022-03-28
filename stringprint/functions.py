from jsmin import jsmin
from csscompressor import compress as css_compress
from django.conf import settings
import os


def compress_static(additional=[]):
    """
    compress selected static files
    """
    files = [
        "js//agietan.js",
        "css//stringprint-core.css",
        "css//stringprint-default.css" "js//clipboard.js",
    ]

    static_dirs = settings.STATICFILES_DIRS

    files.extend(additional)
    for s in static_dirs:
        for f in files:
            path = os.path.join(s, f)
            if os.path.exists(path) is False:
                continue
            print("compressing {0}".format(f))
            head, tail = os.path.splitext(f)
            new_name = "{0}.min{1}".format(head, tail)
            with open(os.path.join(s, f)) as js_file:
                if tail == ".js":
                    minified = jsmin(js_file.read(), quote_chars="'\"`")
                elif tail == ".css":
                    minified = css_compress(js_file.read())
            new_path = os.path.join(s, new_name)
            with open(new_path, "w") as js_file:
                js_file.write(minified)
