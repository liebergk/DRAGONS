from astrodata.eti.pyrafetiparam import PyrafETIParam, IrafStdout
from pyraf import iraf
from astrodata.adutils import logutils

log = logutils.get_logger(__name__)

class GscrrejParam(PyrafETIParam):
    """This class coordinates the ETI parameters as it pertains to the IRAF
    task gscrrej directly.
    """
    rc = None
    adinput = None
    key = None
    value = None
    def __init__(self, rc=None, key=None, value=None):
        """
        :param rc: Used to store reduction information
        :type rc: ReductionContext

        :param key: A parameter name that is added as a dict key in prepare
        :type key: any

        :param value: A parameter value that is added as a dict value
                      in prepare
        :type value: any
        """
        log.debug("GscrrejParam __init__")
        PyrafETIParam.__init__(self, rc)
        self.adinput = self.rc.get_inputs_as_astrodata()
        self.key = key
        self.value = value

    def nonecheck(self, param=None):
        if param is None or param == "None":
            param = "none"
        return param

    def prepare(self):
        log.debug("Gscrrej prepare()")
        self.paramdict.update({self.key:self.value})
        

hardcoded_params = {'Stdout':IrafStdout(),
                    'Stderr':IrafStdout(),
                    }

