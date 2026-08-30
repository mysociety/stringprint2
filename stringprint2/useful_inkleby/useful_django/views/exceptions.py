'''
Created on Aug 21, 2016

@author: Alex
'''
class RedirectException(Exception):
    """
    lets you raise a redirect from anywhere in the structure rather than
    requiring returns to always prioritise it
    """
    pass