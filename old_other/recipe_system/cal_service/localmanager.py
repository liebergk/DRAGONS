import os
from os.path import abspath, basename, dirname, isdir
import warnings
from collections import namedtuple

from sqlalchemy.exc import SAWarning, OperationalError
from gemini_calmgr import fits_storage_config as fsc
from gemini_calmgr import gemini_metadata_utils as gmu
from gemini_calmgr import orm
from gemini_calmgr.orm import file
from gemini_calmgr.orm import diskfile
from gemini_calmgr.orm import preview
from gemini_calmgr.cal import get_cal_object
from gemini_calmgr.orm import createtables
from gemini_calmgr.utils import ingest

__all__ = ['LocalManager, LocalManagerError']

# SQLAlchemy complains about SQLite details. We can't do anything about the
# data types involved, because the ORM files are meant for PostgreSQL.
# The queries work, though, so we just ignore the warnings
warnings.filterwarnings('ignore',
    "Dialect sqlite\+pysqlite does \*not\* support Decimal objects natively, "
    "and SQLAlchemy must convert from floating point - rounding errors and "
    "other issues may occur. Please consider storing Decimal numbers as "
    "strings or integers on this platform for lossless storage\.",
    SAWarning, r'^sqlalchemy\.sql\.sqltypes$')

extra_descript = {
    'GMOS_NODANDSHUFFLE': 'nodandshuffle',
    'SPECT': 'spectroscopy',
    'OVERSCAN_SUBTRACTED': 'overscan_subtracted',
    'OVERSCAN_TRIMMED': 'overscan_trimmed',
    'PREPARED': 'prepared'
}

args_for_cals = {
    # cal_type      : (method_name, {arg_name: value, ...})
    'processed_arc':  ('arc', {'processed': True}),
    'processed_bias': ('bias', {'processed': True}),
    'processed_dark': ('dark', {'processed': True}),
    'processed_flat': ('flat', {'processed': True})
}

DEFAULT_DB_NAME = 'cal_manager.db'

ERROR_CANT_WIPE = 0
ERROR_CANT_CREATE = 1

FileData = namedtuple('FileData', 'name path')

class LocalManagerError(Exception):
    def __init__(self, error_type, *args, **kw):
        super(LocalManagerError, self).__init__(*args, **kw)
        self.error_type = error_type

class LocalManager(object):
    def __init__(self, db_path):
        if isdir(db_path):
            self._db_path = os.path.join(db_path, DEFAULT_DB_NAME)
        else:
            self._db_path = db_path
        self.session = None
        self._reset()

    @property
    def path(self):
        return self._db_path

    def _reset(self):
        """Modifies the gemini_calmgr setup and reloads some modules that
        are affected by the change. Then it sets a new database session object
        for this instance.
        """

        fsc.storage_root = abspath(dirname(self._db_path))
        fsc.fits_dbname = basename(self._db_path)
        fsc.db_path = self._db_path
        fsc.fits_database = 'sqlite:///' + fsc.db_path

        # The reloading is kludgy, but Fits Storage was not designed to change
        # databases on the fly, and we're reusing its infrastructure.
        #
        # This will have to do for the time being
        reload(orm)
        reload(file)
        reload(preview)
        reload(diskfile)
        reload(createtables)
        reload(ingest)

        self.session = orm.sessionfactory()

    def init_database(self, wipe=True):
        """Initializes a SQLite database with the tables required for the
        calibration manager.

        Parameters
        ----------
        wipe: bool, optional
            If the database exists and this parameter is `True` (default
            value), the file will be removed and recreated before
            initializing.

        Raises
        ------
        IOError
            If the file exists and there a system error when trying to
            remove it (eg. lack of permissions).

        LocalManagerError
            If the file exists and `wipe` was `False`
        """

        if os.path.exists(fsc.db_path):
            if wipe:
                os.remove(fsc.db_path)
            else:
                errmsg = "{!r} exists and won't be wiped".format(fsc.db_path)
                raise LocalManagerError(ERROR_CANT_WIPE, errmsg)

        try:
            createtables.create_tables(self.session)
            self.session.commit()
        except OperationalError:
            message = "There was an error when trying to create the database. Please, check your path and permissions."
            raise LocalManagerError(ERROR_CANT_CREATE, message)

    def ingest_file(self, path):
        """Registers a file into the database

        Parameters
        ----------
        path: string
            Path to the file. It can be either absolute or relative
        """
        directory = abspath(dirname(path))
        filename = basename(path)

        ingest.ingest_file(self.session, filename, directory)

    def ingest_directory(self, path, walk=False, log=None):
        """Registers into the database all FITS files under a directory

        Parameters
        ----------
        path: string, optional
            Path to the root directory. It can be either absolute or
            relative
        walk: bool, optional
            If `False` (default), only the files in the top level of the
            directory will be considered.

            If `True`, all the subdirectories under the path will be
            explored in search of FITS files.
        log: function, optional
            If provided, it must be a function that accepts a single argument,
            a message string. This function can then process the message
            and log it into the proper place.
        """

        for root, dirs, files in os.walk(path):
            for fname in filter(lambda l: l.endswith('.fits'), files):
                self.ingest_file(os.path.join(root, fname))
                if log:
                    log("Ingested {}/{}".format(root, fname))

    def calibration_search(self, rq, fullResult=False):
        """Performs a search in the database using the requested criteria.

        Parameters
        ----------
        rq : dict
            Contains the search criteria, including instrument, descriptors,
            etc.
        fullResult : bool
            This is here just for API compatibility. It's not used anywhere
            in the code, anyway, and should probably be removed altogether.

        Returns
        -------

        result: tuple
            A tuple of exactly two elements.

            In the case of success, the tuple contains two strings, the first
            being the URL to a calibration file, and the second its MD5 sum.

            When an error occurs, the first element in the tuple will be
            `None`, and the second a string describing the error.
        """
        from datetime import datetime

        print "\n@ppu074: calibration_search() ..."

        caltype = rq["caltype"]
        descripts = rq["descriptors"]
        types = rq["types"]

        if "ut_datetime" in descripts:
            utc = descripts["ut_datetime"]
            pyutc = datetime.strptime(utc.value, "%Y%m%dT%H:%M:%S")
            print "@ppu079: OBS UT Date Time:", pyutc
            descripts.update({"ut_datetime":pyutc})

        for (type_, desc) in extra_descript.items():
            descripts[desc] = type_ in types

        nones = [desc for (desc, value) in descripts.items() if value is None]

        # Obtain a calibration manager object instantiated according to the
        # instrument.
        cal_obj = get_cal_object(self.session, filename=None, header=None,
                                 descriptors=descripts, types=types)

        caltypes = gmu.cal_types if caltype == '' else [caltype]
        # The function that downloads an XML returns only the first result,
        # so we won't bother iterating over the whole thing in case that
        # caltype was empty.
        ct = caltypes[0]
        method, args = args_for_cals.get(ct, (ct, {}))
        # Obtain a list of calibrations for the specified cal type
        cals = getattr(cal_obj, method)(**args)

        for cal in cals:
            if cal.diskfile.present:
                path = os.path.join(fsc.storage_root, cal.diskfile.path,
                                    cal.diskfile.file.name)

                return ('file://{}'.format(path), cal.diskfile.data_md5)

        # sent_nones = "No Nones Set" if not nones else ", ".join(nones)
        # preerr = RESPONSESTR % { "sequence": pformat(sequence),
        #                          "response": response.strip(),
        #                          "nones"   : sent_nones }

        # try:
        #     dom = minidom.parseString(response)
        #     calel = dom.getElementsByTagName("calibration")
        #     calurlel = dom.getElementsByTagName('url')[0].childNodes[0]
        #     calurlmd5 = dom.getElementsByTagName('md5')[0].childNodes[0]
        # except IndexError:
        #     print "No url for calibration in response, calibration not found"
        #     return (None, preerr)
        # except:
        #     return (None, preerr)

        #print "prs70:", calurlel.data

        #@@TODO: test only 
        # print "@ppu165: ", repr(calurlel.data)
        # return (calurl, calurlmd5)

    def list_files(self):
        File, DiskFile = file.File, diskfile.DiskFile

        query = self.session.query(File.name, DiskFile.path).join(DiskFile)
        for res in query.order_by(File.name):
            yield FileData(res[0], res[1])