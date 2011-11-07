import os, sys
import re
from copy import deepcopy
import pyfits as pf
import numpy as np
import tempfile
import astrodata
from astrodata import Lookups
from astrodata.adutils import gemLog
from astrodata.AstroData import AstroData
from astrodata import Errors

# Load the standard comments for header keywords that will be updated
# in these functions
keyword_comments = Lookups.get_lookup_table("Gemini/keyword_comments",
                                            "keyword_comments")

def checkInputsMatch(adInsA=None, adInsB=None, check_filter=True):
    """
    This function will check if the inputs match.  It will check the filter,
    binning and shape/size of the every SCI frames in the inputs.
    
    There must be a matching number of inputs for A and B.
    
    :param adInsA: input astrodata instance(s) to be check against adInsB
    :type adInsA: AstroData objects, either a single or a list of objects
                Note: inputs A and B must be matching length lists or single 
                objects
    
    :param adInsB: input astrodata instance(s) to be check against adInsA
    :type adInsB: AstroData objects, either a single or a list of objects
                  Note: inputs A and B must be matching length lists or single 
                  objects
    """
    log = gemLog.getGeminiLog() 
    
    # Check inputs are both matching length lists or single objects
    if (adInsA is None) or (adInsB is None):
        log.error('Neither A nor B inputs can be None')
        raise Errors.ToolboxError('Either A or B inputs were None')
    if isinstance(adInsA,list):
        if isinstance(adInsB,list):
            if len(adInsA)!=len(adInsB):
                log.error('Both the A and B inputs must be lists of MATCHING'+
                          ' lengths.')
                raise Errors.ToolboxError('There were mismatched numbers ' \
                                          'of A and B inputs.')
    if isinstance(adInsA,AstroData):
        if isinstance(adInsB,AstroData):
            # casting both A and B inputs to lists for looping later
            adInsA = [adInsA]
            adInsB = [adInsB]
        else:
            log.error('Both the A and B inputs must be lists of MATCHING'+
                      ' lengths.')
            raise Errors.ToolboxError('There were mismatched numbers of '+
                               'A and B inputs.')
    
    for count in range(0,len(adInsA)):
        A = adInsA[count]
        B = adInsB[count]
        log.fullinfo('Checking inputs '+A.filename+' and '+B.filename)
        
        if A.count_exts('SCI')!=B.count_exts('SCI'):
            log.error('Inputs have different numbers of SCI extensions.')
            raise Errors.ToolboxError('Mismatching number of SCI ' \
                                      'extensions in inputs')
        for sciA in A["SCI"]:
            # grab matching SCI extensions from A's and B's
            extCount = sciA.extver()
            sciB = B[('SCI',extCount)]
            
            log.fullinfo('Checking SCI extension '+str(extCount))
            
            # Check shape/size
            if sciA.data.shape!=sciB.data.shape:
                log.error('Extensions have different shapes')
                raise Errors.ToolboxError('Extensions have different shape')
            
            # Check binning
            aX = sciA.detector_x_bin()
            aY = sciA.detector_y_bin()
            bX = sciB.detector_x_bin()
            bY = sciB.detector_y_bin()
            if (aX!=bX) or (aY!=bY):
                log.error('Extensions have different binning')
                raise Errors.ToolboxError('Extensions have different binning')
        
            # Check filter if desired
            if check_filter:
                if (sciA.filter_name().as_pytype() != 
                    sciB.filter_name().as_pytype()):
                    log.error('Extensions have different filters')
                    raise Errors.ToolboxError('Extensions have different ' +
                                              'filters')
        
        log.fullinfo('Inputs match')    


def clip_auxiliary_data(adinput=None, aux=None, aux_type=None):
    """
    This function clips auxiliary data like calibration files or BPMs
    to the size of the data section in the science.  It will pad auxiliary
    data if required to match un-overscan-trimmed data, but otherwise
    requires that the auxiliary data contain the science data.
    """
    # Instantiate the log. This needs to be done outside of the try block,
    # since the log object is used in the except block 
    log = gemLog.getGeminiLog()
    
    # The validate_input function ensures that the input is not None and
    # returns a list containing one or more AstroData objects
    adinput = validate_input(adinput=adinput)
    aux = validate_input(adinput=aux)

    # Create a dictionary that has the AstroData objects specified by adinput
    # as the key and the AstroData objects specified by aux as the value
    aux_dict = make_dict(key_list=adinput, value_list=aux)
    
    # Initialize the list of output AstroData objects
    aux_output_list = []
 
    try:
        
        # Check aux_type parameter for valid value
        if aux_type is None:
            raise Errors.InputError("The aux_type parameter must not be None")

        # If dealing with BPMs, relevant extensions are DQ;
        # otherwise use SCI
        aux_type = aux_type.lower()
        if aux_type=="bpm":
            extname = "DQ"
        else:
            extname = "SCI"

        # Loop over each input AstroData object in the input list
        for ad in adinput:

            # Get the associated auxiliary file
            this_aux = aux_dict[ad]

            # Make a new blank auxiliary file for appending to
            new_aux = AstroData()
            new_aux.filename = this_aux.filename
            new_aux.phu = this_aux.phu

            for sciext in ad["SCI"]:

                # Get science detector, data, and array section
                # Should these be errors or should it try something
                # reasonable?
                sci_detsec = sciext.detector_section()
                if sci_detsec is None:
                    raise Errors.InputError("Input file %s does " \
                                            "not have a detector section" %
                                            ad.filename)
                else:
                    detsec_kw = sci_detsec.keyword
                    sci_detsec = sci_detsec.as_list()

                sci_datasec = sciext.data_section()
                if sci_datasec is None:
                    raise Errors.InputError("Input file %s does " \
                                            "not have a data section" %
                                            ad.filename)
                else:
                    datasec_kw = sci_datasec.keyword
                    sci_datasec = sci_datasec.as_list()

                sci_arraysec = sciext.array_section()
                if sci_arraysec is None:
                    raise Errors.InputError("Input file %s does " \
                                            "not have an array section" %
                                            ad.filename)
                else:
                    arraysec_kw = sci_arraysec.keyword
                    sci_arraysec = sci_arraysec.as_list()

                # Array section is unbinned; to use as indices for
                # extracting data, need to divide by the binning
                xbin = int(sciext.detector_x_bin())
                ybin = int(sciext.detector_y_bin())
                sci_arraysec = [sci_arraysec[0]/xbin,
                                sci_arraysec[1]/xbin,
                                sci_arraysec[2]/ybin,
                                sci_arraysec[3]/ybin]
                

                # Check whether science data has been overscan-trimmed
                sci_shape = sciext.data.shape
                if (sci_shape[1]==sci_datasec[1] and 
                    sci_shape[0]==sci_datasec[3] and
                    sci_datasec[0]==0 and
                    sci_datasec[2]==0):
                    sci_trimmed = True
                    sci_offsets = [0,0,0,0]
                else:
                    sci_trimmed = False

                    # Offsets give overscan regions on either side of data:
                    # [left offset, right offset, bottom offset, top offset]
                    sci_offsets = [sci_datasec[0],sci_shape[1]-sci_datasec[1],
                                   sci_datasec[2],sci_shape[0]-sci_datasec[3]]

                found = False
                for orig_auxext in this_aux[extname]:

                    auxext = deepcopy(orig_auxext)

                    # Get auxiliary VAR/DQ planes if they exist
                    # (in the non-BPM case)
                    ext_to_clip = [auxext]
                    if aux_type!="bpm":
                        varext = this_aux["VAR",orig_auxext.extver()]
                        if varext is not None:
                            ext_to_clip.append(deepcopy(varext))
                            
                        dqext = this_aux["DQ",orig_auxext.extver()]
                        if dqext is not None:
                            ext_to_clip.append(deepcopy(dqext))

                    # Get auxiliary detector, data, and array section
                    aux_detsec = auxext.detector_section(extname=extname)
                    if aux_detsec is None:
                        raise Errors.InputError("Auxiliary file %s does " \
                                                "not have a detector section" %
                                                this_aux.filename)
                    else:
                        aux_detsec = aux_detsec.as_list()

                    aux_datasec = auxext.data_section(extname=extname)
                    if aux_datasec is None:
                        raise Errors.InputError("Auxiliary file %s does " \
                                                "not have a data section" %
                                                this_aux.filename)
                    else:
                        aux_datasec = aux_datasec.as_list()

                    aux_arraysec = auxext.array_section(extname=extname)
                    if aux_arraysec is None:
                        raise Errors.InputError("Input file %s does " \
                                                "not have an array section" %
                                                ad.filename)
                    else:
                        aux_arraysec = aux_arraysec.as_list()

                    # Array section is unbinned; to use as indices for
                    # extracting data, need to divide by the binning
                    aux_arraysec = [aux_arraysec[0]/xbin,
                                    aux_arraysec[1]/xbin,
                                    aux_arraysec[2]/ybin,
                                    aux_arraysec[3]/ybin]

                    # Check whether auxiliary detector section contains
                    # science detector section
                    if (aux_detsec[0] <= sci_detsec[0] and # x lower
                        aux_detsec[1] >= sci_detsec[1] and # x upper
                        aux_detsec[2] <= sci_detsec[2] and # y lower
                        aux_detsec[3] >= sci_detsec[3]):   # y upper

                        # Auxiliary data contains or is equal to science data
                        found=True
                    else:
                        continue

                    # Check whether auxiliary data has been overscan-trimmed
                    aux_shape = auxext.data.shape
                    if (aux_shape[1]==aux_datasec[1] and 
                        aux_shape[0]==aux_datasec[3] and
                        aux_datasec[0]==0 and
                        aux_datasec[2]==0):
                        aux_trimmed = True
                        aux_offsets = [0,0,0,0]
                    else:
                        aux_trimmed = False

                        # Offsets give overscan regions on either side of data:
                        # [left offset, right offset, bottom offset, top offset]
                        aux_offsets = [aux_datasec[0],
                                       aux_shape[1]-aux_datasec[1],
                                       aux_datasec[2],
                                       aux_shape[0]-aux_datasec[3]]

                    # Define data extraction region corresponding to science
                    # data section (not including overscan)
                    x_translation = sci_arraysec[0] - sci_datasec[0] \
                                    - aux_arraysec[0] + aux_datasec[0]
                    y_translation = sci_arraysec[2] - sci_datasec[2] \
                                    - aux_arraysec[2] + aux_datasec[2]
                    region = [sci_datasec[2] + y_translation,
                              sci_datasec[3] + y_translation,
                              sci_datasec[0] + x_translation,
                              sci_datasec[1] + x_translation]

                    # Clip all relevant extensions
                    for ext in ext_to_clip:

                        # Pull out specified region
                        clipped = ext.data[region[0]:region[1],
                                           region[2]:region[3]]
                        
                        # Stack with overscan region if needed
                        if aux_trimmed and not sci_trimmed:

                            # Pad DQ planes with zeros to match
                            # science shape
                            # Note: this only allows an overscan
                            # region at one edge of the data array.
                            # If there ends up being more
                            # than one for some instrument, this code
                            # will have to be revised.
                            if aux_type=="bpm":
                                if sci_offsets[0]>0:
                                    # Left-side overscan
                                    overscan = np.zeros((sci_shape[0],
                                                         sci_offsets[0]),
                                                        dtype=np.int16)
                                    ext.data = np.hstack([overscan,clipped])
                                elif sci_offsets[1]>0:
                                    # Right-side overscan
                                    overscan = np.zeros((sci_shape[0],
                                                         sci_offsets[1]),
                                                        dtype=np.int16)
                                    ext.data = np.hstack([clipped,overscan])
                                elif sci_offsets[2]>0:
                                    # Bottom-side overscan
                                    overscan = np.zeros((sci_offsets[2],
                                                         sci_shape[1]),
                                                        dtype=np.int16)
                                    ext.data = np.vstack([clipped,overscan])
                                elif sci_offsets[3]>0:
                                    # Top-side overscan
                                    overscan = np.zeros((sci_offsets[3],
                                                         sci_shape[1]),
                                                        dtype=np.int16)
                                    ext.data = np.vstack([overscan,clipped])
                            else:
                                # Science decision: trimmed calibrations
                                # can't be meaningfully matched to untrimmed
                                # science data
                                raise Errors.ScienceError(
                                    "Auxiliary data %s is trimmed, but " \
                                    "science data %s is untrimmed." %
                                    (auxext.filename,sciext.filename))

                        elif not sci_trimmed:
                            
                            # Pick out overscan region corresponding
                            # to data section from auxiliary data
                            if aux_offsets[0]>0:
                                if aux_offsets[0]!=sci_offsets[0]:
                                    raise Errors.ScienceError(
                                        "Overscan regions do not match in " \
                                        "%s, %s" % 
                                        (auxext.filename,sciext.filename))

                                # Left-side overscan: height is full ylength,
                                # width comes from 0 -> offset
                                overscan = ext.data[region[0]:region[1],
                                                    0:aux_offsets[0]]
                                ext.data = np.hstack([overscan,clipped])

                            elif aux_offsets[1]>0:
                                if aux_offsets[1]!=sci_offsets[1]:
                                    raise Errors.ScienceError(
                                        "Overscan regions do not match in " \
                                        "%s, %s" % 
                                        (auxext.filename,sciext.filename))

                                # Right-side overscan: height is full ylength,
                                # width comes from xlength-offset -> xlength
                                overscan = ext.data[region[0]:region[1],
                                    aux_shape[1]-aux_offsets[1]:aux_shape[1]]
                                ext.data = np.hstack([clipped,overscan])

                            elif aux_offsets[2]>0: 
                                if aux_offsets[2]!=sci_offsets[2]:
                                    raise Errors.ScienceError(
                                        "Overscan regions do not match in " \
                                        "%s, %s" % 
                                        (auxext.filename,sciext.filename))

                                # Bottom-side overscan: width is full xlength,
                                # height comes from 0 -> offset
                                overscan = ext.data[0:aux_offsets[2],
                                                    region[2]:region[3]]
                                ext.data = np.vstack([clipped,overscan])

                            elif aux_offsets[3]>0:
                                if aux_offsets[3]!=sci_offsets[3]:
                                    raise Errors.ScienceError(
                                        "Overscan regions do not match in " \
                                        "%s, %s" % 
                                        (auxext.filename,sciext.filename))

                                # Top-side overscan: width is full xlength,
                                # height comes from ylength-offset -> ylength
                                overscan = ext.data[
                                    aux_shape[0]-aux_offsets[3]:aux_shape[0],
                                    region[2]:region[3]]
                                ext.data = np.vstack([overscan,clipped])

                        else:
                            # No overscan needed, just use the clipped region
                            ext.data = clipped

                        # Set the section keywords as appropriate
                        if sciext.get_key_value(datasec_kw) is not None:
                            ext.set_key_value(datasec_kw,
                                              sciext.header[datasec_kw],
                                              keyword_comments[datasec_kw])
                        if sciext.get_key_value(detsec_kw) is not None:
                            ext.set_key_value(detsec_kw,
                                              sciext.header[detsec_kw],
                                              keyword_comments[detsec_kw])
                        if sciext.get_key_value(arraysec_kw) is not None:
                            ext.set_key_value(arraysec_kw,
                                              sciext.header[arraysec_kw],
                                              keyword_comments[arraysec_kw])
        
                        # Rename the auxext to the science extver
                        ext.rename_ext(name=ext.extname(),ver=sciext.extver())
                        new_aux.append(ext)

                if not found:
                    raise Errors.ScienceError("No auxiliary data in %s "\
                                              "matches the detector section "\
                                              "%s in %s[SCI,%d]" % 
                                              (this_aux.filename,
                                               sci_detsec,
                                               ad.filename,
                                               sciext.extver()))

            new_aux.refresh_types()
            aux_output_list.append(new_aux)

        return aux_output_list    

    except:
        # Log the message from the exception
        log.critical(repr(sys.exc_info()[1]))
        raise
                    

def convert_to_cal_header(adinput=None, caltype=None):
    """
    This function replaces position, object, and program information 
    in the headers of processed calibration files that are generated
    from science frames, eg. fringe frames, maybe sky frames too.
    It is called, for example, from the storeProcessedFringe primitive.

    :param adinput: astrodata instance to perform header key updates on
    :type adinput: an AstroData instance

    :param caltype: type of calibration.  Accepted values are 'fringe' or
                    'sky'
    :type caltype: string
    """

    # Instantiate the log. This needs to be done outside of the try block,
    # since the log object is used in the except block 
    log = gemLog.getGeminiLog()
    
    # The validate_input function ensures that the input is not None and
    # returns a list containing one or more AstroData objects
    adinput = validate_input(adinput=adinput)
    
    # Initialize the list of output AstroData objects
    adoutput_list = []
    
    try:

        if caltype is None:
            raise Errors.InputError("Caltype should not be None")

        fitsfilenamecre = re.compile("^([NS])(20\d\d)([01]\d[0123]\d)(S)"\
                                     "(?P<fileno>\d\d\d\d)(.*)$")

        for ad in adinput:

            log.fullinfo("Setting OBSCLASS, OBSTYPE, GEMPRGID, OBSID, " +
                         "DATALAB, RELEASE, OBJECT, RA, DEC, CRVAL1, " +
                         "and CRVAL2 to generic defaults")

            # Do some date manipulation to get release date and 
            # fake program number

            # Get date from day data was taken if possible
            date_taken = ad.ut_date()
            if date_taken.collapse_value() is None:
                # Otherwise use current time
                import datetime
                date_taken = datetime.date.today()
            else:
                date_taken = date_taken.as_pytype()
            site = str(ad.telescope()).lower()
            release = date_taken.strftime("%Y-%m-%d")

            # Fake ID is G(N/S)-CALYYYYMMDD-900-fileno
            if "north" in site:
                prefix = "GN-CAL"
            elif "south" in site:
                prefix = "GS-CAL"
            prgid = "%s%s" % (prefix,date_taken.strftime("%Y%m%d"))
            obsid = "%s-%d" % (prgid, 900)

            m = fitsfilenamecre.match(ad.filename)
            if m:
                fileno = m.group("fileno")
                try:
                    fileno = int(fileno)
                except:
                    fileno = None
            else:
                fileno = None

            # Use a random number if the file doesn't have a
            # Gemini filename
            if fileno is None:
                import random
                fileno = random.randint(1,999)
            datalabel = "%s-%03d" % (obsid,fileno)

            # Set class, type, object to generic defaults
            ad.phu_set_key_value("OBSCLASS","partnerCal",
                                 keyword_comments["OBSCLASS"])

            if "fringe" in caltype:
                ad.phu_set_key_value("OBSTYPE","FRINGE",
                                     keyword_comments["OBSTYPE"])
                ad.phu_set_key_value("OBJECT","Fringe Frame",
                                     keyword_comments["OBJECT"])
            elif "sky" in caltype:
                ad.phu_set_key_value("OBSTYPE","SKY",
                                     keyword_comments["OBSTYPE"])
                ad.phu_set_key_value("OBJECT","Sky Frame",
                                     keyword_comments["OBJECT"])
            else:
                raise Errors.InputError("Caltype %s not supported" % caltype)
            
            # Blank out program information
            ad.phu_set_key_value("GEMPRGID",prgid,
                                 keyword_comments["GEMPRGID"])
            ad.phu_set_key_value("OBSID",obsid,
                                 keyword_comments["OBSID"])
            ad.phu_set_key_value("DATALAB",datalabel,
                                 keyword_comments["DATALAB"])

            # Set release date
            ad.phu_set_key_value("RELEASE",release,
                                 keyword_comments["RELEASE"])

            # Blank out positional information
            ad.phu_set_key_value("RA",0.0,keyword_comments["RA"])
            ad.phu_set_key_value("DEC",0.0,keyword_comments["DEC"])
            
            # Blank out RA/Dec in WCS information in PHU if present
            if ad.phu_get_key_value("CRVAL1") is not None:
                ad.phu_set_key_value("CRVAL1",0.0,keyword_comments["CRVAL1"])
            if ad.phu_get_key_value("CRVAL2") is not None:
                ad.phu_set_key_value("CRVAL2",0.0,keyword_comments["CRVAL2"])

            # Do the same for each SCI,VAR,DQ extension
            # as well as the object name
            for ext in ad:
                if ext.extname() not in ["SCI","VAR","DQ"]:
                    continue
                if ext.get_key_value("CRVAL1") is not None:
                    ext.set_key_value("CRVAL1",0.0,keyword_comments["CRVAL1"])
                if ext.get_key_value("CRVAL2") is not None:
                    ext.set_key_value("CRVAL2",0.0,keyword_comments["CRVAL2"])
                if ext.get_key_value("OBJECT") is not None:
                    if "fringe" in caltype:
                        ext.set_key_value("OBJECT","Fringe Frame",
                                          keyword_comments["OBJECT"])
                    elif "sky" in caltype:
                        ext.set_key_value("OBJECT","Sky Frame",
                                          keyword_comments["OBJECT"])

            adoutput_list.append(ad)

        return adoutput_list    

    except:
        # Log the message from the exception
        log.critical(repr(sys.exc_info()[1]))
        raise


def fileNameUpdater(adIn=None, infilename='', suffix='', prefix='',
                    strip=False):
    """
    This function is for updating the file names of astrodata objects.
    It can be used in a few different ways.  For simple post/pre pending of
    the infilename string, there is no need to define adIn or strip. The 
    current filename for adIn will be used if infilename is not defined. 
    The examples below should make the main uses clear.
        
    Note: 
    1.if the input filename has a path, the returned value will have
    path stripped off of it.
    2. if strip is set to True, then adIn must be defined.
          
    :param adIn: input astrodata instance having its filename being updated
    :type adIn: astrodata object
    
    :param infilename: filename to be updated
    :type infilename: string
    
    :param suffix: string to put between end of current filename and the 
                   extension 
    :type suffix: string
    
    :param prefix: string to put at the beginning of a filename
    :type prefix: string
    
    :param strip: Boolean to signal that the original filename of the astrodata
                  object prior to processing should be used. adIn MUST be 
                  defined for this to work.
    :type strip: Boolean
    
    ::
    
     fileNameUpdater(adIn=myAstrodataObject, suffix='_prepared', strip=True)
     result: 'N20020214S022_prepared.fits'
        
     fileNameUpdater(infilename='N20020214S022_prepared.fits',
         suffix='_biasCorrected')
     result: 'N20020214S022_prepared_biasCorrected.fits'
        
     fileNameUpdater(adIn=myAstrodataObject, prefix='testversion_')
     result: 'testversion_N20020214S022.fits'
    
    """
    log = gemLog.getGeminiLog() 

    # Check there is a name to update
    if infilename=='':
        # if both infilename and adIn are not passed in, then log critical msg
        if adIn==None:
            log.critical('A filename or an astrodata object must be passed '+
                         'into fileNameUpdater, so it has a name to update')
        # adIn was passed in, so set infilename to that ad's filename
        else:
            infilename = adIn.filename
            
    # Strip off any path that the input file name might have
    basefilename = os.path.basename(infilename)

    # Split up the filename and the file type ie. the extension
    (name,filetype) = os.path.splitext(basefilename)
    
    if strip:
        # Grabbing the value of PHU key 'ORIGNAME'
        phuOrigFilename = adIn.phu_get_key_value('ORIGNAME') 
        # If key was 'None', ie. store_original_name() wasn't ran yet, then run
        # it now
        if phuOrigFilename is None:
            # Storing the original name of this astrodata object in the PHU
            phuOrigFilename = adIn.store_original_name()
            
        # Split up the filename and the file type ie. the extension
        (name,filetype) = os.path.splitext(phuOrigFilename)
        
    # Create output filename
    outFileName = prefix+name+suffix+filetype
    return outFileName
    

def log_message(function, name, message_type):
    if function == 'ulf':
        full_function_name = 'user level function'
    else:
        full_function_name = function
    if message_type == 'calling':
        message = 'Calling the %s %s' \
                  % (full_function_name, name)
    if message_type == 'starting':
        message = 'Starting the %s %s' \
                  % (full_function_name, name)
    if message_type == 'finishing':
        message = 'Finishing the %s %s' \
                  % (full_function_name, name)
    if message_type == 'completed':
        message = 'The %s %s completed successfully' \
                  % (name, full_function_name)
    if message:
        return message
    else:
        return None


def make_dict(key_list=None, value_list=None):
    """
    The make_dict function creates a dictionary with the elements in 'key_list'
    as the key and the elements in 'value_list' as the value to create an
    association between the input science dataset (the 'key_list') and a, for
    example, dark that is needed to be subtracted from the input science
    dataset. This function also does some basic checks to ensure that the
    filters, exposure time etc are the same.

    :param key: List containing one or more AstroData objects
    :type key: AstroData

    :param value: List containing one or more AstroData objects
    :type value: AstroData
    """
    # Check the inputs have matching filters, binning and SCI shapes.
    #checkInputsMatch(adInsA=darks, adInsB=adInputs)
    ret_dict = {}
    if len(key_list) == 1 and len(value_list) == 1:
        # There is only one key and one value - create a single entry in the
        # dictionary
        ret_dict[key_list[0]] = value_list[0]
    elif len(key_list) > 1 and len(value_list) == 1:
        # There is only one value for the list of keys
        for i in range (0, len(key_list)):
            ret_dict[key_list[i]] = value_list[0]
    elif len(key_list) > 1 and len(value_list) > 1:
        # There is one value for each key. Check that the lists are the same
        # length
        if len(key_list) != len(value_list):
            msg = """Number of AstroData objects in key_list does not match
            with the number of AstroData objects in value_list. Please provide
            lists containing the same number of AstroData objects. Please
            supply either a single AstroData object in value_list to be applied
            to all AstroData objects in key_list OR the same number of
            AstroData objects in value_list as there are in key_list"""
            raise Errors.InputError(msg)
        for i in range (0, len(key_list)):
            ret_dict[key_list[i]] = value_list[i]
    
    return ret_dict

def mark_history(adinput=None, keyword=None):
    """
    The function to use near the end of a python user level function to 
    add a history_mark timestamp to all the outputs indicating when and what
    function was just performed on them, then logging the new historyMarkKey
    PHU key and updated 'GEM-TLM' key values due to history_mark.
    
    Note: The GEM-TLM key will be updated, or added if not in the PHU yet, 
    automatically everytime wrapUp is called.
    
    :param adinput: List of astrodata instance(s) to perform history_mark 
                      on.
    :type adinput: Either a single or multiple astrodata instances in a 
                     list.
    
    :param keyword: The PHU header key to write the current UT time 
    :type keyword: Under 8 character, all caps, string.
                          If None, then only 'GEM-TLM' is added/updated.
    """
    # Instantiate the log
    log = gemLog.getGeminiLog()
    # If adinput is a single AstroData object, put it in a list
    if not isinstance(adinput, list):
        adinput = [adinput]
    # Loop over each input AstroData object in the input list
    for ad in adinput:
        # Add the 'GEM-TLM' keyword (automatic) and the keyword specified by
        # the 'keyword' parameter to the PHU. If 'keyword' is None,
        # history_mark will still add the 'GEM-TLM' keyword
        ad.history_mark(key=keyword, stomp=True)
        if keyword is not None:
            log.fullinfo("PHU keyword %s = %s added to %s" \
                         % (keyword, ad.phu_get_key_value(keyword),
                            ad.filename), category='header')
        log.fullinfo("PHU keyword GEM-TLM = %s added to %s" \
                     % (ad.phu_get_key_value("GEM-TLM"), ad.filename),
                     category='header')

def update_key_from_descriptor(adinput=None, descriptor=None, 
                               keyword=None, extname=None):
    """
    This function updates keywords in the headers of the input dataset,
    performs logging of the changes and writes history keyword related to the
    changes to the PHU.
    
    :param adinput: astrodata instance to perform header key updates on
    :type adinput: an AstroData instance
    
    :param descriptor: string for an astrodata function or descriptor function
                       to perform on the input ad.
                       ie. for ad.gain(), descriptor='gain()'
    :type descriptor: string 
    
    :param extname: Set to 'PHU', 'SCI', 'VAR' or 'DQ' to update the given
                    keyword in the PHU, SCI, VAR or DQ extension, respectively.
                    
    :type extname: string
    """
    log = gemLog.getGeminiLog()
    historyComment = None

    # Make sure a valid extname is specified
    if extname is None:
        extname = "SCI"

    if extname == "PHU":
        # Use exec to perform the requested function on full AD 
        # Allow it to raise the error if the descriptor fails
        exec('dv = adinput.%s' % descriptor)
        if dv is None:
            log.fullinfo("No value found for descriptor %s on %s" % 
                         (descriptor,adinput.filename))
        else:
            if keyword is not None:
                key = keyword
            else:
                key = dv.keyword
                if key is None:
                    raise Errors.ToolboxError(
                        "No keyword found for descriptor %s" % descriptor)

            # Get comment from lookup table
            # Allow it to raise the KeyError if it can't find it
            comment = keyword_comments[key]
            
            # Set the keyword value and comment
            adinput.phu_set_key_value(key, dv.as_pytype(), comment)
    else:
        for ext in adinput[extname]:
            # Use exec to perform the requested function on a single extension
            # Allow it to raise the error if the descriptor fails
            exec('dv = ext.%s' % descriptor)
            if dv is None:
                log.fullinfo("No value found for descriptor %s on %s[%s,%d]" %
                             (descriptor,adinput.filename,
                              ext.extname(),ext.extver()))
            else:
                if keyword is not None:
                    key = keyword
                else:
                    key = dv.keyword
                    if key is None:
                        raise Errors.ToolboxError(
                            "No keyword found for descriptor %s" % descriptor)
        
                # Get comment from lookup table
                # Allow it to raise the KeyError if it can't find it
                comment = keyword_comments[key]
            
                # Set the keyword value and comment
                ext.set_key_value(key, dv.as_pytype(), comment)
            


def validate_input(adinput=None):
    """
    The validate_input helper function is used to validate the inputs given to
    the user level functions.
    """
    # If the adinput is None, raise an exception
    if adinput is None:
        raise Errors.InputError("The adinput cannot be None")
    # If the adinput is a single AstroData object, put it in a list
    if not isinstance(adinput, list):
        adinput = [adinput]
    # If the adinput is an empty list, raise an exception
    if len(adinput) == 0:
        raise Errors.InputError("The adinput cannot be an empty list")
    # Now, adinput is a list that contains one or more AstroData objects
    return adinput
