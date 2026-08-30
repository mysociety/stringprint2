from .mixins import *
from .flexi import *

class FlexiBulkModel(FlexiModel,EasyBulkModel,StockModelHelpers):
    
    class Meta:
        abstract = True
