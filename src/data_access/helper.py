import functools
import toolz


def many2many_to_dictOfList(relation_pairs, keep_set=False):
    mapping = {}
    for k, v in relation_pairs:
        mapping.setdefault(k, set()).add(v)
    if keep_set:
        return mapping
    else:
        return toolz.valmap(list, mapping)


def many2manyLists_to_dictOfList(relation_pairs, keep_set=False):
    mapping = {}
    for k, v in relation_pairs:
        mapping.setdefault(k, set()).update(v)
    if keep_set:
        return mapping
    else:
        return toolz.valmap(list, mapping)


def image_of_dict(dom, dic):
    dom_in_dic = set(dic.keys()).intersection(dom)
    return set(dic[k] for k in dom_in_dic)


def image_of_dictOfLists(dom, dic):
    return functools.reduce(lambda img, x: img.union(dic.get(x, [])), dom, set())
