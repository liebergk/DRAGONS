"""
Utility functions for RecipeMapper.

    configure_pkg()   -- returns a PackageConfig object.
    get_config_file() -- looks for a $GEMINIDR env var
    dictify()         -- list of user parameters -> dictionary
    dotpath()         -- build a python import path or GeminiDR packages.

"""
import os
import imp
import sys
import pkgutil

from inspect import isclass
from importlib import import_module

from packageConfig import PackageConfig

# ------------------------------------------------------------------------------
# public functions
#
#     -- retrieve_primtive_set()
#     -- retrieve_recipe()
#
# and supporting generators to introsepctively find primitive classes and recipe
# libraries.

def _package_loader(pkgname):
    pfile, pkgpath, descr = imp.find_module(pkgname)
    loaded_pkg = imp.load_module(pkgname, pfile, pkgpath, descr)
    sys.path.extend(loaded_pkg.__path__)
    return loaded_pkg

# ------------------------------------------------------------------------------
# Recipe hunt cascade

def _generate_context_libs(pkg):
    pkg_importer = pkgutil.ImpImporter(pkg)
    for pkgname, ispkg in pkg_importer.iter_modules():
        if not ispkg:
            yield pkgname, ispkg
        else:
            continue

def _generate_context_pkg(pkg, context):
    pkg_importer = pkgutil.ImpImporter(pkg)
    for pkgname, ispkg in pkg_importer.iter_modules():
        if ispkg and pkgname == context:
            break
        else:
            continue

    loaded_pkg = _package_loader(pkgname)
    for mod, ispkg in _generate_context_libs(loaded_pkg.__path__[0]):
        yield mod, ispkg

def _generate_recipe_modules(pkg, context, recipedir='recipes'):
    pkg_importer = pkgutil.ImpImporter(pkg)
    for pkgname, ispkg in pkg_importer.iter_modules():
        if ispkg and pkgname == recipedir:
            break 
        else:
            continue

    loaded_pkg = _package_loader(pkgname)
    for context_pkg, ispkg in _generate_context_pkg(loaded_pkg.__path__[0],context):
        yield context_pkg, ispkg

def _get_tagged_recipes(pkgname, context):
    loaded_pkg = _package_loader(pkgname)
    for rmod, ispkg in _generate_recipe_modules(loaded_pkg.__path__[0], context):
        if not ispkg:
            yield import_module(rmod)
        else:
            continue

def retrieve_recipe(adtags, pkgname, rname, context):
    """
    Caller passes a recipe name, set of AstroData tags, the instrument package 
    name and a "context". Currently, this is defined as either "QA" or "SQ".

    :parameter rname:  name of requested recipe.
    :type rname:       <str>

    :parameter adtags: set of AstroData tags on an 'ad' instance.
    :type adtags:      <type 'set'>
                       E.g., set(['GMOS', 'SIDEREAL', 'SPECT', 'GMOS_S', 'GEMINI'])

    :parameter pkgname: An instrument package under GeminiDR.
    :type pkgname:     <str>, E.g., "GMOS"

    :parameter context: the context for recipe selection. 
    :type context:      <str> 

    :returns: tuple including the best tag set match and the primitive class
              that provided the match.
    :rtype: <tuple>, (set, class)

    """
    matched_set = (set([]), None)
    for rlib in _get_tagged_recipes(pkgname, context):
        isection = adtags.intersection(rlib.recipe_tags)
        matched_set = (isection, rlib) if isection > matched_set[0] else matched_set

    isection, rlib = matched_set
    if hasattr(rlib, 'recipe_tags'):
        recipe_actual = getattr(rlib, rname)
    return isection, recipe_actual


# ------------------------------------------------------------------------------
# Primtive hunt cascade

def _generate_primitive_modules(pkg):
    pkg_importer = pkgutil.ImpImporter(pkg)
    for pkgname, ispkg in pkg_importer.iter_modules():
        if ispkg:
            continue
        else:
            yield (pkg_importer.path, pkgname)

def _get_tagged_primitives(pkgname):
    loaded_pkg = _package_loader(pkgname)
    for pkgpath, pkg in _generate_primitive_modules(loaded_pkg.__path__[0]):
        fd, path, descr = imp.find_module(pkg, [pkgpath])
        mod = imp.load_module(pkg, fd, path, descr)
        for atrname in dir(mod):
            if atrname.startswith('_'):        # no prive, no magic
                continue
                
            atr = getattr(mod, atrname)
            if isclass(atr) and hasattr(atr, 'tagset'):
                yield atr

def retrieve_primitive_set(adtags, pkgname):
    """
    Caller passes a set of AstroData tags and the instrument package name.

    :parameter adtags: set of AstroData tags on an 'ad' instance.
    :type adtags:      <type 'set'>
                       E.g., set(['GMOS', 'SIDEREAL', 'SPECT', 'SOUTH', 'GEMINI'])

    :parameter pkgname: An instrument package under GeminiDR.
    :type pkgname:     <str>, E.g., "GMOS"

    :returns: tuple including the best tag set match and the primitive class
              that provided the match.
    :rtype: <tuple>, (set, class)

    """
    matched_set = (set([]), None)
    for pclass in _get_tagged_primitives(pkgname):
        isection = adtags.intersection(pclass.tagset)
        matched_set = (isection, pclass) if isection > matched_set[0] else matched_set
    return matched_set

# ------------------------------------------------------------------------------
def configure_pkg():
    cfgfile = get_config_file()
    pkg_conf = PackageConfig()
    pkg_conf.configure_pkg(cfgfile)
    return pkg_conf

def get_config_file():
    """
    Find a GeminiDR package config file, pkg.cfg.
    Examines env var $GEMINIDR.

    """
    config_path = os.environ.get('GEMINIDR')
    default_cfg = 'pkg.cfg'
    config_file = os.path.join(config_path, default_cfg)
    return config_file

def dictify(parset):
    """
    Converts a list of tuples, nominally a set of user parameters passed via
    the 'reduce' command line, into a dictionary directly usable by a primitive
    class.
    
    :parameter parset: A list of user parameters tuples, 
                       e.g., [('foo', 'bar'), ('foobar', 'bat')]
    :type parset: <list>
    
    :returns: A dictionary of those tuples as key=val pairs, 
              e.g., {'foo': 'bar', 'foobar': 'bat'}
    :rtype: <dict>

    """
    pardict = {}
    if parset:
        for pset in parset:
            pardict[pset[0]] = pset[1]
    return pardict

def dotpath(*args):
    """
    Build an import path from args.

    :parameter args: a list of arguments of arbitrary length
    :type args: <list>, implied by *

    :returns: a path to an importable module
    :rtype: <str>

    """
    ppath = ''
    for pkg in args:
        if ppath:
            ppath += os.extsep + pkg
        else:
            ppath += pkg
    ppath.rstrip(os.extsep)
    return ppath
