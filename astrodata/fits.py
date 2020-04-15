import gc
import logging
import os
import traceback
from collections import OrderedDict
from copy import deepcopy
from io import BytesIO
from itertools import product as cart_product
from itertools import zip_longest

import numpy as np

import astropy
from astropy import units as u
from astropy.io import fits
from astropy.io.fits import (DELAYED, BinTableHDU, Column, FITS_rec, HDUList,
                             ImageHDU, PrimaryHDU, TableHDU)
# NDDataRef is still not in the stable astropy, but this should be the one
# we use in the future...
# from astropy.nddata import NDData, NDDataRef as NDDataObject
from astropy.table import Table
from gwcs import coordinate_frames as cf
from gwcs.wcs import WCS as gWCS

from . import wcs as adwcs
from .nddata import ADVarianceUncertainty
from .nddata import NDAstroData as NDDataObject
from .utils import normalize_indices

DEFAULT_EXTENSION = 'SCI'
NO_DEFAULT = object()
LOGGER = logging.getLogger(__name__)


class KeywordCallableWrapper:
    def __init__(self, keyword, default=NO_DEFAULT, on_ext=False, coerce_with=None):
        self.kw = keyword
        self.on_ext = on_ext
        self.default = default
        self.coercion_fn = coerce_with if coerce_with is not None else (lambda x: x)

    def __call__(self, adobj):
        def wrapper():
            manip = adobj.phu if not self.on_ext else adobj.hdr
            if self.default is NO_DEFAULT:
                ret = getattr(manip, self.kw)
            else:
                ret = manip.get(self.kw, self.default)
            return self.coercion_fn(ret)
        return wrapper


class FitsHeaderCollection:
    """
    FitsHeaderCollection(headers)

    This class provides group access to a list of PyFITS Header-like objects.
    It exposes a number of methods (`set`, `get`, etc.) that operate over all
    the headers at the same time.

    It can also be iterated.
    """
    def __init__(self, headers):
        self.__headers = list(headers)

    def _insert(self, idx, header):
        self.__headers.insert(idx, header)

    def __iter__(self):
        yield from self.__headers

#    @property
#    def keywords(self):
#        if self._on_ext:
#            return self._ret_ext([set(h.keys()) for h in self.__headers])
#        else:
#            return set(self.__headers[0].keys())
#
#    def show(self):
#        if self._on_ext:
#            for n, header in enumerate(self.__headers):
#                print("==== Header #{} ====".format(n))
#                print(repr(header))
#        else:
#            print(repr(self.__headers[0]))

    def __setitem__(self, key, value):
        if isinstance(value, tuple):
            self.set(key, value=value[0], comment=value[1])
        else:
            self.set(key, value=value)

    def set(self, key, value=None, comment=None):
        for header in self.__headers:
            header.set(key, value=value, comment=comment)

    def __getitem__(self, key):
        raised = False
        missing_at = []
        ret = []
        for n, header in enumerate(self.__headers):
            try:
                ret.append(header[key])
            except KeyError:
                missing_at.append(n)
                ret.append(None)
                raised = True
        if raised:
            error = KeyError("The keyword couldn't be found at headers: {}"
                             .format(tuple(missing_at)))
            error.missing_at = missing_at
            error.values = ret
            raise error
        return ret

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError as err:
            vals = err.values
            for n in err.missing_at:
                vals[n] = default
            return vals

    def __delitem__(self, key):
        self.remove(key)

    def remove(self, key):
        deleted = 0
        for header in self.__headers:
            try:
                del header[key]
                deleted = deleted + 1
            except KeyError:
                pass
        if not deleted:
            raise KeyError("'{}' is not on any of the extensions".format(key))

    def get_comment(self, key):
        return [header.comments[key] for header in self.__headers]

    def set_comment(self, key, comment):
        def _inner_set_comment(header):
            if key not in header:
                raise KeyError("Keyword {!r} not available".format(key))

            header.set(key, comment=comment)

        for n, header in enumerate(self.__headers):
            try:
                _inner_set_comment(header)
            except KeyError as err:
                raise KeyError(err.args[0] + " at header {}".format(n))

    def __contains__(self, key):
        return any(tuple(key in h for h in self.__headers))


def new_imagehdu(data, header, name=None):
    # Assigning data in a delayed way, won't reset BZERO/BSCALE in the header,
    # for some reason. Need to investigated. Maybe astropy.io.fits bug. Figure
    # out WHY were we delaying in the first place.
    #    i = ImageHDU(data=DELAYED, header=header.copy(), name=name)
    #    i.data = data
    return ImageHDU(data=data, header=header.copy(), name=name)


def table_to_bintablehdu(table, extname=None):
    """
    Convert an astropy Table object to a BinTableHDU before writing to disk.

    Parameters
    ----------
    table: astropy.table.Table instance
        the table to be converted to a BinTableHDU
    extname: str
        name to go in the EXTNAME field of the FITS header

    Returns
    -------
    BinTableHDU
    """
    add_header_to_table(table)
    array = table.as_array()
    header = table.meta['header'].copy()
    if extname:
        header['EXTNAME'] = (extname, 'added by AstroData')
    coldefs = []
    for n, name in enumerate(array.dtype.names, 1):
        coldefs.append(Column(
            name   = header.get('TTYPE{}'.format(n)),
            format = header.get('TFORM{}'.format(n)),
            unit   = header.get('TUNIT{}'.format(n)),
            null   = header.get('TNULL{}'.format(n)),
            bscale = header.get('TSCAL{}'.format(n)),
            bzero  = header.get('TZERO{}'.format(n)),
            disp   = header.get('TDISP{}'.format(n)),
            start  = header.get('TBCOL{}'.format(n)),
            dim    = header.get('TDIM{}'.format(n)),
            array  = array[name]
        ))

    return BinTableHDU(data=FITS_rec.from_columns(coldefs), header=header)


header_type_map = {
    'bool': 'L',
    'int8': 'B',
    'int16': 'I',
    'int32': 'J',
    'int64': 'K',
    'uint8': 'B',
    'uint16': 'I',
    'uint32': 'J',
    'uint64': 'K',
    'float32': 'E',
    'float64': 'D',
    'complex64': 'C',
    'complex128': 'M'
}


def header_for_table(table):
    columns = []
    for col in table.itercols():
        descr = {'name': col.name}
        typekind = col.dtype.kind
        typename = col.dtype.name
        if typekind in {'S', 'U'}: # Array of strings
            strlen = col.dtype.itemsize // col.dtype.alignment
            descr['format'] = '{}A'.format(strlen)
            descr['disp'] = 'A{}'.format(strlen)
        elif typekind == 'O': # Variable length array
            raise TypeError("Variable length arrays like in column '{}' are not supported".format(col.name))
        else:
            try:
                typedesc = header_type_map[typename]
            except KeyError:
                raise TypeError("I don't know how to treat type {!r} for column {}".format(col.dtype, col.name))
            repeat = ''
            data = col.data
            shape = data.shape
            if len(shape) > 1:
                repeat = data.size // shape[0]
                if len(shape) > 2:
                    descr['dim'] = shape[1:]
            if typedesc == 'L' and len(shape) > 1:
                # Bit array
                descr['format'] = '{}X'.format(repeat)
            else:
                descr['format'] = '{}{}'.format(repeat, typedesc)
            if col.unit is not None:
                descr['unit'] = str(col.unit)

        columns.append(fits.Column(array=col.data, **descr))

    fits_header = fits.BinTableHDU.from_columns(columns).header
    if 'header' in table.meta:
        fits_header = update_header(table.meta['header'], fits_header)
    return fits_header


def add_header_to_table(table):
    header = header_for_table(table)
    table.meta['header'] = header
    return header


def _process_table(self, table, name=None, header=None):
    if isinstance(table, BinTableHDU):
        obj = Table(table.data, meta={'header': header or table.header})
        for i, col in enumerate(obj.columns, start=1):
            try:
                obj[col].unit = u.Unit(obj.meta['header']['TUNIT{}'.format(i)])
            except (KeyError, TypeError):
                pass
    elif isinstance(table, Table):
        obj = Table(table)
        if header is not None:
            obj.meta['header'] = deepcopy(header)
        elif 'header' not in obj.meta:
            obj.meta['header'] = header_for_table(obj)
    else:
        raise ValueError("{} is not a recognized table type"
                         .format(table.__class__))

    if name is not None:
        obj.meta['header']['EXTNAME'] = name

    return obj


def card_filter(cards, include=None, exclude=None):
    for card in cards:
        if include is not None and card[0] not in include:
            continue
        elif exclude is not None and card[0] in exclude:
            continue
        yield card


def update_header(headera, headerb):
    cardsa = tuple(tuple(cr) for cr in headera.cards)
    cardsb = tuple(tuple(cr) for cr in headerb.cards)

    if cardsa == cardsb:
        return headera

    # Ok, headerb differs somehow. Let's try to bring the changes to
    # headera
    # Updated keywords that should be unique
    difference = set(cardsb) - set(cardsa)
    headera.update(card_filter(difference, exclude={'HISTORY', 'COMMENT', ''}))
    # Check the HISTORY and COMMENT cards, just in case
    for key in ('HISTORY', 'COMMENT'):
        fltcardsa = card_filter(cardsa, include={key})
        fltcardsb = card_filter(cardsb, include={key})
        # assume we start with two headers that are mostly the same and
        # that will have added comments/history at the end (in headerb)
        for (ca, cb) in zip_longest(fltcardsa, fltcardsb):
            if ca is None:
                headera.update((cb,))

    return headera


class FitsProviderProxy:

    def __getattr__(self, attribute):
        if not attribute.startswith('_'):
            try:
                # Check first if this is something we can get from the main object
                # But only if it's not an internal attribute
                try:
                    return self._provider._getattr_impl(attribute, self._mapped_nddata())
                except AttributeError:
                    # Not a special attribute. Check the regular interface
                    return getattr(self._provider, attribute)
            except AttributeError:
                pass
        # Not found in the real Provider. Ok, if we're working with single
        # slices, let's look some things up in the ND object
        if self.is_single:
            if attribute.isupper():
                try:
                    return self._mapped_nddata(0).meta['other'][attribute]
                except KeyError:
                    # Not found. Will raise an exception...
                    pass
        raise AttributeError("{} not found in this object".format(attribute))

    def __setattr__(self, attribute, value):
        def _my_attribute(attr):
            return attr in self.__dict__ or attr in self.__class__.__dict__

        # This method is meant to let the user set certain attributes of the NDData
        # objects. First we check if the attribute belongs to this object's dictionary.
        # Otherwise, see if we can pass it down.

        if not _my_attribute(attribute) and self._provider.is_settable(attribute):
            if attribute.isupper():
                if not self.is_single:
                    raise TypeError("This attribute can only be assigned to a single-slice object")
                target = self._mapped_nddata(0)
                self._provider.append(value, name=attribute, add_to=target)
                return
            elif attribute in {'path', 'filename'}:
                # FIXME: never reached because path/filename are not settable
                raise AttributeError("Can't set path or filename on a sliced object")
            else:
                setattr(self._provider, attribute, value)

        super().__setattr__(attribute, value)

    def __delattr__(self, attribute):
        if not attribute.isupper():
            raise ValueError("Can't delete non-capitalized attributes from slices")
        if not self.is_single:
            raise TypeError("Can't delete attributes on non-single slices")
        other, otherh = self.nddata.meta['other'], self.nddata.meta['other_header']
        if attribute in other:
            del other[attribute]
            if attribute in otherh:
                del otherh[attribute]
        else:
            raise AttributeError("'{}' does not exist in this extension".format(attribute))

    @property
    def exposed(self):
        return self._provider._exposed.copy() | set(self._mapped_nddata(0).meta['other'])

    def __iter__(self):
        if self._single:
            yield self
        else:
            for n in self._mapping:
                yield self._provider._slice((n,), multi=False)

    def __getitem__(self, slc):
        if self.is_single:
            raise TypeError("Can't slice a single slice!")

        indices, multiple = normalize_indices(slc, nitems=len(self))
        mapped_indices = tuple(self._mapping[idx] for idx in indices)
        return self._provider._slice(mapped_indices, multi=multiple)

    def __delitem__(self, idx):
        raise TypeError("Can't remove items from a sliced object")

    def __rtruediv__(self, operand):
        self._provider._oper(self._provider._rdiv, operand, self._mapping)
        return self

    def _crop_nd(self, nd, x1, y1, x2, y2):
        # needed because __getattr__ breaks finding private methods in the
        # parent class...
        self._provider._crop_nd(nd, x1, y1, x2, y2)

    def _crop_impl(self, x1, y1, x2, y2, nds=None):
        # needed because __getattr__ breaks finding private methods in the
        # parent class...
        self._provider._crop_impl(x1, y1, x2, y2, nds=nds)

    def crop(self, x1, y1, x2, y2):
        self._crop_impl(x1, y1, x2, y2, self._mapped_nddata())


class FitsProvider:

    default_extension = 'SCI'

    def _getattr_impl(self, attribute, nds):
        # Exposed objects are part of the normal object interface. We may have
        # just lazy-loaded them, and that's why we get here...
        if attribute in self._exposed:
            return getattr(self, attribute)

        # Check if it's an aliased object
        for nd in nds:
            if nd.meta.get('name') == attribute:
                return nd

        raise AttributeError("Not found")

    def __getattr__(self, attribute):
        try:
            return self._getattr_impl(attribute, self._nddata)
        except AttributeError:
            raise AttributeError("{} not found in this object, or available only for sliced data".format(attribute))

    def __setattr__(self, attribute, value):
        def _my_attribute(attr):
            return attr in self.__dict__ or attr in self.__class__.__dict__

        # This method is meant to let the user set certain attributes of the NDData
        # objects.
        #
        # self._resetting shortcircuits the method when populating the object. In that
        # situation, we don't want to interfere. Of course, we need to check first
        # if self._resetting is there, because otherwise we enter a loop..
        # CJS 20200131: if the attribute is "exposed" then we should set it via the
        # append method I think (it's a Table or something)
        if ('_resetting' in self.__dict__ and not self._resetting and
                (not _my_attribute(attribute) or attribute in self._exposed)):
            if attribute.isupper():
                self.append(value, name=attribute, add_to=None)
                return

        # Fallback
        super().__setattr__(attribute, value)

    def __delattr__(self, attribute):
        # TODO: So far we're only deleting tables by name.
        #       Figure out what to do with aliases
        if not attribute.isupper():
            raise ValueError("Can't delete non-capitalized attributes")
        try:
            del self._tables[attribute]
            del self.__dict__[attribute]
        except KeyError:
            raise AttributeError("'{}' is not a global table for this instance".format(attribute))

    def _slice(self, indices, multi=True):
        return FitsProviderProxy(self, indices, single=not multi)

    def __getitem__(self, slc):
        nitems = len(self._nddata)
        indices, multiple = normalize_indices(slc, nitems=nitems)
        return self._slice(indices, multi=multiple)

    def __delitem__(self, idx):
        del self._nddata[idx]

    def _crop_nd(self, nd, x1, y1, x2, y2):
        nd.data = nd.data[y1:y2+1, x1:x2+1]
        if nd.uncertainty is not None:
            nd.uncertainty = nd.uncertainty[y1:y2+1, x1:x2+1]
        if nd.mask is not None:
            nd.mask = nd.mask[y1:y2+1, x1:x2+1]

    def _crop_impl(self, x1, y1, x2, y2, nds=None):
        if nds is None:
            nds = self.nddata
        # TODO: Consider cropping of objects in the meta section
        for nd in nds:
            orig_shape = nd.data.shape
            self._crop_nd(nd, x1, y1, x2, y2)
            for o in nd.meta['other'].values():
                try:
                    if o.shape == orig_shape:
                        self._crop_nd(o, x1, y1, x2, y2)
                except AttributeError:
                    # No 'shape' attribute in the object. It's probably
                    # not array-like
                    pass

    def crop(self, x1, y1, x2, y2):
        self._crop_impl(x1, y1, x2, y2)


def fits_ext_comp_key(ext):
    """
    Returns a pair (integer, string) that will be used to sort extensions
    """
    if isinstance(ext, PrimaryHDU):
        # This will guarantee that the primary HDU goes first
        ret = (-1, "")
    else:
        header = ext.header
        ver = header.get('EXTVER')

        # When two extensions share version number, we'll use their names
        # to sort them out. Choose a suitable key so that:
        #
        #  - SCI extensions come first
        #  - unnamed extensions come last
        #
        # We'll resort to add 'z' in front of the usual name to force
        # SCI to be the "smallest"
        name = header.get('EXTNAME')  # Make sure that the name is a string
        if name is None:
            name = "zzzz"
        elif name != FitsProvider.default_extension:
            name = "z" + name

        if ver in (-1, None):
            # In practice, this number should be larger than any
            # EXTVER found in real life HDUs, pushing unnumbered
            # HDUs to the end
            ret = (2**32-1, name)
        else:
            # For the general case, just return version and name, to let them
            # be sorted naturally
            ret = (ver, name)

    return ret


class FitsLazyLoadable:

    def __init__(self, obj):
        self._obj = obj
        self.lazy = True

    def _create_result(self, shape):
        return np.empty(shape, dtype=self.dtype)

    def _scale(self, data):
        bscale = self._obj._orig_bscale
        bzero = self._obj._orig_bzero
        if bscale == 1 and bzero == 0:
            return data
        return (bscale * data + bzero).astype(self.dtype)

    def __getitem__(self, sl):
        # TODO: We may want (read: should) create an empty result array before scaling
        return self._scale(self._obj.section[sl])

    @property
    def header(self):
        return self._obj.header

    @property
    def data(self):
        res = self._create_result(self.shape)
        res[:] = self._scale(self._obj.data)
        return res

    @property
    def shape(self):
        return self._obj.shape

    @property
    def dtype(self):
        """
        Need to to some overriding of astropy.io.fits since it doesn't
        know about BITPIX=8
        """
        bitpix = self._obj._orig_bitpix
        if self._obj._orig_bscale == 1 and self._obj._orig_bzero == 0:
            dtype = fits.BITPIX2DTYPE[bitpix]
        else:
            # this method from astropy will return the dtype if the data
            # needs to be converted to unsigned int or scaled to float
            dtype = self._obj._dtype_for_bitpix()

        if dtype is None:
            if bitpix < 0:
                dtype = np.dtype('float{}'.format(abs(bitpix)))
        if (self._obj.header['EXTNAME'] == 'DQ' or self._obj._uint and
                self._obj._orig_bscale == 1 and bitpix == 8):
            dtype = np.uint16
        return dtype


def _prepare_hdulist(hdulist, default_extension='SCI', extname_parser=None):
    new_list = []
    highest_ver = 0
    recognized = set()

    if len(hdulist) > 1 or (len(hdulist) == 1 and hdulist[0].data is None):
        # MEF file
        for n, unit in enumerate(hdulist):
            if extname_parser:
                extname_parser(unit)
            ev = unit.header.get('EXTVER')
            eh = unit.header.get('EXTNAME')
            if ev not in (-1, None) and eh is not None:
                highest_ver = max(highest_ver, unit.header['EXTVER'])
            elif not isinstance(unit, PrimaryHDU):
                continue

            new_list.append(unit)
            recognized.add(unit)

        for unit in hdulist:
            if unit in recognized:
                continue
            elif isinstance(unit, ImageHDU):
                highest_ver += 1
                if 'EXTNAME' not in unit.header:
                    unit.header['EXTNAME'] = (default_extension, 'Added by AstroData')
                if unit.header.get('EXTVER') in (-1, None):
                    unit.header['EXTVER'] = (highest_ver, 'Added by AstroData')

            new_list.append(unit)
            recognized.add(unit)
    else:
        # Uh-oh, a single image FITS file
        new_list.append(PrimaryHDU(header=hdulist[0].header))
        image = ImageHDU(header=hdulist[0].header, data=hdulist[0].data)
        # Fudge due to apparent issues with assigning ImageHDU from data
        image._orig_bscale = hdulist[0]._orig_bscale
        image._orig_bzero = hdulist[0]._orig_bzero

        for keyw in ('SIMPLE', 'EXTEND'):
            if keyw in image.header:
                del image.header[keyw]
        image.header['EXTNAME'] = (default_extension, 'Added by AstroData')
        image.header['EXTVER'] = (1, 'Added by AstroData')
        new_list.append(image)

    return HDUList(sorted(new_list, key=fits_ext_comp_key))


def read_fits(cls, source, extname_parser=None):
    """
    Takes either a string (with the path to a file) or an HDUList as input, and
    tries to return a populated FitsProvider (or descendant) instance.

    It will raise exceptions if the file is not found, or if there is no match
    for the HDUList, among the registered AstroData classes.
    """

    ad = cls()

    if isinstance(source, str):
        hdulist = fits.open(source, memmap=True,
                            do_not_scale_image_data=True, mode='readonly')
        ad.path = source
    else:
        hdulist = source
        try:
            ad.path = source[0].header.get('ORIGNAME')
        except AttributeError:
            ad.path = None

    _file = hdulist._file
    hdulist = _prepare_hdulist(hdulist, default_extension=DEFAULT_EXTENSION,
                               extname_parser=extname_parser)
    if _file is not None:
        hdulist._file = _file

    # Initialize the object containers to a bare minimum
    if 'ORIGNAME' not in hdulist[0].header and ad.orig_filename is not None:
        hdulist[0].header.set('ORIGNAME', ad.orig_filename,
                              'Original filename prior to processing')
    ad.set_phu(hdulist[0].header)

    seen = {hdulist[0]}

    skip_names = {DEFAULT_EXTENSION, 'REFCAT', 'MDF'}

    def associated_extensions(ver):
        for unit in hdulist:
            header = unit.header
            if header.get('EXTVER') == ver and header['EXTNAME'] not in skip_names:
                yield unit

    sci_units = [x for x in hdulist[1:]
                 if x.header.get('EXTNAME') == DEFAULT_EXTENSION]

    for idx, unit in enumerate(sci_units):
        seen.add(unit)
        ver = unit.header.get('EXTVER', -1)
        parts = {
            'data': unit,
            'uncertainty': None,
            'mask': None,
            'wcs': None,
            'other': [],
        }

        for extra_unit in associated_extensions(ver):
            seen.add(extra_unit)
            name = extra_unit.header.get('EXTNAME')
            if name == 'DQ':
                parts['mask'] = extra_unit
            elif name == 'VAR':
                parts['uncertainty'] = extra_unit
            elif name == 'WCS':
                parts['wcs'] = extra_unit
            else:
                parts['other'].append(extra_unit)

        if hdulist._file is not None and hdulist._file.memmap:
            nd = NDDataObject(
                    data=FitsLazyLoadable(parts['data']),
                    uncertainty=(None if parts['uncertainty'] is None
                                 else FitsLazyLoadable(parts['uncertainty'])),
                    mask=(None if parts['mask'] is None
                          else FitsLazyLoadable(parts['mask'])),
                    wcs=(None if parts['wcs'] is None
                         else asdftablehdu_to_wcs(parts['wcs'])),
                    )
            if nd.wcs is None:
                try:
                    nd.wcs = adwcs.fitswcs_to_gwcs(nd.meta['header'])
                    # In case WCS info is in the PHU
                    if nd.wcs is None:
                        nd.wcs = adwcs.fitswcs_to_gwcs(hdulist[0].header)
                except TypeError as e:
                    raise e
            ad.append(nd, name=DEFAULT_EXTENSION, reset_ver=False)
        else:
            nd = ad.append(parts['data'], name=DEFAULT_EXTENSION,
                           reset_ver=False)
            for item_name in ('mask', 'uncertainty'):
                item = parts[item_name]
                if item is not None:
                    ad.append(item, name=item.header['EXTNAME'], add_to=nd)
            if isinstance(nd, NDData):
                if parts['wcs'] is not None:
                    nd.wcs = asdftablehdu_to_wcs(parts['wcs'])
                else:
                    try:
                        nd.wcs = adwcs.fitswcs_to_gwcs(nd.meta['header'])
                    except TypeError:
                        pass

        for other in parts['other']:
            ad.append(other, name=other.header['EXTNAME'], add_to=nd)

    for other in hdulist:
        if other in seen:
            continue
        name = other.header.get('EXTNAME')
        try:
            ad.append(other, name=name, reset_ver=False)
        except ValueError as e:
            print(str(e)+". Discarding "+name)

    return ad


def write_fits(ad, filename, overwrite=False):
    hdul = HDUList()
    hdul.append(PrimaryHDU(header=ad.phu(), data=DELAYED))

    for ext in ad._nddata:
        meta = ext.meta
        header, ver = meta['header'], meta['ver']
        wcs = ext.wcs

        if isinstance(wcs, gWCS):
            # We don't have access to the AD tags so see if it's an image
            # Catch ValueError as any sort of failure
            try:
                wcs_dict = adwcs.gwcs_to_fits(ext, ad.phu())
            except (ValueError, NotImplementedError) as e:
                LOGGER.warning(e)
            else:
                # HACK! Don't update the FITS WCS for an image
                # Must delete keywords if image WCS has been downscaled
                # from a higher number of dimensions
                for i in range(1, 5):
                    for kw in (f'CDELT{i}', f'CRVAL{i}', f'CUNIT{i}', f'CTYPE{i}'):
                        if kw in header:
                            del header[kw]
                    for j in range(1, 5):
                        for kw in (f'CD{i}_{j}', f'PC{i}_{j}', f'CRPIX{j}'):
                            if kw in header:
                                del header[kw]
                header.update(wcs_dict)
                # Use "in" here as the dict entry may be (value, comment)
                if 'APPROXIMATE' not in wcs_dict.get('FITS-WCS', ''):
                    wcs = None  # There's no need to create a WCS extension

        hdul.append(new_imagehdu(ext.data, header))
        if ext.uncertainty is not None:
            hdul.append(new_imagehdu(ext.uncertainty.array, header, 'VAR'))
        if ext.mask is not None:
            hdul.append(new_imagehdu(ext.mask, header, 'DQ'))

        if isinstance(wcs, gWCS):
            hdul.append(wcs_to_asdftablehdu(ext.wcs, extver=ver))

        for name, other in meta.get('other', {}).items():
            if isinstance(other, Table):
                hdul.append(table_to_bintablehdu(other))
            elif isinstance(other, np.ndarray):
                header = meta['other_header'].get(name, meta['header'])
                hdul.append(new_imagehdu(other, header, name=name))
            elif isinstance(other, NDDataObject):
                hdul.append(new_imagehdu(other.data, meta['header']))
            else:
                raise ValueError("I don't know how to write back an object "
                                 "of type {}".format(type(other)))

    if ad._tables is not None:
        for name, table in sorted(ad._tables.items()):
            hdul.append(table_to_bintablehdu(table, extname=name))

    hdul.writeto(filename, overwrite=overwrite)


def windowedOp(func, sequence, kernel, shape=None, dtype=None,
               with_uncertainty=False, with_mask=False, **kwargs):
    """Apply function on a NDData obbjects, splitting the data in chunks to
    limit memory usage.

    Parameters
    ----------
    func : callable
        The function to apply.
    sequence : list of NDData
        List of NDData objects.
    kernel : tuple of int
        Shape of the blocks.
    shape : tuple of int
        Shape of inputs. Defaults to ``sequence[0].shape``.
    dtype : str or dtype
        Type of the output array. Defaults to ``sequence[0].dtype``.
    with_uncertainty : bool
        Compute uncertainty?
    with_mask : bool
        Compute mask?
    **kwargs
        Additional args are passed to ``func``.

    """

    def generate_boxes(shape, kernel):
        if len(shape) != len(kernel):
            raise AssertionError("Incompatible shape ({}) and kernel ({})"
                                 .format(shape, kernel))
        ticks = [[(x, x+step) for x in range(0, axis, step)]
                 for axis, step in zip(shape, kernel)]
        return list(cart_product(*ticks))

    if shape is None:
        if len({x.shape for x in sequence}) > 1:
            raise ValueError("Can't calculate final shape: sequence elements "
                             "disagree on shape, and none was provided")
        shape = sequence[0].shape

    if dtype is None:
        dtype = sequence[0].window[:1, :1].data.dtype

    result = NDDataObject(
        np.empty(shape, dtype=dtype),
        uncertainty=(ADVarianceUncertainty(np.zeros(shape, dtype=dtype))
                     if with_uncertainty else None),
        mask=(np.empty(shape, dtype=np.uint16) if with_mask else None),
        meta=sequence[0].meta, wcs=sequence[0].wcs
    )
    # Delete other extensions because we don't know what to do with them
    result.meta['other'] = OrderedDict()
    result.meta['other_header'] = {}

    # The Astropy logger's "INFO" messages aren't warnings, so have to fudge
    log_level = astropy.logger.conf.log_level
    astropy.log.setLevel(astropy.logger.WARNING)

    boxes = generate_boxes(shape, kernel)

    try:
        for coords in boxes:
            section = tuple([slice(start, end) for (start, end) in coords])
            out = func([element.window[section] for element in sequence],
                       **kwargs)
            result.set_section(section, out)

            # propagate additional attributes
            if out.meta.get('other'):
                for k, v in out.meta['other'].items():
                    if len(boxes) > 1:
                        result.meta['other'][k, coords] = v
                    else:
                        result.meta['other'][k] = v

            gc.collect()
    finally:
        astropy.log.setLevel(log_level)  # and reset

    # Now if the input arrays where splitted in chunks, we need to gather
    # the data arrays for the additional attributes.
    other = result.meta['other']
    if other:
        if len(boxes) > 1:
            for (name, coords), obj in list(other.items()):
                if not isinstance(obj, NDData):
                    raise ValueError('only NDData objects are handled here')
                if name not in other:
                    other[name] = NDDataObject(np.empty(shape,
                                                        dtype=obj.data.dtype))
                section = tuple([slice(start, end) for (start, end) in coords])
                other[name].set_section(section, obj)
                del other[name, coords]

        for name in other:
            # To set the name of our object we need to save it as an ndarray,
            # otherwise for a NDData one AstroData would use the name of the
            # AstroData object.
            other[name] = other[name].data
            result.meta['other_header'][name] = fits.Header({'EXTNAME': name})

    return result


# ---------------------------------------------------------------------------
# gWCS <-> FITS WCS helper functions go here
# ---------------------------------------------------------------------------
# Could parametrize some naming conventions in the following two functions if
# done elsewhere for hard-coded names like 'SCI' in future, but they only have
# to be self-consistent with one another anyway.

def wcs_to_asdftablehdu(wcs, extver=None):
    """
    Serialize a gWCS object as a FITS TableHDU (ASCII) extension.

    The ASCII table is actually a mini ASDF file. The constituent AstroPy
    models must have associated ASDF "tags" that specify how to serialize them.

    In the event that serialization as pure ASCII fails (this should not
    happen), a binary table representation will be used as a fallback.
    """

    import asdf
    import jsonschema

    # Create a small ASDF file in memory containing the WCS object
    # representation because there's no public API for generating only the
    # relevant YAML subsection and an ASDF file handles the "tags" properly.
    try:
        af = asdf.AsdfFile({"wcs" : wcs})
    except jsonschema.exceptions.ValidationError:
        # (The original traceback also gets printed here)
        raise TypeError("Cannot serialize model(s) for 'WCS' extension {}"\
                        .format(extver or ''))

    # ASDF can only dump YAML to a binary file object, so do that and read
    # the contents back from it for storage in a FITS extension:
    with BytesIO() as fd:
        with af:
            # Generate the YAML, dumping any binary arrays as text:
            af.write_to(fd, all_array_storage='inline')
        fd.seek(0)
        wcsbuf = fd.read()

    # Convert the bytes to readable lines of text for storage (falling back to
    # saving as binary in the unexpected event that this is not possible):
    try:
        wcsbuf = wcsbuf.decode('ascii').splitlines()
    except UnicodeDecodeError:
        # This should not happen, but if the ASDF contains binary data in
        # spite of the 'inline' option above, we have to dump the bytes to
        # a non-human-readable binary table rather than an ASCII one:
        LOGGER.warning("Could not convert WCS {} ASDF to ASCII; saving table "
                       "as binary".format(extver or ''))
        hduclass = BinTableHDU
        fmt = 'B'
        wcsbuf = np.frombuffer(wcsbuf, dtype=np.uint8)
    else:
        hduclass = TableHDU
        fmt = 'A{0}'.format(max(len(line) for line in wcsbuf))

    # Construct the FITS table extension:
    col = Column(name='gWCS', format=fmt, array=wcsbuf,
                 ascii= hduclass is TableHDU)
    hdu = hduclass.from_columns([col], name='WCS', ver=extver)

    return hdu

def asdftablehdu_to_wcs(hdu):
    """
    Recreate a gWCS object from its serialization in a FITS table extension.

    Returns None (issuing a warning) if the extension cannot be parsed, so
    the rest of the file can still be read.
    """

    import asdf

    ver = hdu.header.get('EXTVER', -1)

    if isinstance(hdu, (TableHDU, BinTableHDU)):
        try:
            colarr = hdu.data['gWCS']
        except KeyError:
            LOGGER.warning("Ignoring 'WCS' extension {} with no 'gWCS' table "
                           "column".format(ver))
            return

        # If this table column contains text strings as expected, join the rows
        # as separate lines of a string buffer and encode the resulting YAML as
        # bytes that ASDF can parse. If AstroData has produced another format,
        # it will be a binary dump due to the unexpected presence of non-ASCII
        # data, in which case we just extract unmodified bytes from the table.
        if colarr.dtype.kind in ('U', 'S'):
            sep = os.linesep
            # Just in case io.fits ever produces 'S' on Py 3 (not the default):
            # join lines as str & avoid a TypeError with unicode linesep; could
            # also use astype('U') but it assumes an encoding implicitly.
            if colarr.dtype.kind == 'S' and not isinstance(sep, bytes):
                colarr = np.char.decode(np.char.rstrip(colarr),
                                        encoding='ascii')
            wcsbuf = sep.join(colarr).encode('ascii')
        else:
            wcsbuf = colarr.tobytes()

        # Convert the stored text to a Bytes file object that ASDF can open:
        with BytesIO(wcsbuf) as fd:

            # Try to extract a 'wcs' entry from the YAML:
            try:
                af = asdf.open(fd)
            except:
                LOGGER.warning("Ignoring 'WCS' extension {}: failed to parse "
                               "ASDF.\nError was as follows:\n{}"\
                               .format(ver, traceback.format_exc()))
                return
            else:
                with af:
                    try:
                        wcs = af.tree['wcs']
                    except KeyError:
                        LOGGER.warning("Ignoring 'WCS' extension {}: missing "
                                       "'wcs' dict entry.".format(ver))
                        return

    else:
        LOGGER.warning("Ignoring non-FITS-table 'WCS' extension {}"\
                       .format(ver))
        return

    return wcs
