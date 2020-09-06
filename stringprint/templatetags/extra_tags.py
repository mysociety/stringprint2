from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from stringprint.models import Asset
register = template.Library()


@register.filter("range")
def range_f(v):
    if v < 0:
        return range(v, 0)
    else:
        return range(0, v)


@register.filter
def empty_if_none(v):
    if v:
        return v
    else:
        return ""


@register.filter
def blankfix(v):
    if v == None:
        return "-"
    else:
        return v


@register.simple_tag
def active(v1, v2):
    if v1 == v2:
        return mark_safe('class = "active"')
    else:
        return ""


@register.simple_tag
def alert(message):

    if message:
        alert_type = "success"
        if "|" in message:
            alert_type, message = message.split("|")
        alert_type = alert_type.lower().strip()
        template = '<div class="alert alert-{1}" role="alert">{0}</div>'
        return mark_safe(template.format(message, alert_type))
    else:
        return ""


@register.filter
def display_asset(article, asset_id):

    if hasattr(article, "render_basic_assets"):
        basic = True
    else:
        basic = False

    asset = [x for x in article.cached_assets if x.id == asset_id]
    if asset:
        return asset[0].render(basic=basic)
    else:
        return None


@register.filter
def display_header_asset(article, asset_id):

    if hasattr(article, "render_basic_assets"):
        basic = True
    else:
        basic = False

    asset = [x for x in article.cached_assets if x.id == asset_id]
    if asset:
        return asset[0].render(basic=basic, header=True)
    else:
        return None


@register.filter
def display_asset_caption(article, asset_id):
    asset = [x for x in article.cached_assets if x.id == asset_id]
    if asset:
        return asset[0].caption
    else:
        return None


@register.filter
def display_asset_text(article, asset_id):

    asset = [x for x in article.cached_assets if x.id == asset_id]
    if asset:
        return asset[0].render(basic=True, kindle=False)
    else:
        return None


@register.filter
def display_asset_kindle(article, asset_id):

    asset = [x for x in article.cached_assets if x.id == asset_id]
    if asset:
        return asset[0].render(basic=True, kindle=True)
    else:
        return None


@register.filter
def cite_link(article, paragraph):
    return article.cite_link(paragraph)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def divide(value, arg):
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError):
        return None


@register.inclusion_tag('ink//header_image.html')
def header_image(image_obj, alt_text=""):
    return {"image": image_obj, 'alt_text': alt_text}


@register.filter("url")
def url(item, url):
    """
    return link
    """
    return mark_safe('<a href="{1}">{0}</a>'.format(item, url))


@register.filter("int")
def e_int(obj):
    """
    return comma seperated integer from float
    """
    if obj == "":
        obj = 0
    num = int(obj)
    return"{:,}".format(num)


@register.filter
def sub(obj, object2):
    """
    basic substitution
    """
    return obj - object2


@register.filter
def percent(obj, object2):
    """
    return percentage of 1 of 2
    """
    if object2:
        return int(float(int(obj)) / object2 * 100)
    else:
        return 0


@register.filter
def no_float_zeros(v):
    """
    if a float that is equiv to integer - return int instead
    """
    if v % 1 == 0:
        return int(v)
    else:
        return v


@register.filter
def evenchunks(l, n):
    """
    return a list in two even junks
    """
    if type(l) != list:
        l = list(l)

    import math
    n = int(math.floor(len(l) / float(n))) + 10
    print(len(l))
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


@register.filter
def intdistance(d):
    if d == "":
        d = 0
    if d < 1:
        return "{0} m".format(int(d * 1000))
    else:
        return "{0} km".format(int(d))


@register.filter
def yield2(l):
    """
    return a list in two even junks
    """

    l = list(l)

    for x in range(0, len(l), 2):
        try:
            yield [l[x], l[x + 1]]
        except IndexError:
            yield [l[x], None]


@register.filter
def evenquerychunks(l, n):
    """
    return a list in two even junks
    """

    l = list(l)

    import math
    n = int(math.floor(len(l) / float(n))) + 1
    print(len(l))
    """Yield successive n-sized chunks from l."""
    results = []
    for i in range(0, len(l), n):
        results.append(l[i:i + n])

    return results


@register.filter
def chunks(l, n):
    """
    returns a list in set n
    """
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


@register.filter
def clip(st, length):
    """
    will clip down a string to the length specified
    """
    if len(st) > length:
        return st[:length] + "..."
    else:
        return st


@register.filter
def limit(st, length):
    """
    same as clip - but doesn't add ellipses
    """
    return st[:length]


@register.filter
def five(ls):
    """
    returns first five of list
    """
    return ls[:5]


@register.filter
def target_naming(ty, target):
    """
    returns first five of list
    """
    de = ty.description(target)
    de = de[0].upper() + de[1:] + "."
    return de


@register.filter
def human_travel(hours):
    """
    given decimal hours - names it look nice in human
    """
    import math

    m = int((hours % 1) * 60)
    h = int(math.floor(hours))
    if h > 24:
        d = int(math.floor(h / 24))
        h = h % 24
    else:
        d = 0

    st = ""

    if d:
        st += "{0} Day".format(d)
        if d > 1:
            st += "s"
    if h:
        st += " {0} Hour".format(h)
        if h > 1:
            st += "s"
    if m and not d:
        st += " {0} Minute".format(m)
        if m > 1:
            st += "s"
    st = st.strip()
    return st
