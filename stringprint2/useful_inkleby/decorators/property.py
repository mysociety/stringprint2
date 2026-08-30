
from .base import GenericDecorator

class use_self_property(GenericDecorator):
    """
    for one argument class functions.
    if non-self argument is missing, use a property from self
    
    e.g.
    
    @use_self_property("foo")
    def bar(self,foo):
        print foo
        
    if bar doesn't recieve foo - it will use self.foo
    
    """
    args_map = ["property_to_use"]
    def arg_decorator(self,function,*args,**kwargs):
        
            if len(args) == 1 and len(kwargs) < 1:
                func_self = args[0]
                value = getattr(func_self,self.property_to_use)
                return function(*args+(value,),**kwargs)
            else:
                return function(*args,**kwargs)       