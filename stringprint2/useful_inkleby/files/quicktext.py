# -*- coding: utf-8 -*-
'''
Created on Jul 25, 2016

@author: Alex
'''
import codecs
try:
    from decorators import use_self_property
except:
    from useful_inkleby.decorators import use_self_property
import six

if six.PY2:
    unicodetype = unicode
else:
    unicodetype = str

class QuickText(object):
    """
    quick helper object to save as unicode text
    """
    
    def __init__(self,text="",filename=""):
        self.text = text
        self.filename = filename
        if self.filename:
            self.open()

    @use_self_property("filename")
    def save(self,f_name=""):
        if f_name == "":
            raise ValueError("No filename given")
        with codecs.open(f_name, "wb", encoding='utf-8') as f:
            f.write(self.text)

    @use_self_property("filename")
    def open(self,f_name=""):
        if f_name == "":
            raise ValueError("No filename given")
        with codecs.open(f_name, encoding='utf-8') as f:
            self.text = f.read()
            self.filename = f_name
        return self
    
    def conform_quotes(self):
        self.text = self.text.replace(u"“",'"')
        self.text = self.text.replace(u"”",'"')
        self.text = self.text.replace(u"’","'")
        self.text = self.text.replace(u"’","'")
        self.text = self.text.replace(u"‘","'")
        
        self.text = self.text.replace(u"\u2002"," ")
        
    def from_list(self,ls,delimiter="\r\n"):
        """
        given a list - merge it
        """
        self.text = delimiter.join(ls)
        return self
    
    def lines(self,delimiter="\n"):
        """
        iterate though all lines in the file
        can amend with .update method 
        """
        final = []
        has_changed = False
        
        class UnicodeLine(unicodetype):
            """
            basic subclass to allow you to update values back through the loop
            """
            def update(self,value):
                self.new_value = value
                
            def get_update(self):
                if hasattr(self,"new_value"):
                    return True, self.new_value
                else:
                    return False, self    
        
        lines = self.text.split(delimiter)
        lines = [UnicodeLine(l) for l in lines]
        
        for n, ul in enumerate(lines):
            if n != len(lines)-1:
                ul.future = lines[n+1]
            else:
                ul.future = None
            yield ul
            changed, nl = ul.get_update()
            if changed:
                has_changed = True
            if nl != None:
                final.append(nl)
        
        if has_changed:
            self.text = delimiter.join(final)
            
    __iter__ = lines
            