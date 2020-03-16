# coding=utf-8
from optparse import OptionParser, OptionGroup
from os import sep
from os.path import basename
from sys import argv, exit as sysExit
from sys import stderr

linesep = "\n"


def optParse():
    """
    Parses command line options.

    Generally we're supporting all the command line options that doxypy.py
    supports in an analogous way to make it easy to switch back and forth.
    We additionally support a top-level namespace argument that is used
    to trim away excess path information.
    """

    parser = OptionParser(prog=basename(argv[0]))

    parser.set_usage("%prog [options] filename")
    parser.add_option(
        "-a", "--autobrief",
        action="store_true", dest="autobrief",
        help="parse the docstring for @brief description and other information"
    )
    parser.add_option(
        "-c", "--autocode",
        action="store_true", dest="autocode",
        help="parse the docstring for code samples"
    )
    parser.add_option(
        "-n", "--ns",
        action="store", type="string", dest="topLevelNamespace",
        help="specify a top-level namespace that will be used to trim paths"
    )
    parser.add_option(
        "-t", "--tablength",
        action="store", type="int", dest="tablength", default=4,
        help="specify a tab length in spaces; only needed if tabs are used"
    )
    group = OptionGroup(parser, "Debug Options")
    group.add_option(
        "-d", "--debug",
        action="store_true", dest="debug",
        help="enable debug output on stderr"
    )
    parser.add_option_group(group)

    ## Parse options based on our definition.
    (options, filename) = parser.parse_args()

    # Just abort immediately if we are don't have an input file.
    if not filename:
        stderr.write("No filename given." + linesep)
        sysExit(-1)

    # Turn the full path filename into a full path module location.
    fullPathNamespace = filename[0].replace(sep, '.')[:-3]
    # Use any provided top-level namespace argument to trim off excess.
    realNamespace = fullPathNamespace
    if options.topLevelNamespace:
        namespaceStart = fullPathNamespace.find(options.topLevelNamespace)
        if namespaceStart >= 0:
            realNamespace = fullPathNamespace[namespaceStart:]
    options.fullPathNamespace = realNamespace

    return options, filename[0]
