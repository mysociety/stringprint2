'''
View for managing social properties of view
'''

from django.template import Template, Context
from django.conf import settings

class SocialView(object):
    """
    Uses class properties for social arguments
    Allows inheritance. 
    Template language can be used
    e.g.
    
    share_title = "{{title}}"
    
    Where a view has a 'title' variable. 
    
    """
    share_image = ""
    share_site_name = ""
    share_image_alt = ""
    share_description = ""
    share_title = ""
    share_twitter = ""
    share_url = ""
    twitter_share_image = ""
    share_image_alt = ""
    page_title = ""

    def extra_params(self,context):
        params = super(SocialView,self).extra_params(context)
        if hasattr(settings,"SITE_ROOT"):
            params["SITE_ROOT"] = settings.SITE_ROOT
        extra = {"social_settings":self.social_settings(params),
                 "page_title":self._page_title(params)}
        params.update(extra)
        return params
    
    def _page_title(self,context):
            c_context = Context(context)
            return Template(self.__class__.page_title).render(c_context)
    
    def social_settings(self,context):
        """
        run class social settings against template
        """
        cls = self.__class__
        
        c_context = Context(context)
        
        process = lambda x: Template(x).render(c_context)
            
        if cls.twitter_share_image:
            twitter_img = cls.twitter_share_image
        else:
            twitter_img = cls.share_image
            
        di = {'share_site_name':process(cls.share_site_name),
              'share_image':process(cls.share_image),
              'twitter_share_image':process(twitter_img),
              'share_image_alt':process(cls.share_image_alt),
              'share_description':process(cls.share_description),
              'share_title':process(cls.share_title),
              'url':process(cls.share_url),
              'share_image_alt':process(cls.share_image_alt),
              }
        
        return di
    