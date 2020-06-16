'''
Created on Aug 1, 2016

@author: Alex
'''
import inspect
from copy import deepcopy

from useful_inkleby.useful_django.serialisers import SerialBase, BasicSerial
def add_quotes(value):
    try:
        i = int(value)
    except ValueError:
        i = None
    if i == None:
        return '"{0}"'.format(value)
    else:
        return value

class Choice(SerialBase):
    """
    sets the options avaliable and a description of them
    """
    def __init__(self,choice="",description=""):
        self.choice = choice
        self.description = description

    def print_self(self,spaces=""):
        """
        used by the interpreter to return the code that will produce this object
        """

        settings = ["choice","description"]
        options = []
        for s in settings:
            v = getattr(self,s)
            options.append("{1}".format(s,add_quotes(v)))
        
        t =  "Choice({0})".format(",".join(options))

            
        return t

class Option(SerialBase):
    """
    An option object represents the property being assigned to the google chart
    """
    def __init__(self,type="string",default="",description="",choices=[],value=""):
        self.name = "" #set when OptionObject inits
        self.type = type
        self.default= default
        self.description = description
        self.choices = list(choices)
        self.choice_values = [x.choice for x in self.choices]
        if value:
            self.value = value
        else:
            self.value = self.default
            
    def print_self(self):
        """
        used by the interpreter to return the code that will produce this object
        """
        
             
        settings = ["type","default","description","choices"]
        options = []
        
        spaces_len = len("{0} = Option(".format(self.name))
        spaces = "".join([" " for x in range(0,spaces_len)])
        choice_spaces = "".join([" " for x in range(0,spaces_len + len("choices = ("))])
        
        for s in settings:
            v = getattr(self,s)
            if v:
                if s == "choices":
                    choices = [x.print_self(spaces=choice_spaces) for x in v]
                    v = "(" + (",\r\n"+choice_spaces).join(choices) + ",)"
                else:
                    v = add_quotes(v)

                options.append("{0} = {1}".format(s,v))
        

        
        return "{0} = Option({1})".format(self.name,(",\r\n"+spaces).join(options))
            
    def get_value(self):
        if self.value == self.default:
            return None
        else:
            return self.value
    
    def set_value(self,value):
        if self.choices:
            if value in self.choice_values:
                self.value = value
            else:
                raise ValueError("{0} is not one of avaliable choices for {1}".format(value,
                                                                                      self.name))
        else:
            self.value = value
            
    def __repr__(self):
        return "[{0}: {1}]".format(self.name,self.value)
        
    

class OptionObject(SerialBase):
    """
    Controls all the options for an object. 
    
    a dictionary is returned from get_options.
    
    set shortcut if setting the value of the tiered option is supposed to affect a 
    sub-option
    
    e.g. .backgroundColor changes .backgroundColor.fill
    
    """
    shortcut = "" 
    
    
    def get_options(self):
        """
        returns a dictionary of all values that differ from the default
        """
        options = {}
        
        for p in self.properties:
            v = getattr(self,p).get_value()
            if v:
                options[p] = v
                
        for t in self.tiered:
            t_v = getattr(self,t).get_options()
            if t_v:
                options[t] = t_v
                
        return options
    
    to_json = get_options #json will extract only the changes needed
    
    def from_json(self,values):
        self.__init__() #hasn't been called because of seraliser
        self.inject_options(values)
        
    def inject_options(self,options):
        """
        set the object based on being fed a set of options
        """
        for name,value in options.items():
            if isinstance(value,dict):
                relevant = getattr(self,name)
                relevant.inject_options(value)
            else:
                setattr(self,name,value)

    def _set_shortcut(self,value):
        """
        if this object has a shortcut to a sub-value - set it
        """
        if self.shortcut:
            obj = getattr(self,self.shortcut)
            obj.set_value(value)
    
    def __setattr__(self,name,value):
        """
        modify setattr so that trying to set an attribute modified it's value option
        """
        if hasattr(self,name):
            obj = getattr(self,name)
            if isinstance(obj,Option):
                obj.set_value(value)
            elif isinstance(obj,OptionObject) and obj.shortcut:
                obj._set_shortcut(value)
            else:
                super(OptionObject,self).__setattr__(name,value)
        else:
            super(OptionObject,self).__setattr__(name,value)
    
    def __init__(self):
        """
        ititalise any subvalues and copy options from the class
        """
        self.properties = []
        self.tiered = []
        
        for item, obj in self.__class__.__dict__.items():
            
            """
            copy option objects locally
            """
            if isinstance(obj,Option):
                nobj = deepcopy(obj)
                nobj.name = item
                super(OptionObject,self).__setattr__(item,nobj)
                self.properties.append(item)
            """
            initalise tiered options
            """
            if inspect.isclass(obj) and issubclass(obj,OptionObject):
                nobj = obj()
                nobj.name = item
                super(OptionObject,self).__setattr__(item,nobj)
                self.tiered.append(item)
                
            
        

    
    