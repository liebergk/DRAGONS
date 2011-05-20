# This module contains user level functions related to resampling the input
# dataset

import sys
from astrodata import Errors
from astrodata.adutils.gemutil import pyrafLoader
from gempy import geminiTools as gt
from gempy import managers as man
from gempy.geminiCLParDicts import CLDefaultParamsDict

def mosaic_detectors(adInputs, fl_paste=False, interp_function='linear',  
                fl_vardq='AUTO', outNames=None, suffix=None):
    """
    This function will mosaic the SCI frames of the input images, 
    along with the VAR and DQ frames if they exist.  
    
    WARNING: The gmosaic script used here replaces the previously 
    calculated DQ frames with its own versions.  This may be corrected 
    in the future by replacing the use of the gmosaic
    with a Python routine to do the frame mosaicing.
    
    NOTE: The inputs to this function MUST be prepared. 

    Either a 'main' type logger object, if it exists, or a null logger 
    (ie, no log file, no messages to screen) will be retrieved/created in the 
    ScienceFunctionManager and used within this function.
    
    :param adInputs: Astrodata inputs to mosaic the extensions of
    :type adInputs: Astrodata objects, either a single or a list of objects
    
    :param fl_paste: Paste images instead of mosaic?
    :type fl_paste: Python boolean (True/False)
    
    :param interp_function: type of interpolation algorithm to use for between 
                            the chip gaps.
    :type interp_function: string, options: 'linear', 'nearest', 'poly3', 
                           'poly5', 'spine3', 'sinc'.
    
    :param fl_vardq: Also mosaic VAR and DQ frames?
    :type fl_vardq: Python boolean (True/False), OR string 'AUTO' to do 
                    it automatically if there are VAR and DQ frames in the 
                    inputs.
                    NOTE: 'AUTO' uses the first input to determine if VAR and  
                    DQ frames exist, so, if the first does, then the rest MUST 
                    also have them as well.
    
    :param outNames: filenames of output(s)
    :type outNames: String, either a single or a list of strings of same length 
                    as adInputs.
    
    :param suffix: string to add on the end of the input filenames 
                    (or outNames if not None) for the output filenames.
    :type suffix: string
    
    """
    
    # Instantiate ScienceFunctionManager object
    sfm = man.ScienceFunctionManager(adInputs, outNames, suffix, 
                                      funcName='mosaic_detectors') 
    # Perform start up checks of the inputs, prep/check of outnames, and get log
    adInputs, outNames, log = sfm.startUp()
    
    try:
        # loading and bringing the pyraf related modules into the name-space
        pyraf, gemini, yes, no = pyrafLoader()  
            
        # Converting input True/False to yes/no or detecting fl_vardq value
        # if 'AUTO' chosen with autoVardq in the ScienceFunctionManager
        fl_vardq = sfm.autoVardq(fl_vardq)
        
        # To clean up log and screen if multiple inputs
        log.fullinfo('+'*50, category='format')    
        
        # Preparing input files, lists, parameters... for input to 
        # the CL script
        clm=man.CLManager(imageIns=adInputs, imageOutsNames=outNames, 
                           suffix=suffix, funcName='mosaicDetectors', log=log)
        
        # Check the status of the CLManager object, True=continue, False= issue warning
        if clm.status: 
            # Parameters set by the man.CLManager or the definition of the prim 
            clPrimParams = {
              # Retrieving the inputs as a string of filenames
              'inimages'    :clm.imageInsFiles(type='string'),
              'outimages'   :clm.imageOutsFiles(type='string'),
              # Setting the value of FL_vardq set above
              'fl_vardq'    :fl_vardq,
              # This returns a unique/temp log file for IRAF 
              'logfile'     :clm.templog.name,               
                          }
            # Parameters from the Parameter file adjustable by the user
            clSoftcodedParams = {
              # pyrafBoolean converts the python booleans to pyraf ones
              'fl_paste'    :gt.pyrafBoolean(fl_paste),
              'outpref'     :suffix,
              'geointer'    :interp_function,
                              }
            # Grabbing the default params dict and updating it with 
            # the two above dicts
            clParamsDict = CLDefaultParamsDict('gmosaic')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)      
                
            # Logging the parameters that were not defaults
            log.fullinfo('\nParameters set automatically:', 
                         category='parameters')
            # Loop through the parameters in the clPrimParams dictionary
            # and log them
            gt.logDictParams(clPrimParams)
            
            log.fullinfo('\nParameters adjustable by the user:', 
                         category='parameters')
            # Loop through the parameters in the clSoftcodedParams 
            # dictionary and log them
            gt.logDictParams(clSoftcodedParams)
            
            log.debug('calling the gmosaic CL script for inputs '+
                                        clm.imageInsFiles(type='string'))
        
            gemini.gmos.gmosaic(**clParamsDict)
    
            if gemini.gmos.gmosaic.status:
                raise Errors.ScienceError('gireduce failed for inputs '+
                             clm.imageInsFiles(type='string'))
            else:
                log.status('Exited the gmosaic CL script successfully')    
                
                
            # Renaming CL outputs and loading them back into memory 
            # and cleaning up the intermediate temp files written to disk
            # refOuts and arrayOuts are None here
            imageOuts, refOuts, arrayOuts = clm.finishCL()   
            
            # Renaming for symmetry
            adOutputs = imageOuts
                
            # Wrap up logging
            i=0
            for ad in adOutputs:
                log.fullinfo('-'*50, category='header')
                
                # Varifying gireduce was actually ran on the file
                # then logging file names of successfully reduced files
                if ad.phu_get_key_value('GMOSAIC'): 
                    log.fullinfo('\nFile '+clm.preCLimageNames()[i]+\
                                 ' mosaiced successfully')
                    log.fullinfo('New file name is: '+ad.filename)
                i=i+1

                # Updating GEM-TLM (automatic) and BIASCORR time stamps to the PHU
                # and updating logger with updated/added time stamps
                sfm.markHistory(adOutputs=ad, historyMarkKey='MOSAIC')
        else:
            raise Errors.ScienceError('One of the inputs has not been prepared, the'+
             ' mosaicDetectors function can only work on prepared data.')
                
        log.status('**FINISHED** the mosaic_detectors function')
        
        # Return the outputs list, even if there is only one output
        return adOutputs
    except:
        # logging the exact message from the actual exception that was raised
        # in the try block. Then raising a general ScienceError with message.
        log.critical(repr(sys.exc_info()[1]))
        raise
