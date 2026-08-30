'''
Basic postcode sanity detector
'''

#postcode formats that are valid in the uk
valid_postcode_formats = [
    "AA9A 9AA",
    "A9A 9AA",
    "A9 9AA",
    "A99 9AA",
    "AA9 9AA",
    "AA99 9AA",
]

valid_postcodes_no_space = [x.replace(" ", "") for x in valid_postcode_formats]
no_space_to_valid = {x.replace(" ", ""): x for x in valid_postcode_formats}


def to_a9(tx):
    '''
    converts a string to it's A9 format
    '''
    def check(t):
        if t.isalpha():
            return "A"
        elif t.isnumeric():
            return "9"
        else:
            return t

    if type(tx) == str:
        txx = unicode(tx, errors="ignore")
    else:
        txx = tx  # force to unicode to use isnumberic function

    return "".join([check(x) for x in txx])


def valid_uk_postcode(postcode):
    return to_a9(postcode) in valid_postcode_formats + valid_postcodes_no_space


def extract_postcode(tx):
    """
    given comma seperated text will extract postcode  

    e.g. 123 fake street, fakedown, FAKEPOSTCODE
    """
    postcodes = []
    for part in tx.split(","):
        if valid_uk_postcode(part.strip()):
            postcodes.append(part.strip().upper())

    return postcodes
