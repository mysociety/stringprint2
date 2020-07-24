'''
Extention to filesystem loader that allows
template directories to have namespaces
'''
from django.template.loaders.filesystem import (
    Loader, safe_join, SuspiciousFileOperation, Origin)


class NamespaceAwareLoader(Loader):

    def namespace_aware_dirs(self):
        dirs = self.get_dirs()
        for d in dirs:
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
                if namespace.lower() == template_name[:len(namespace)].lower():
                    adjusted_template_name = template_name[len(namespace) + 1:]
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
