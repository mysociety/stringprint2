from .functional import *
from .bake import *
from .url import *
from .social import *
from .exceptions import *

class LogicalURLView(BakeView,IntegratedURLView):
    """
    Contains baking, logical structure, and integrated URl
    """
    pass

class LogicalSocialView(LogicalURLView,SocialView):
    """
    Contains baking, logical structure, and integrated URl and social mix-in
    """
    pass

class ComboView(LogicalSocialView):
    """
    Backwards compatible LogicalSocialView
    """
    pass