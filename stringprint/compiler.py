"""
Extending CSS compilers and minifers

"""
from static_precompiler.compilers.scss import SCSS
import static_precompiler.utils as utils
import static_precompiler.exceptions as exceptions
import static_precompiler.url_converter as url_converter

from compressor.filters.cssmin import rCSSMinFilter
from rcssmin import cssmin
import os


def svg_safe(input_css, *args, **kwargs):
    """
    does not allow whitespace to be removed where svg is contained
    in the css
    """

    input_css = input_css.replace("/%%static%%", "../..")

    replace_str = "!!TEMPSPACE!!"

    line_safe = []
    for line in input_css.split("\n"):
        if "svg+xml" in line:
            line = line.replace(" ", replace_str)
        line_safe.append(line)
    input_css = "\n".join(line_safe)
    ns = cssmin(input_css, *args, **kwargs)
    ns = ns.replace(replace_str, " ")
    return (ns)


class SVGSafeMinify(rCSSMinFilter):
    callback = 'stringprint.compiler.svg_safe'


class CustomSCSS(SCSS):
    '''
    dart-sass doesn't use the same source map parameter
    this overrides that

    Also adds the autoprefixer post-processsor that
    bootstrap requires 
    '''

    def compile_file(self, source_path):
        full_source_path = self.get_full_source_path(source_path)
        full_output_path = self.get_full_output_path(source_path)
        args = [
            self.executable,
            # "--sourcemap={0}".format("auto" if self.is_sourcemap_enabled else "none"),
            "--no-source-map",
        ] + self.get_extra_args()

        args.extend([
            self.get_full_source_path(source_path),
            full_output_path,
        ])

        full_output_dirname = os.path.dirname(full_output_path)
        if not os.path.exists(full_output_dirname):
            os.makedirs(full_output_dirname)

        # `cwd` is a directory containing `source_path`.
        # Ex: source_path = '1/2/3', full_source_path = '/abc/1/2/3' -> cwd =
        # '/abc'
        cwd = os.path.normpath(os.path.join(
            full_source_path, *([".."] * len(source_path.split("/")))))
        return_code, out, errors = utils.run_command(args, None, cwd=cwd)

        if return_code:
            if os.path.exists(full_output_path):
                os.remove(full_output_path)
            raise exceptions.StaticCompilationError(errors)

        url_converter.convert_urls(full_output_path, source_path)

        if self.is_sourcemap_enabled:
            utils.fix_sourcemap(full_output_path + ".map",
                                source_path, full_output_path)

        # postprocess using autoprefixer
        post_process = ["npx",
                        "postcss",
                        full_output_path,
                        "--use",
                        "autoprefixer",
                        "--replace"]

        return_code, out, errors = utils.run_command(
            post_process, None, cwd=cwd)

        return self.get_output_path(source_path)
