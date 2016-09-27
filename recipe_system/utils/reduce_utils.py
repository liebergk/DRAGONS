from argparse import ArgumentParser
from argparse import HelpFormatter

from .reduceActions import PosArgAction
from .reduceActions import BooleanAction 
from .reduceActions import ParameterAction
from .reduceActions import CalibrationAction
from .reduceActions import UnitaryArgumentAction

# ------------------------------------------------------------------------------
class ReduceHelpFormatter(HelpFormatter):
    """
    ReduceHelpFormatter class overrides default help formatting on customized
    reduce actions.

    """
    def _format_args(self, action, default_metavar):
        get_metavar = self._metavar_formatter(action, default_metavar)
        if action.nargs is None:
            result = '%s' % get_metavar(1)
        elif isinstance(action, BooleanAction):
            result = ''
        elif isinstance(action, PosArgAction):
            result = '%s [%s ...]' % get_metavar(2)
        elif isinstance(action, UnitaryArgumentAction):
            result = '%s' % get_metavar(1)
        elif isinstance(action, ParameterAction):
            result = '%s [%s ...]' % get_metavar(2)
        elif isinstance(action, CalibrationAction):
            result = '%s [%s ...]' % get_metavar(2)
        else:
            formats = ['%s' for _ in range(action.nargs)]
            result = ' '.join(formats) % get_metavar(action.nargs)
        return result

# ------------------------------------------------------------------------------
class ReduceArgumentParser(ArgumentParser):
    """
    Converts an argument line from a user param file into an actual argument,
    yields to the calling parser.

    """
    def convert_arg_line_to_args(self, arg_line):
        if not arg_line.startswith("#"):
            for arg in arg_line.split():
                if not arg.strip():
                    continue
                if arg.strip().startswith("#"):
                    break
                yield arg

# ------------------------------------------------------------------------------
def buildParser(version):
    parser = ReduceArgumentParser(description="_"*29 + " Gemini Observatory " + 
                                  "_"*28 + "\n" + "_"*20 + 
                                  " Recipe Processing Management System " + 
                                  "_"*20 + "\n" + "_"*18 + 
                                  " recipeSystem2 Release" + version + "_"*18, 
                                  prog="reduce", 
                                  formatter_class=ReduceHelpFormatter,
                                  fromfile_prefix_chars='@')

    parser.add_argument("-v", "--version", action='version',
                        version='%(prog)s v'+ version)

    parser.add_argument("-d", "--displayflags", dest='displayflags',
                        default=False, nargs='*', action=BooleanAction,
                        help="display all parsed option flags and exit.")

    parser.add_argument('files', metavar='fitsfile', nargs = "*",
                        action=PosArgAction, default=[],
                        help="fitsfile [fitsfile ...] ")

    parser.add_argument("--context", dest="context", default=None,
                        nargs="*", action=UnitaryArgumentAction,
                        help="Use <context> for recipe selection and "
                        " primitives sensitive to context. Eg., --context QA")

    parser.add_argument("--logmode", dest="logmode", default="standard",
                        nargs="*", action=UnitaryArgumentAction,
                        help="Set log mode: 'standard', 'console', 'quiet', "
                        "'debug', or 'null'.")

    parser.add_argument("--logfile", dest="logfile", default="reduce.log",
                        nargs="*", action=UnitaryArgumentAction,
                        help="name of log (default is 'reduce.log')")

    parser.add_argument("--loglevel", dest="loglevel", default="stdinfo", 
                        nargs="*", action=UnitaryArgumentAction,
                        help="Set the verbose level for console "
                        "logging; (critical, error, warning, status, stdinfo, "
                        "fullinfo, debug)")

    parser.add_argument("-p", "--param", dest="userparam", default=None,
                        nargs="*", action=ParameterAction,
                        help="Set a parameter from the command line. The form "
                        "'-p par=val' sets a parameter such that all primitives "
                        "with that defined parameter will 'see' it.  The form: "
                        "'-p primitivename:par=val', sets the parameter only "
                        "for 'primitivename'. Separate par/val pairs by "
                        "whitespace: "
                        "(eg. '-p par1=val1 par2=val2')")

    parser.add_argument("-r", "--recipe", dest="recipename", default=None,
                        nargs="*", action=UnitaryArgumentAction,
                        help="Specify a recipe by name. Users can request "
                        "non-default system recipe functions by their simple "
                        "names, e.g., -r qaStack, OR may specify their own "
                        "recipe file and recipe function. A user defined "
                        "recipe function must be 'dotted' with the recipe file."
                        " E.g., "
                        " '-r /path/to/recipes/recipefile.recipe_function' "
                        "For a recipe file in the current working directory "
                        "(cwd), only the file name is needed, as in, "
                        "'-r recipefile.recipe_function' "
                        "The fact that the recipe function is dotted with the "
                        "recipe file name implies that multiple user defined "
                        "recipe functions can be defined in a single file." )

    parser.add_argument("--user_cal", dest='user_cal', default=None,
                        nargs="*", action=UnitaryArgumentAction,
                        help="Specify user supplied calibrations for "
                        "calibration types. "
                        "Eg., --user_cal processed_arc:gsTest_arc.fits")

    parser.add_argument("--suffix", dest='suffix', default=None,
                        nargs="*", action=UnitaryArgumentAction,
                        help="Add 'suffix' to filenames at end of reduction.")

    return parser

# --------------------------- Emulation functions ------------------------------
# The functions below encapsulate ArgumentParser access to option strings and 
# matches them to 'dest' attributes and attribute values. There is no public 
# interface as with OptionParser.has_option() and OptionParser.get_option() for
# testing and getting option flags.

# The functions
#
#     parser_has_option()
#     get_option_flags()
#
# emulate those methods.
#
#     insert_option_value()  -- assigns an option value to matching 'dest' attr
#     show_parser_options()  -- pretty print options, 'dest' attrs, values.
# ------------------------------------------------------------------------------

def parser_has_option(parser, option):
    return option in parser._option_string_actions

def get_option_flags(parser, option):
    return parser._option_string_actions[option].option_strings

def insert_option_value(parser, args, option, value):
    dest = parser._option_string_actions[option].dest
    setattr(args, dest, value)
    return

def show_parser_options(parser, args):
    all_opts = parser.__dict__['_option_string_actions'].keys()
    handled_flag_set = []
    print "\n\t"+"-"*20+"   switches, vars, vals  "+"-"*20+"\n"
    print "\t  Literals\t\t\tvar 'dest'\t\tValue"
    print "\t", "-"*65
    for opt in all_opts:
        all_option_flags = get_option_flags(parser, opt)
        if opt in handled_flag_set:
            continue
        elif "--help" in all_option_flags:
            continue
        elif "--version" in all_option_flags:
            continue
        else:
            handled_flag_set.extend(all_option_flags)
            dvar = parser.__dict__['_option_string_actions'][opt].__dict__['dest']
            val = args.__dict__[dvar]
            if len(all_option_flags) == 1 and len(dvar) == 3:
                print "\t", all_option_flags, "\t"*3,"::", dvar, "\t\t\t::", val
                continue
            if len(all_option_flags) == 1 and (12 < len(dvar) < 17):
                print "\t", all_option_flags, "\t"*3,"::", dvar, "\t::", val
                continue
            if len(all_option_flags) == 1 and len(all_option_flags[0]) > 24:
                print "\t", all_option_flags, "::", dvar, "\t::", val
                continue
            elif len(all_option_flags) == 1 and len(all_option_flags[0]) < 11:
                print "\t", all_option_flags, "\t"*3+"::", dvar, "\t\t::", val
                continue
            elif len(all_option_flags) == 2 and len(all_option_flags[1]) > 12:
                print "\t", all_option_flags, "\t"+"::", dvar, "\t::", val
                continue
            elif len(all_option_flags) == 2:
                print "\t", all_option_flags, "\t"*2+"::", dvar, "\t\t::", val
                continue
            else: 
                print "\t", all_option_flags, "\t"*2+"::", dvar, "\t\t::", val
    print "\t"+"-"*65+"\n"
    return

# ------------------------------------------------------------------------------
def set_btypes(userparams):
    """
    All cmd line args are delivered as strings. Find any user parameters that 
    should be other python types and set them to those actual corresponding types.

    I.e., 

        'None'  --> None
        'True'  --> True
        'False' --> False

    :parameters userparams: user parameters (if any) passed on the command line.
    :type userparms: <list>

    :returns: A tuple of same parameters with converted None and boolean types.
              preserved with any specified primitive name.
              E.g., [('foo','bar'), ('tileArrays:par1','val1')]
    :rtype:   <list> of tuples.

    """
    upars = []
    if userparams:
        for upar in userparams:
            tmp = upar.split("=")
            spec, val = tmp[0].strip(), tmp[1].strip()
            if val == 'None':
                val = None
            elif val == 'True':
                val = True
            elif val == 'False':
                val = False
            upars.append((spec,val))

    return upars

# ------------------------------------------------------------------------------
def normalize_args(args):
    """
    Convert argparse argument lists to single string values.

    :parameter args: argparse Namespace object or equivalent
    :type args: <Namespace>

    :return:  Same with converted types.
    :rtype: <Namespace>

    """

    if isinstance(args.recipename, list):
        args.recipename = args.recipename[0]
    if isinstance(args.context, list):
        args.context = args.context[0]
    if isinstance(args.loglevel, list):
        args.loglevel = args.loglevel[0]
    if isinstance(args.logmode, list):
        args.logmode = args.logmode[0]
    if isinstance(args.logfile, list):
        args.logfile = args.logfile[0]
    if isinstance(args.suffix, list):
        args.suffix = args.suffix[0]
    return args
