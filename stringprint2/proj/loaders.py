"""
Extention to filesystem loader that allows
template directories to have namespaces
"""
from django.template.loaders.filesystem import (
    Loader,
    safe_join,
    SuspiciousFileOperation,
    Origin,
)


class NamespaceAwareLoader(Loader):
    def raw_dirs(self):
        """
        The dirs this loader was configured with - settings.py passes it
        ORG_TEMPLATE_DIRS, a list of (namespace, path) tuples, as its own
        `dirs` via the (loader_path, dirs) OPTIONS["loaders"] form. That's
        a different contract from get_dirs() below.
        """
        return self.dirs if self.dirs is not None else self.engine.dirs

    def get_dirs(self):
        """
        Overrides the base Loader.get_dirs(), which callers outside this
        class - django.template.autoreload.get_template_directories(),
        used by the dev server's autoreload watcher, for one - expect to
        return plain paths. Unpack any (namespace, path) tuples down to
        just the path; namespace_aware_dirs() below is what keeps the
        namespace for get_template_sources()'s own use.
        """
        for d in self.raw_dirs():
            yield d[1] if isinstance(d, tuple) else d

    def namespace_aware_dirs(self):
        for d in self.raw_dirs():
            if isinstance(d, tuple):
                namespace, template_dir = d
            else:
                namespace = None
                template_dir = d
            yield namespace, template_dir

    def get_template_sources(self, template_name):
        """
        Return an Origin object pointing to an absolute path in each directory
        in template_dirs. For security reasons, if a path doesn't lie inside
        one of the template_dirs it is excluded from the result set.

        Adjusts template_name if referring to a namespace aware folder

        """
        for namespace, template_dir in self.namespace_aware_dirs():
            adjusted_template_name = template_name
            if namespace:
                if namespace.lower() == template_name[: len(namespace)].lower():
                    adjusted_template_name = template_name[len(namespace) + 1 :]
                else:
                    adjusted_template_name = namespace + adjusted_template_name
            try:
                name = safe_join(template_dir, adjusted_template_name)
            except SuspiciousFileOperation:
                # The joined path was located outside of this template_dir
                # (it might be inside another one, so this isn't fatal).
                continue
            yield Origin(
                name=name,
                template_name=adjusted_template_name,
                loader=self,
            )
