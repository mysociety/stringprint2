
from django.template.loader import get_template


def use_template(template):
    """
    Decorator to return a HTTPResponse from a function that just returns a dictionary.
    
    Functions should return a dictionary.
    
    Usage: @use_template(template_location)
        
    """
    def outer(func):  
        def inner(request,*args,**kwargs):
            temp = get_template(template)
            context = func(request,*args,**kwargs)
            return temp.render(context=context,
                               request=request)
        return inner
    return outer
