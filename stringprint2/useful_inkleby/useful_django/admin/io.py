'''
Helper decorators for working with django_import_export.

Fixes issue with pre-20th c dates until there's a fix in main import_export

'''
from django.contrib import admin
try:
    from import_export import resources
except:
    import_export = None

from django.utils import datetime_safe
from import_export import widgets
import functools


class PastSafeDateTimeWidget(widgets.DateTimeWidget):
    
    def render(self, value):
        if not value:
            return ""
        try:
            return value.strftime(self.formats[0])
        except:
            return datetime_safe.new_date(value).strftime(self.formats[0])
        


class PastSafeModelResource(resources.ModelResource):
    """
   Minor tweak to fix pre 1900 date issue
    """

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        """
        Returns the widget that would likely be associated with each
        Django type.
        """
        
        
        
        result = default
        internal_type = f.get_internal_type()
        if internal_type in ('ManyToManyField', ):
            result = functools.partial(widgets.ManyToManyWidget,
                    model=f.rel.to)
        if internal_type in ('ForeignKey', 'OneToOneField', ):
            #django 2.0 patch
            f_rel = f.rel.to if hasattr(f, 'rel') else f.remote_field.related_model
            result = functools.partial(widgets.ForeignKeyWidget,
                    model=f_rel)
        if internal_type in ('DecimalField', ):
            result = widgets.DecimalWidget
        if internal_type in ('DateTimeField', ):
            result = PastSafeDateTimeWidget
        elif internal_type in ('DateField', ):
            result = widgets.DateWidget
        elif internal_type in ('IntegerField', 'PositiveIntegerField', 'BigIntegerField',
                'PositiveSmallIntegerField', 'SmallIntegerField', 'AutoField'):
            result = widgets.IntegerWidget
        elif internal_type in ('BooleanField', 'NullBooleanField'):
            result = widgets.BooleanWidget
        return result

def construct_model_resource(passed_model):

    class LocalResource(PastSafeModelResource):
    
        class Meta:
            model = passed_model
            
    return LocalResource

def io_admin_register(passed_model):
    """
    filter that registers ImportExportModelAdmin and
    assigns them a blank model_resource
    """
    model_resource = construct_model_resource(passed_model)
    
    def inner(admin_cls):
        
        class ModelAdmin(admin_cls):
            resource_class = model_resource
    
        admin.site.register(passed_model,ModelAdmin)
        return ModelAdmin

    return inner
