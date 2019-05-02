# -*- coding: utf-8 -*-
import re
import codecs

if __name__ == "__main__":

    final = []

    with codecs.open("E:\\Users\\Alex\\Dropbox\\letting\\combined.md", encoding='utf-8') as f:
        raw = f.read()
    
    
    
    """ extract all footnotes"""
    for line in raw.split("\n"):
        #print line
        num = 1
        footnotes = []
        for q in re.findall('\(\((.*)\)\)', line): #inside ((footnote))
            footnotes.append("^{0}: {1}".format(num,q))
            q = "(({0}))".format(q)
            line = line.replace(q,"^{0}".format(num))
            num += 1
            
        final.append(line)
        if footnotes:
            final.append("\n\n")
            final.extend(footnotes)
            final.append("\n")        
    with codecs.open("E:\\Users\\Alex\\Dropbox\\letting\\combined-newfn.md", "wb", encoding='utf-8') as f:
        for l in final:
            print(l)
            f.write(l)
            
        
            