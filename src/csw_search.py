from owslib import fes
from owslib.fes import SortBy, SortProperty
from owslib.csw import CatalogueServiceWeb
from geolinks import sniff_link

# CREDITS:
# code derived from:
# https://github.com/ioos/notebooks_demos/blob/master/notebooks/2016-12-19-exploring_csw.ipynb

# code owslib: 
# https://github.com/geopython/OWSLib/tree/master/owslib/catalogue
# https://github.com/geopython/OWSLib/blob/master/tests/test_iso_parsing.py

# doc owslib: https://geopython.github.io/OWSLib/#csw

# schemas:
# http://schemas.opengis.net/csw/2.0.2/record.xsd
# http://schemas.opengis.net/cat/csw/3.0/record.xsd
# https://www.isotc211.org/2005/gmd/

def fes_date_filter(start, stop, constraint="overlaps"):
    """
    Take datetime-like objects and returns a fes filter for date range
    (begin and end inclusive).
    NOTE: Truncates the minutes!!!

    Examples
    --------
    >>> from datetime import datetime, timedelta
    >>> stop = datetime(2010, 1, 1, 12, 30, 59).replace(tzinfo=pytz.utc)
    >>> start = stop - timedelta(days=7)
    >>> begin, end = fes_date_filter(start, stop, constraint='overlaps')
    >>> begin.literal, end.literal
    ('2010-01-01 12:00', '2009-12-25 12:00')
    >>> begin.propertyoperator, end.propertyoperator
    ('ogc:PropertyIsLessThanOrEqualTo', 'ogc:PropertyIsGreaterThanOrEqualTo')
    >>> begin, end = fes_date_filter(start, stop, constraint='within')
    >>> begin.literal, end.literal
    ('2009-12-25 12:00', '2010-01-01 12:00')
    >>> begin.propertyoperator, end.propertyoperator
    ('ogc:PropertyIsGreaterThanOrEqualTo', 'ogc:PropertyIsLessThanOrEqualTo')
    """
    start = start.strftime("%Y-%m-%d %H:00")
    stop = stop.strftime("%Y-%m-%d %H:00")
    if constraint == "overlaps":
        propertyname = "apiso:TempExtent_begin"
        begin = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=stop)
        propertyname = "apiso:TempExtent_end"
        end = fes.PropertyIsGreaterThanOrEqualTo(
            propertyname=propertyname, literal=start
        )
    elif constraint == "within":
        propertyname = "apiso:TempExtent_begin"
        begin = fes.PropertyIsGreaterThanOrEqualTo(
            propertyname=propertyname, literal=start
        )
        propertyname = "apiso:TempExtent_end"
        end = fes.PropertyIsLessThanOrEqualTo(propertyname=propertyname, literal=stop)
    else:
        raise NameError("Unrecognized constraint {}".format(constraint))
    return begin, end

def csw_query(endpoint, bbox=None, start=None, stop=None, kw_names=None, crs="urn:ogc:def:crs:OGC:1.3:CRS84"):
    crs="urn:ogc:def:crs:::EPSG:4326" #https://github.com/qgis/QGIS/issues/40778
    constraints = []
    csw = None
    while csw is None:
        try:
            csw = CatalogueServiceWeb(endpoint, timeout=60)
            #csw.getrecords2(maxrecords=10)
            #for rec in csw.records:
            #    print(vars(csw.records[rec]))
            #    print(csw.records[rec].title)
        except:
            pass
    if kw_names:
        kw = dict(wildCard="*", escapeChar="\\", singleChar="?", propertyname="apiso:AnyText")
        or_filt = fes.Or([fes.PropertyIsLike(literal=("*%s*" % val), **kw) for val in kw_names])
        constraints.append(or_filt)
        
    if all(v is not None for v in [start, stop]): 
        begin, end = fes_date_filter(start, stop)
        constraints.append(begin)
        constraints.append(end)
    if bbox:
        bbox_crs = fes.BBox(bbox, crs=crs)
        constraints.append(bbox_crs)
    if len(constraints) >= 2:
        filter_list = [
            fes.And(
                constraints
            )
        ]
    else:
        filter_list = constraints
    get_csw_records(csw, filter_list, pagesize=10, maxrecords=10)

    print("Found {} records.\n".format(len(csw.records.keys())))
    for key, value in list(csw.records.items()):
        print(u"Title: [{}]\nID: {}\n".format(value.title, key))
        msg = "geolink: {geolink}\nscheme: {scheme}\nURL: {url}\n".format
        for ref in value.references:
            print(msg(geolink=sniff_link(ref["url"]), **ref))
        print("#########################################################", '\n')

def get_csw_records(csw, filter_list, pagesize=10, maxrecords=10000):
    """
    Iterate `maxrecords`/`pagesize` times until the requested value in `maxrecords` is reached.
    """
    # Iterate over sorted results.
    sortby = SortBy([SortProperty("dc:title", "ASC")])
    csw_records = {}
    startposition = 0
    nextrecord = getattr(csw, "results", 1)
    while nextrecord != 0:
        csw.getrecords2(
            constraints=filter_list,
            startposition=startposition,
            maxrecords=pagesize,
            sortby=sortby,
        )
        csw_records.update(csw.records)
        if csw.results["nextrecord"] == 0:
            break
        startposition += pagesize + 1  # Last one is included.
        if startposition >= maxrecords:
            break
    csw.records.update(csw_records)

def read_keywords(func, csw, url_endpoint, outputschema, accepted_vocabularies, pagesize=10, maxrecords=10):
    """
    Extract keyword from an endpoint.
    Different function (fun) can be used to use a different outputschema.
    """
    keywords = []
    nextrecord = getattr(csw, "results", 1)
    startposition = 0
    while nextrecord != 0:
        csw.getrecords2(startposition=startposition,maxrecords=pagesize, outputschema=outputschema, esn='full')
        #print(startposition)
        for rec in csw.records:
            keywords = keywords + func(csw.records[rec], url_endpoint, outputschema, accepted_vocabularies)
        if csw.results["nextrecord"] == 0:
            break
        startposition += pagesize + 1  # Last one is included.
        if startposition >= maxrecords:
            break
    return keywords

def get_csw_keywords_gmd(record, url_endpoint, outputschema, accepted_vocabularies):
    """
    Extract keyword from an endpoint using gmd schema.
    """
    keywords = []
    for ii in record.identificationinfo:
        #print(str(vars(ii)))
        if ii.keywords2 == None or len(ii.keywords) == 0:
            print("-- no keywords for the record: "  + url_endpoint + "?SERVICE=CSW&VERSION=2.0.2&outputSchema=" + outputschema + "&elementsetname=full&REQUEST=GetRecordById&ID=" + record.identifier)
        else:
            presence_keywords = False
            for jj in ii.keywords2: # for each set of keywords
                for kk in ii.keywords2:
                    if kk.keywords != None and len(kk.keywords) > 0 and kk.thesaurus != None and any(s in kk.thesaurus['title'] for s in accepted_vocabularies):#"GCMD" in kk.thesaurus['title']:
                        keywords = keywords + kk.keywords
                        presence_keywords = True
            if not presence_keywords:
                print("-- keywords or thesaurus not provided for the record: "  + url_endpoint + "?SERVICE=CSW&VERSION=2.0.2&outputSchema=" + outputschema + "&elementsetname=full&REQUEST=GetRecordById&ID=" + record.identifier)
    return keywords

def get_csw_keywords_default(record, url_endpoint, outputschema, accepted_vocabularies):
    """
    Extract keyword from an endpoint using default csw schema.
    """
    keywords = []
    keywords = keywords + record.subjects  
    keywords = [ x for x in keywords if ">" in x ] # filter for keeping only GCMD terms (temporary).
    return keywords

def get_csw_keywords(endpoints, accepted_vocabularies):
    """
    Extract keyword from a list of endpoints. gmd schema first and csw if no keywords found.
    """
    keywords = []
    for endpoint in endpoints:
        csw = CatalogueServiceWeb(endpoints[endpoint])
        ret = read_keywords(get_csw_keywords_gmd, csw, endpoints[endpoint], "http://www.isotc211.org/2005/gmd", accepted_vocabularies)
        if ret != None and len(ret) > 0:
            keywords = keywords + ret
        else:
            ret = read_keywords(get_csw_keywords_default, csw, endpoints[endpoint], "http://www.opengis.net/cat/csw/2.0.2", accepted_vocabularies)
            if ret != None and len(ret) > 0:
                keywords = keywords + ret
    if len(keywords) > 0:
        keywords = list(dict.fromkeys(keywords))
        #keywords = [ x.capitalize() for x in keywords ] 
    list.sort(keywords)
    return keywords

