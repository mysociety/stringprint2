'''
Created on Aug 1, 2016

@author: Alex
'''
from BeautifulSoup import BeautifulSoup
from files import QuickText
from .base import Choice,Option
from itertools import groupby

def fix_multi_spaces(v):
    return ' '.join(v.split())

def variable_split(v):
    """
    api documentation varies between using - and : to signify the choice options
    This tries to figure out the format being used
    """
    
    if v[0] == "{":
        v = v.replace("{format: ","")
        v = v.replace("'}",'"')
    
    colon_find = v.find(":")
    dash_find = v.find("-")
    use = ""
    if dash_find == -1:
        use = "colon"
    elif colon_find == -1:
        use = "dash"
    elif dash_find < colon_find:
            use = "dash"
    else:
        use = "colon"
            
    if use == "colon":
        pos = colon_find
    if use == "dash":
        pos = dash_find

    
    
    return v[:pos],v[pos+1:]

def extract_classes(class_name,file_name):

    text = QuickText().open(file_name).text
    
    soup = BeautifulSoup(text)
    
    rows = soup.findAll("tr")
    
    results = []
    
    all_options = []
    #create all option objects on their own
    for row in rows:
        o = Option()
        columns = row.findAll("td")
        o.name = columns[0].text
        if "." in o.name:
            all_options.append("zzzz." + o.name)
            split = o.name.split(".")
            o.name = split[-1]
            o.group = split[-2]
            o.level = len(split)
        else:
            o.group = "zzzz"
            o.level = 1
        
        body = columns[1]
        items = row.findAll({"div":True,
                             "ul":True,
                             "p":True})
        for x,i in enumerate(items):
            if x == 0 and i.name != "ul":
                o.description = i.text.replace("\n","").replace("\r","")
                o.description = fix_multi_spaces(o.description).replace('"',"'")
            elif i.name == "ul":
                for choice in i.findAll('li'):
                    c = Choice()
                    c.choice,c.description = variable_split(choice.text)
                    c.choice = c.choice.replace('"',"")
                    c.description = c.description.strip().replace("\n","").replace("\r","")
                    c.description = fix_multi_spaces(c.description).replace('"',"'")
                    c.choice = c.choice.replace("'","").strip()
                    if " " not in c.choice: #ignore where formatting is bad
                        o.choices.append(c)
            elif "Type:" in i.text:
                o.type = i.text.split(":")[1].strip()
            elif "Default:" in i.text:
                o.default = i.text.split(":")[1].strip().replace("'","")
                if " " in o.default:
                    o.default = None
        results.append(o)
    
    class ClassStorage(object):
        
        def __init__(self):
            self.name = ""
            self.class_label = ""
            self.text = ""
    
    created_storage = []
    depth_sort = lambda x: x.level
    alpha_sort = lambda x: x.group
    results.sort(key=depth_sort,reverse=True)
    for lk,lg in groupby(results,depth_sort):
        ll = [x for x in lg]
        ll.sort(key=alpha_sort)
        for k,g in groupby(results,alpha_sort):
            c = ClassStorage()
            if k == "zzzz":
                c.class_label = class_name
            else:
                c.class_label = k[0].upper() + k[1:] + "Option"
            c.name = k
            
            local_sub_properties = []
            

            for o in all_options:
                o_split = o.split(".")[:-1]
                if k in o_split:
                    loc = o_split.index(k)
                    try:
                        sub = o_split[loc+1]
                        local_sub_properties.append(sub)
                    except IndexError:
                        pass

            valid_children = [x for x in created_storage if x.name in local_sub_properties]
            
            excluded_names = [x.name for x in valid_children]
            
            include_children = ["{0} = {1}".format(x.name,x.class_label) for x in valid_children]
            
            allowed_properties = [x for x in g if x.name not in excluded_names]
            
            txt_options = "\r\n".join(include_children + [x.print_self() for x in allowed_properties])
            
            #adjust line breaks
            txt_options = "\r\n".join(["    " + x for x in txt_options.split("\r\n")])
            
            c.text = "class {0}(OptionObject):".format(c.class_label)
            c.text += "\r\n" + txt_options
            
            if c.name not in [x.name for x in created_storage]:
                created_storage.append(c)
            
    final = "\r\n\r\n".join([x.text for x in created_storage])
    return final
        
f = extract_classes("LineChartOption","E:\\api_test.txt")

e = QuickText()
e.text = f
e.save("E:\\api_results.txt")