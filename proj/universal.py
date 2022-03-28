from django.conf import settings  # import the settings file


def universal_context(request):
    """
    returns helpful universal context to the views
    """

    return {
        "debug": settings.DEBUG,
        "IS_LIVE": settings.IS_LIVE,
        "GA_CODE": settings.GA_CODE,
        "request": request,
        "current_path": settings.SITE_ROOT + request.get_full_path(),
        "SITE_NAME": settings.SITE_NAME,
        "SHARE_IMAGE": settings.SHARE_IMAGE,
        "SITE_ROOT": settings.SITE_ROOT,
    }
