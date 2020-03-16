# -*- coding: utf-8 -*-
from re import compile as regexpCompile, IGNORECASE, MULTILINE

linesep = "\n"


## @formatter:off ↓
class RE:

    _indentRE        = regexpCompile(r'^(\s*)\S')
    _newlineRE       = regexpCompile(r'^#', MULTILINE)
    _blanklineRE     = regexpCompile(r'^\s*$')
    _docstrMarkerRE  = regexpCompile(r"\s*([uUbB]*[rR]?(['\"]{3}))")
    _docstrOneLineRE = regexpCompile(r"\s*[uUbB]*[rR]?(['\"]{3})(.+)\1")

    _implementsRE = regexpCompile(r"^(\s*)(?:zope\.)?(?:interface\.)?"
                                  r"(?:module|class|directly)?"
                                  r"(?:Provides|Implements)\(\s*(.+)\s*\)",
                                  IGNORECASE) ## zope
    _classRE        = regexpCompile(r"^\s*class\s+(\S+)\s*\((\S+)\):")
    _interfaceRE    = regexpCompile(r"^\s*class\s+(\S+)\s*\(\s*(?:zope\.)?"
                                 r"(?:interface\.)?"
                                 r"Interface\s*\)\s*:", IGNORECASE) ## zope
    _attributeRE    = regexpCompile(r"^(\s*)(\S+)\s*=\s*(?:zope\.)?"
                                 r"(?:interface\.)?"
                                 r"Attribute\s*\(['\"]{1,3}(.*)['\"]{1,3}\)",
                                 IGNORECASE) ## zope

    _singleLineREs  = {
        ' @author: '  : regexpCompile(r"^(\s*Authors?:\s*)(.*)$", IGNORECASE),
        ' @copyright ': regexpCompile(r"^(\s*Copyright:\s*)(.*)$", IGNORECASE),
        ' @date '     : regexpCompile(r"^(\s*Date:\s*)(.*)$", IGNORECASE),
        ' @file '     : regexpCompile(r"^(\s*File:\s*)(.*)$", IGNORECASE),
        ' @version: ' : regexpCompile(r"^(\s*Version:\s*)(.*)$", IGNORECASE),
        ' @note '     : regexpCompile(r"^(\s*Note:\s*)(.*)$", IGNORECASE),
        ' @warning '  : regexpCompile(r"^(\s*Warning:\s*)(.*)$", IGNORECASE)
    }
    _argsStartRE    = regexpCompile(r"^(\s*(?:(?:Keyword\s+)?"
                                 r"(?:A|Kwa)rg(?:ument)?|Attribute)s?"
                                 r"\s*:\s*)$", IGNORECASE)
    _argsRE = regexpCompile(r"^\s*(?P<name>\w+)\s*(?P<type>\(?\S*\)?)?\s*"
                            r"(?:-|:)+\s+(?P<desc>.+)$")
    _returnsStartRE = regexpCompile(r"^\s*(?:Return|Yield)s:\s*$", IGNORECASE)
    _raisesStartRE  = regexpCompile(r"^\s*(Raises|Exceptions|See Also):\s*$",
                                   IGNORECASE)
    _listRE           = regexpCompile(r"^\s*(([\w\.]+),\s*)+(&|and)?\s*([\w\.]+)$")
    _singleListItemRE = regexpCompile(r'^\s*([\w\.]+)\s*$')
    _listItemRE       = regexpCompile(r'([\w\.]+),?\s*')
    _examplesStartRE  = regexpCompile(r"^\s*(?:Example|Doctest)s?:\s*$",
                                     IGNORECASE)
    _sectionStartRE   = regexpCompile(r"^\s*(([A-Z]\w* ?){1,2}):\s*$")
    # The error line should match traceback lines, error exception lines, and
    # (due to a weird behavior of codeop) single word lines.
    _errorLineRE      = regexpCompile(r"^\s*((?:\S+Error|Traceback.*):?\s*(.*)|@?[\w.]+)\s*$",
                                 IGNORECASE)
