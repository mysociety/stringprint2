"""
Extend Django's filesystem loader with template-directory namespaces.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from os import PathLike

from django.core.exceptions import SuspiciousFileOperation
from django.template import Origin
from django.template.loaders.filesystem import Loader, safe_join

TemplateDirectory = str | PathLike[str]
NamespacedTemplateDirectory = tuple[str, TemplateDirectory]


class NamespaceAwareLoader(Loader):
    """
    Load templates from ordinary or namespace-prefixed directories.
    """

    def raw_dirs(
        self,
    ) -> Sequence[TemplateDirectory | NamespacedTemplateDirectory]:
        """
        Return the directories supplied when the loader was configured.

        ``settings.py`` passes ``ORG_TEMPLATE_DIRS`` as ``(namespace, path)``
        pairs through Django's ``(loader_path, dirs)`` loader form. This is a
        different contract from ``get_dirs()``, whose external callers expect
        plain paths.
        """
        return self.dirs if self.dirs is not None else self.engine.dirs

    def get_dirs(self) -> Iterator[TemplateDirectory]:
        """
        Return plain paths for Django's template autoreloader.
        """
        for directory in self.raw_dirs():
            yield directory[1] if isinstance(directory, tuple) else directory

    def namespace_aware_dirs(
        self,
    ) -> Iterator[tuple[str | None, TemplateDirectory]]:
        """
        Return each configured directory together with its optional namespace.
        """
        for directory in self.raw_dirs():
            if isinstance(directory, tuple):
                namespace, template_dir = directory
            else:
                namespace = None
                template_dir = directory
            yield namespace, template_dir

    def get_template_sources(self, template_name: str) -> Iterator[Origin]:
        """
        Yield secure candidate origins for a possibly namespaced template.
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
                continue
            yield Origin(
                name=name,
                template_name=adjusted_template_name,
                loader=self,
            )
