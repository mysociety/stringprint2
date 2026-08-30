'''

FlexiModel tidies up adding up methods to models and querysets.

'''

import six
from django.db import models
from django.db.models.base import ModelBase


class CustomRootManager(models.Manager):

    use_for_related_fields = True

    def get_or_none(self, *args, **kwargs):
        try:
            x = self.get(*args, **kwargs)
        except self.model.DoesNotExist:
            x = None
        return x


def allow_floating_methods(cls):
    """
    Decorator for models that allows functions to be transposed to querysets and managers
    can decorate models directly - or make a subclass of FlexiModel.

    """
    class CustomQuerySet(models.QuerySet):
        pass

    """
    Move flagged queryset methods to queryset
    """
    for i in cls.__dict__.keys():
        method = cls.__dict__[i]
        if hasattr(method, "_querysetmethod"):
            setattr(CustomQuerySet, i, method)

    class CustomManager(CustomRootManager):

        def get_queryset(self):
            return CustomQuerySet(self.model, using=self._db)

    """
    Move flagged manager methods to manager
    """
    for i in cls.__dict__.keys():
        method = cls.__dict__[i]
        if hasattr(method, "_managermethod"):
            setattr(CustomManager, i, method)

    cls.add_to_class('objects', CustomManager())
    try:
        cls._default_manager = cls.objects
    except AttributeError:
        pass # django 1.11 doesn't need this.
    
    
    return cls


class ApplyManagerMethodMeta(ModelBase):
    """
    Customise the metaclass to apply a decorator that allows custom manager
    and queryset methods
    """
    def __new__(cls, name, parents, dct):
        """
        only apply decorator to non abstract models
        """
        is_abstract = False
        try:
            if hasattr(dct['Meta'],"abstract"):
                if dct['Meta'].abstract:
                    is_abstract = True
        except KeyError:
            pass

        cls = super(ApplyManagerMethodMeta, cls).__new__(
            cls, name, parents, dct)
        if is_abstract:
            return cls
        else:
            return allow_floating_methods(cls)


class FlexiModel(six.with_metaclass(ApplyManagerMethodMeta, models.Model)):
    """
    Class for models to inherit to receive correct metaclass that allows the floating decorators

    use instead of models.Model
    """

    class Meta:
        abstract = True


def querysetmethod(func):
    """
    Decorator for a model method to make it apply to the queryset.

    Will be accessible as model.objects.all().foo()

    "self" will then be the query object.

    """
    func._querysetmethod = True
    return func


def managermethod(func):
    """
    Decorator for a model method to make it a manager method instead.

    will be accessible as model.objects.foo()

    "self" will then be the manager object.

    self.model - can then be used to access model.
    self.get_queryset() - to get access to a query

    """

    func._managermethod = True
    return func
