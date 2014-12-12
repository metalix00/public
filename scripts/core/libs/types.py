try:
    from collections import OrderedDict as od
except:
    from core.lib.python26_types import OrderedDict as od

OrderedDict = od

def asList(items, skipNoneType=False):
    """
    Usage:
        asList(list items)
    Description:
        returns a list from the input
    In:
        [type] items
    """
    results = []
    if isinstance(items, list) or issubclass(type(items), list) or \
            isinstance(items, tuple) or issubclass(type(items), tuple):
        results = list(items)

    elif isinstance(items, dict) or issubclass(type(items), dict):
        results = [value for variable, value in items.items()]

    elif 'collection' in type(items).__name__:
        try:
            results = list(items)

        except:
            pass

    else:
        results = [items]

    if skipNoneType:
        return [item for item in results if item is not None]

    else:
        return results

    return [items]


def asInt(value):
    """
    Converts the value to an integer
    """
    return int(asFloat(value))


def asFloat(value):
    """
    Converts the value to a float
    """
    if str(value).lower() == 'false':
        return 0.0

    elif str(value).lower() == 'true':
        return 1.0

    elif str(value).lower() == 'none':
        return 0.0

    try:
        value = float(value)
        return value

    except:
        return 0.0



def fi(items):
    """
    Usage:
        fi(list items)
    Description:
        returns the first item in a list
    In:
        [list] items
    """
    items = asList(items)

    if len(items) == 0:
        return None
    return items[0]


def li(items):
    """
    Usage:
        li(list items)
    Description:
        returns the last item in a list
    In:
        [list] items
    """
    items = asList(items)

    if len(items) == 0:
        return None
    return items[-1]


def isType(item, types, subclass=True):
    """
    Description:
        returns True if the item matches the specified types
    In:
        [item] item
        [list] types
        [bool] subclass, if False will use isinstance instead of issubclass
    """
    types = asList(types)
    if dict in types and od not in types:
        types.append(od)

    for t in types:
        if subclass and issubclass(type(item), t):
            return True

        elif isinstance(item, t):
            return True

    return False


class ExtendedDict(dict):
    marker = object()
    def __init__(self, value=None):
        if value is None:
            pass
        elif isinstance(value, dict):
            for key in value:
                self.__setitem__(key, value[key])
        else:
            pass

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, ExtendedDict):
            value = ExtendedDict(value)
        dict.__setitem__(self, key, value)

    def __getitem__(self, key):
        found = self.get(key, ExtendedDict.marker)
        if found is ExtendedDict.marker:
            found = ExtendedDict()
            dict.__setitem__(self, key, found)
        return found

    __setattr__ = __setitem__
    __getattr__ = __getitem__


def parseArgs(*args, **kwargs):
    for arg in args:
        if arg is None:
            continue

        return arg

    if kwargs and "default" in kwargs.keys():
        return kwargs.get("default")

    return None
