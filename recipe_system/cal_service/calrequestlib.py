#
#                                                               calrequestlib.py
# ------------------------------------------------------------------------------
from os import mkdir
from os.path import dirname, basename, exists, join
from datetime import datetime

import hashlib
# Handle 2.x and 3.x. Module urlparse is urllib.parse in 3.x
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

from urllib2  import HTTPError

import astrodata
import gemini_instruments

from gempy.utils import logutils
from gempy.utils import netutil

from .caches  import set_caches
from recipe_system.cal_service import cal_search_factory
# ------------------------------------------------------------------------------
log = logutils.get_logger(__name__)
Section = gemini_instruments.common.Section
# ------------------------------------------------------------------------------
# Currently delivers transport_request.calibration_search fn.
calibration_search = cal_search_factory()
# ------------------------------------------------------------------------------
descriptor_list = ['amp_read_area','camera','central_wavelength','coadds',
                   'data_label','data_section','detector_roi_setting',
                   'detector_x_bin','detector_y_bin','disperser','exposure_time',
                   'filter_name','focal_plane_mask','gain_setting','gcal_lamp',
                   'instrument','lyot_stop','nod_count','nod_pixels','object',
                   'observation_class','observation_type','program_id',
                   'read_speed_setting', 'ut_datetime','read_mode',
                   'well_depth_setting']
# ------------------------------------------------------------------------------
def generate_md5_digest(filename):
    md5 = hashlib.md5()
    fdata = open(filename).read()
    md5.update(fdata)
    return md5.hexdigest()

def _check_cache(cname, ctype):
    cachedir = _makecachedir(ctype)
    cachename = join(cachedir, cname)
    if exists(cachename):
        return cachename, cachedir
    return None, cachedir

def _makecachedir(caltype):
    cache = set_caches()
    cachedir = join(cache["calibrations"], caltype)
    if not exists(cachedir):
        mkdir(cachedir)
    return cachedir

class CalibrationRequest(object):
    """
    Request objects are passed to a calibration_search() function
    
    """
    def __init__(self, ad, caltype=None):
        self.ad = ad
        self.caltype  = caltype
        self.datalabel = ad.data_label()
        self.descriptors = None
        self.filename = ad.filename
        self.tags = ad.tags

    def as_dict(self):
        retd = {}
        retd.update(
            {'filename'   : self.filename,
             'caltype'    : self.caltype,
             'datalabel'  : self.datalabel,
             "descriptors": self.descriptors,
             "tags"       : self.tags,
         }
        )

        return retd

    def __str__(self):
        tempStr = "filename: {}\nDescriptors: {}\nTypes: {}"
        tempStr = tempStr.format(self.filename, self.descriptors, self.tags)
        return tempStr


def get_cal_requests(inputs, caltype):
    """
    Builds a list of CalibrationRequest objects, one for each 'ad' input.
    
    @param inputs: list of input AstroData instances
    @type inputs:  <list>
    
    @param caltype: Calibration type, eg., 'processed_bias', 'flat', etc.
    @type caltype:  <str>
    
    @return: Returns a list of CalibrationRequest instances, one for
             each passed 'ad' instance in 'inputs'.
    @rtype:  <list>

    """
    dlist = []
    options = { 'central_wavelength': 'asMicrometers=True' }
    def _handle_sections(dv):
        if isinstance(dv, list) and isinstance(dv[0], Section):
                return [ [el.x1, el.x2, el.y1, el.y2] for el in dv ]
        return dv

    rqEvents = []
    for ad in inputs:
        log.stdinfo("Recieved calibration request for {}".format(ad.filename))
        rq = CalibrationRequest(ad, caltype)
        # Check that each descriptor works and returns a sensible value.
        desc_dict = {}
        for desc_name in descriptor_list:
            descriptor = getattr(ad, desc_name)
            if desc_name in options.keys():
                desc_dict[desc_name] = descriptor(options[desc_name])
            elif desc_name == 'amp_read_area':
                desc_dict[desc_name] = "+".join(descriptor())
            else:
                try:
                    desc_dict[desc_name] = _handle_sections(descriptor())
                except (KeyError, ValueError):
                    desc_dict[desc_name] = None
        rq.descriptors = desc_dict
        rqEvents.append(rq)
            
    return rqEvents


def process_cal_requests(cal_requests):
    """
    Conduct a search for calibration files for the passed list of calibration
    requests. This passes the requests to the calibration_search() function,
    and then examines the search results to see if a matching file, if any,
    is cached. If not, then the calibration file is retrieved from the
    archive.

    If a calibration match is found by the calibration manager, a URL is
    returned. This function will perform a cache inspection to see if the
    matched calibraiton file is already present. If not, the calibration
    will be downloaded and written to the cache. It is this path that is 
    returned in the dictionary structure. A path of 'None' indicates that no
    calibration match was found.

    :parameter cal_requests: list of CalibrationRequest objects
    :type cal_requests: <list>

    :returns: A set of science frames and matching calibrations.
    :rtype:   <dict>

    E.g., The returned dictionary has the form, 

    { (input datalabel, caltype): (<filename>, <path_to_calibration>, caltype),
      ...
    }

    """
    calibration_records = {}
    def _add_cal_record(rq, calfile):
        rqkey = (rq.datalabel, rq.caltype)
        calrec = (rq.filename, calfile, rq.caltype)
        calibration_records.update({rqkey: calrec})
        return

    cache = set_caches()
    for rq in cal_requests:
        calname = None
        calmd5 = None
        calurl = None
        sci_ad = rq.ad
        calurl, calmd5 = calibration_search(rq)
        if calurl is None:
            log.error("START CALIBRATION SERVICE REPORT\n")
            log.error(calmd5)
            log.error("END CALIBRATION SERVICE REPORT\n")
            warn = "No {} calibration file found for {}"
            log.warning(warn.format(rq.caltype, rq.filename))
            _add_cal_record(rq, calname)
            continue

        log.info("found calibration (url): {}".format(calurl))
        components = urlparse(calurl)
        calname = basename(components.path)
        cachename, cachedir = _check_cache(calname, rq.caltype)
        if cachename:
            cached_md5 = generate_md5_digest(cachename)
            if cached_md5 == calmd5:
                log.stdinfo("Cached calibration {} matched.".format(cachename))
                _add_cal_record(rq, cachename)
                continue
            else:
                log.stdinfo("File {} is cached but".format(calbname))
                log.stdinfo("md5 checksums DO NOT MATCH")
                log.stdinfo("Making request on calibration service")
                log.stdinfo("Requesting URL {}".format(calurl))
                try:
                    calname = netutil.urlfetch(calurl, store=cachedir)
                    _add_cal_record(rq, cachename)
                    continue
                except HTTPError, error:
                    errstr = "Could not retrieve {}".format(calurl)
                    log.error(errstr)

        try:
            calname = netutil.urlfetch(calurl, store=cachedir)
            _add_cal_record(rq, calname)
        except HTTPError as err:
            log.error(str(err))

    return calibration_records
