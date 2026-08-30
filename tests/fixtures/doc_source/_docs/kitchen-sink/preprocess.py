"""
Preprocess for the kitchen-sink fixture.

Deliberately does no downloading or conversion - the fixture ships its own
document.md. It exists so that run_command's module:: loader is exercised.
"""

from __future__ import annotations


class Preprocess:
    ran_for: list = []

    def __init__(self, article):
        self.article = article

    def __call__(self) -> None:
        type(self).ran_for.append(self.article.slug)
