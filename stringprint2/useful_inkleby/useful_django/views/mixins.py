
import codecs
import re
import string
from markdown import markdown

from django.utils.safestring import mark_safe

bracket_extract = re.compile(r"<.*?>(.*?)<\/.*?>")

class MarkDownView(object):
    """
    allows for a basic view where a markdown files is read in and rendered
    
    Give the class a markdown_loc variable which is the filepath to the markdown files.
    
    use self.get_markdown() to retrieve markdown text. If using clean, it is avaliable as 
    'markdown' in the template.
    
    """
    markdown_loc = ""
    
    def get_markdown(self):
        f = codecs.open(self.__class__.markdown_loc, "rb", "cp1252")
        txt = f.read()
        md = markdown(txt, extensions=['markdown.extensions.tables'])
        
        lines = md.split("\n")
        final = []
        for l in lines:
            if l[:2].lower() == "<h":
                contents = bracket_extract.search(l).groups()[0]
                contents = contents.replace(" ","-").lower()
                contents = u"".join([x for x in contents if x in string.ascii_lowercase + "-"])
                final.append('<a name="{0}"></a>'.format(contents))
            final.append(l)
        md = "\n".join(final)
        md = mark_safe(md)
        
        return md
    
    def view(self,request):
        return {"markdown":self.get_markdown()}
    
    
