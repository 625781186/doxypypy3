#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Filters Python code for use with Doxygen, using a syntax-aware approach.

Rather than implementing a partial Python parser with regular expressions, this
script uses Python's own abstract syntax tree walker to isolate meaningful
constructs.  It passes along namespace information so Doxygen can construct a
proper tree for nested functions, classes, and methods.  It understands bed lump
variables are by convention private.  It groks Zope-style Python interfaces.
It can automatically turn PEP 257 compliant that follow the more restrictive
Google style guide into appropriate Doxygen tags, and is even aware of
doctests.
"""

from ast import NodeVisitor, parse
from types import GeneratorType
from sys import stderr

from string import whitespace
from codeop import compile_command

from .compile import RE, linesep
from .AstVisit import AstVisit


def coroutine(func):
    """Basic decorator to implement the coroutine pattern."""

    def __start(*args, **kwargs):
        """Automatically calls next() on the internal generator function."""
        __cr = func(*args, **kwargs)
        next(__cr)
        return __cr

    return __start


class AstWalker(AstVisit, NodeVisitor, ):
    """
    A walker that'll recursively progress through an AST.

    Given an abstract syntax tree for Python code, walk through all the
    nodes looking for significant types (for our purposes we only care
    about module starts, class definitions, function definitions, variable
    assignments, and function calls, as all the information we want to pass
    to Doxygen is found within these constructs).  If the autobrief option
    is set, it further attempts to parse docstrings to create appropriate
    Doxygen tags.
    """

    # We have a number of regular expressions that we use.  They don't
    # vary across instances and so are compiled directly in the class
    # definition.

    @staticmethod
    def _stripOutAnds(inStr):
        """Takes a string and returns the same without ands or ampersands."""
        assert isinstance(inStr, str)
        return inStr.replace(' and ', ' ').replace(' & ', ' ')

    @staticmethod
    def _endCodeIfNeeded(line, inCodeBlock):
        """Simple routine to append end code marker if needed."""
        assert isinstance(line, str)
        if inCodeBlock:
            line = '# @endcode{0}{1}'.format(linesep, line.rstrip())
            inCodeBlock = False
        return line, inCodeBlock

    @coroutine
    def _checkIfCode(self, inCodeBlock):
        """Checks whether or not a given line appears to be Python code."""
        while True:
            ## @formatter:off ↓
            line    :str
            lines   :list
            lineNum :int

            line, lines, lineNum = (yield)  ## ! return
            testLineNum    = 1
            currentLineNum = 0
            testLine       = line.strip() #type:str
            lineOfCode     = None
            while lineOfCode is None:
                match = RE._errorLineRE.match(testLine)
                if  testLine=="" or testLine == '...' or match:
                    # These are ambiguous.
                    line, lines, lineNum = (yield)    ## ! return
                    testLine = line.strip()
                    # testLineNum = 1
                elif testLine.startswith('>>> '):
                    # This is definitely code.
                    lineOfCode = True
                else:
                    try:
                        compLine = compile_command(testLine)
                        if compLine and lines[currentLineNum].strip().startswith('#'):
                            lineOfCode = True
                        else:
                            line, lines, lineNum = (yield) ## ! return
                            line = line.strip()
                            if line.startswith('>>> '):
                                # Definitely code, don't compile further.
                                lineOfCode = True
                            else:
                                testLine += linesep + line
                                testLine = testLine.strip()
                                testLineNum += 1
                    except (SyntaxError, RuntimeError):
                        # This is definitely not code.
                        lineOfCode = False
                    except Exception:
                        # Other errors are ambiguous.
                        line, lines, lineNum = (yield)  ## ! return
                        testLine = line.strip()
                        # testLineNum = 1
                currentLineNum = lineNum - testLineNum
            if not inCodeBlock and lineOfCode:
                inCodeBlock = True
                lines[currentLineNum] = '{0}{1}# @code{1}'.format(
                    lines[currentLineNum],
                    linesep
                )
            elif inCodeBlock and lineOfCode is False:
                # None is ambiguous, so strict checking
                # against False is necessary.
                inCodeBlock = False
                lines[currentLineNum] = '{0}{1}# @endcode{1}'.format(
                    lines[currentLineNum],
                    linesep
                )

    @coroutine
    def __alterDocstring(self, tail='', writer=None):
        """
        Runs eternally, processing docstring lines.

        Parses docstring lines as they get fed in via send, applies appropriate
        Doxygen tags, and passes them along in batches for writing.
        """
        assert isinstance(tail, str) and isinstance(writer, GeneratorType)

        lines = []
        timeToSend = False
        inCodeBlock = False
        inSection = False
        prefix = ''
        firstLineNum = -1
        sectionHeadingIndent = 0
        codeChecker = self._checkIfCode(False)
        proseChecker = self._checkIfCode(True)
        while True:
            lineNum, line = (yield)
            if firstLineNum < 0:
                firstLineNum = lineNum
            # Don't bother doing extra work if it's a sentinel.
            if line is not None:
                # Also limit work if we're not parsing the docstring.
                if self.options.autobrief:
                    for doxyTag, tagRE in RE._singleLineREs.items():
                        match = tagRE.search(line)
                        if match:
                            # We've got a simple one-line Doxygen command
                            lines[-1], inCodeBlock = self._endCodeIfNeeded(
                                lines[-1], inCodeBlock)
                            writer.send((firstLineNum, lineNum - 1, lines))
                            lines = []
                            firstLineNum = lineNum
                            line = line.replace(match.group(1), doxyTag)
                            timeToSend = True

                    if inSection:
                        # The last line belonged to a section.
                        # Does this one too? (Ignoring empty lines.)
                        match = RE._blanklineRE.match(line)
                        if not match:
                            indent = len(line.expandtabs(self.options.tablength)) - \
                                     len(line.expandtabs(self.options.tablength).lstrip())
                            if indent <= sectionHeadingIndent:
                                inSection = False
                            else:
                                if lines[-1] == '#':
                                    # If the last line was empty, but we're still in a section
                                    # then we need to start a new paragraph.
                                    lines[-1] = '# @par'

                    match = RE._returnsStartRE.match(line)
                    if match:
                        # We've got a "returns" section
                        line = line.replace(match.group(0), ' @return\t').rstrip()
                        prefix = '@return\t'
                    else:
                        match = RE._argsStartRE.match(line)
                        if match:
                            # We've got an "arguments" section
                            line = line.replace(match.group(0), '').rstrip()
                            if 'attr' in match.group(0).lower():
                                prefix = '@property\t'
                            else:
                                prefix = '@param\t'
                            lines[-1], inCodeBlock = self._endCodeIfNeeded(
                                lines[-1], inCodeBlock)
                            lines.append('#' + line)
                            continue
                        else:
                            match = RE._argsRE.match(line)
                            if match and not inCodeBlock:
                                # We've got something that looks like an item /
                                # description pair.
                                if 'property' in prefix:
                                    line = '# {0}\t{1[name]}{2}# {1[desc]}'.format(
                                        prefix, match.groupdict(), linesep)
                                else:
                                    line = ' {0}\t{1[name]}\t{1[desc]}'.format(
                                        prefix, match.groupdict())
                            else:
                                match = RE._raisesStartRE.match(line)
                                if match:
                                    line = line.replace(match.group(0), '').rstrip()
                                    if 'see' in match.group(1).lower():
                                        # We've got a "see also" section
                                        prefix = '@sa\t'
                                    else:
                                        # We've got an "exceptions" section
                                        prefix = '@exception\t'
                                    lines[-1], inCodeBlock = self._endCodeIfNeeded(
                                        lines[-1], inCodeBlock)
                                    lines.append('#' + line)
                                    continue
                                else:
                                    match = RE._listRE.match(line)
                                    if match and not inCodeBlock:
                                        # We've got a list of something or another
                                        itemList = []
                                        for itemMatch in RE._listItemRE.findall(self._stripOutAnds(
                                                match.group(0))):
                                            itemList.append('# {0}\t{1}{2}'.format(
                                                prefix, itemMatch, linesep))
                                        line = ''.join(itemList)[1:]
                                    else:
                                        match = RE._examplesStartRE.match(line)
                                        if match and lines[-1].strip() == '#' \
                                                and self.options.autocode:
                                            # We've got an "example" section
                                            inCodeBlock = True
                                            line = line.replace(match.group(0),
                                                                ' @b Examples{0}# @code'.format(linesep))
                                        else:
                                            match = RE._sectionStartRE.match(line)
                                            if match:
                                                # We've got an arbitrary section
                                                prefix = ''
                                                inSection = True
                                                # What's the indentation of the section heading?
                                                sectionHeadingIndent = len(line.expandtabs(self.options.tablength)) \
                                                                       - len(
                                                    line.expandtabs(self.options.tablength).lstrip())
                                                line = line.replace(
                                                    match.group(0),
                                                    ' @par {0}'.format(match.group(1))
                                                )
                                                if lines[-1] == '# @par':
                                                    lines[-1] = '#'
                                                lines[-1], inCodeBlock = self._endCodeIfNeeded(
                                                    lines[-1], inCodeBlock)
                                                lines.append('#' + line)
                                                continue
                                            elif prefix:
                                                match = RE._singleListItemRE.match(line)
                                                if match and not inCodeBlock:
                                                    # Probably a single list item
                                                    line = ' {0}\t{1}'.format(
                                                        prefix, match.group(0))
                                                elif self.options.autocode and inCodeBlock:
                                                    proseChecker.send(
                                                        (
                                                            line, lines,
                                                            lineNum - firstLineNum
                                                        )
                                                    )
                                                elif self.options.autocode:
                                                    codeChecker.send(
                                                        (
                                                            line, lines,
                                                            lineNum - firstLineNum
                                                        )
                                                    )

                # If we were passed a tail, append it to the docstring.
                # Note that this means that we need a docstring for this
                # item to get documented.
                if tail and lineNum == len(self.docLines) - 1:
                    line = '{0}{1}# {2}'.format(line.rstrip(), linesep, tail)

                # Add comment marker for every line.
                line = '#{0}'.format(line.rstrip())
                # Ensure the first line has the Doxygen double comment.
                if lineNum == 0:
                    line = '#' + line

                lines.append(line.replace(' ' + linesep, linesep))
            else:
                # If we get our sentinel value, send out what we've got.
                timeToSend = True

            if timeToSend:
                lines[-1], inCodeBlock = self._endCodeIfNeeded(lines[-1],
                                                               inCodeBlock)
                writer.send((firstLineNum, lineNum, lines))
                lines = []
                firstLineNum = -1
                timeToSend = False

    @coroutine
    def __writeDocstring(self):
        """
        Runs eternally, dumping out docstring line batches as they get fed in.

        Replaces original batches of docstring lines with modified versions
        fed in via send.
        """
        while True:
            firstLineNum, lastLineNum, lines = (yield)
            newDocstringLen = lastLineNum - firstLineNum + 1
            while len(lines) < newDocstringLen:
                lines.append('')
            # Substitute the new block of lines for the original block of lines.
            self.docLines[firstLineNum: lastLineNum + 1] = lines

    def _processDocstring(self, node, tail='', **kwargs):
        """
        Handles a docstring for functions, classes, and modules.

        Basically just figures out the bounds of the docstring and sends it
        off to the parser to do the actual work.
        """
        typeName = type(node).__name__
        # Modules don't have lineno defined, but it's always 0 for them.
        curLineNum = startLineNum = 0
        if typeName != 'Module':
            startLineNum = curLineNum = node.lineno - 1
        # Figure out where both our enclosing object and our docstring start.
        line = ''
        while curLineNum < len(self.lines):
            line = self.lines[curLineNum]
            match = RE._docstrMarkerRE.match(line)
            if match:
                break
            curLineNum += 1
        docstringStart = curLineNum
        # Figure out where our docstring ends.
        if not RE._docstrOneLineRE.match(line):
            # Skip for the special case of a single-line docstring.
            curLineNum += 1
            while curLineNum < len(self.lines):
                line = self.lines[curLineNum]
                if line.find(match.group(2)) >= 0:
                    break
                curLineNum += 1
        endLineNum = curLineNum + 1

        # Isolate our enclosing object's declaration.
        defLines = self.lines[startLineNum: docstringStart]
        # Isolate our docstring.
        self.docLines = self.lines[docstringStart: endLineNum]

        # If we have a docstring, extract information from it.
        if self.docLines:
            # Get rid of the docstring delineators.
            self.docLines[0] = RE._docstrMarkerRE.sub('',
                                                      self.docLines[0])
            self.docLines[-1] = RE._docstrMarkerRE.sub('',
                                                       self.docLines[-1])
            # Handle special strings within the docstring.
            docstringConverter = self.__alterDocstring(
                tail, self.__writeDocstring())
            for lineInfo in enumerate(self.docLines):
                docstringConverter.send(lineInfo)
            docstringConverter.send((len(self.docLines) - 1, None))

        # Add a Doxygen @brief tag to any single-line description.
        if self.options.autobrief:
            safetyCounter = 0
            while len(self.docLines) > 0 and self.docLines[0].lstrip('#').strip() == '':
                del self.docLines[0]
                self.docLines.append('')
                safetyCounter += 1
                if safetyCounter >= len(self.docLines):
                    # Escape the effectively empty docstring.
                    break
            if len(self.docLines) == 1 or (len(self.docLines) >= 2 and (
                    self.docLines[1].strip(whitespace + '#') == '' or
                    self.docLines[1].strip(whitespace + '#').startswith('@'))):
                self.docLines[0] = "## @brief {0}".format(self.docLines[0].lstrip('#'))
                if len(self.docLines) > 1 and self.docLines[1] == '# @par':
                    self.docLines[1] = '#'

        if defLines:
            match = RE._indentRE.match(defLines[0])
            indentStr = match and match.group(1) or ''
            self.docLines = [RE._newlineRE.sub(indentStr + '#', docLine)
                             for docLine in self.docLines]

        # Taking away a docstring from an interface method definition sometimes
        # leaves broken code as the docstring may be the only code in it.
        # Here we manually insert a pass statement to rectify this problem.
        if typeName != 'Module':
            if docstringStart < len(self.lines):
                match = RE._indentRE.match(self.lines[docstringStart])
                indentStr = match and match.group(1) or ''
            else:
                indentStr = ''
            containingNodes = kwargs.get('containingNodes', []) or []
            fullPathNamespace = self._getFullPathName(containingNodes)
            parentType = fullPathNamespace[-2][1]
            if parentType == 'interface' and typeName == 'FunctionDef' \
                    or fullPathNamespace[-1][1] == 'interface':
                defLines[-1] = '{0}{1}{2}pass'.format(defLines[-1],
                                                      linesep, indentStr)
            elif self.options.autobrief and typeName == 'ClassDef':
                # If we're parsing docstrings separate out class attribute
                # definitions to get better Doxygen output.
                for firstVarLineNum, firstVarLine in enumerate(self.docLines):
                    if '@property\t' in firstVarLine:
                        break
                lastVarLineNum = len(self.docLines)
                if '@property\t' in firstVarLine:
                    while lastVarLineNum > firstVarLineNum:
                        lastVarLineNum -= 1
                        if '@property\t' in self.docLines[lastVarLineNum]:
                            break
                    lastVarLineNum += 1
                    if firstVarLineNum < len(self.docLines):
                        indentLineNum = endLineNum
                        indentStr = ''
                        while not indentStr and indentLineNum < len(self.lines):
                            match = RE._indentRE.match(self.lines[indentLineNum])
                            indentStr = match and match.group(1) or ''
                            indentLineNum += 1
                        varLines = ['{0}{1}'.format(linesep, docLine).replace(
                            linesep, linesep + indentStr)
                            for docLine in self.docLines[
                                           firstVarLineNum: lastVarLineNum]]
                        defLines.extend(varLines)
                        self.docLines[firstVarLineNum: lastVarLineNum] = []
                        # After the property shuffling we will need to relocate
                        # any existing namespace information.
                        namespaceLoc = defLines[-1].find('\n# @namespace')
                        if namespaceLoc >= 0:
                            self.docLines[-1] += defLines[-1][namespaceLoc:]
                            defLines[-1] = defLines[-1][:namespaceLoc]

        # For classes and functions, apply our changes and reverse the
        # order of the declaration and docstring, and for modules just
        # apply our changes.
        if typeName != 'Module':
            self.lines[startLineNum: endLineNum] = self.docLines + defLines
        else:
            self.lines[startLineNum: endLineNum] = defLines + self.docLines

    @staticmethod
    def _checkMemberName(name):
        """
        See if a member name indicates that it should be private.

        Private variables in Python (starting with a double underscore but
        not ending in a double underscore) and bed lumps (variables that
        are not really private but are by common convention treated as
        protected because they begin with a single underscore) get Doxygen
        tags labeling them appropriately.
        """
        assert isinstance(name, str)
        restrictionLevel = None
        if not name.endswith('__'):
            if name.startswith('__'):
                restrictionLevel = 'private'
            elif name.startswith('_'):
                restrictionLevel = 'protected'
        return restrictionLevel

    def _processMembers(self, node, contextTag):
        """
        Mark up members if they should be private.

        If the name indicates it should be private or protected, apply
        the appropriate Doxygen tags.
        """
        restrictionLevel = self._checkMemberName(node.name)
        if restrictionLevel:
            workTag = '{0}{1}# @{2}'.format(contextTag,
                                            linesep,
                                            restrictionLevel)
        else:
            workTag = contextTag
        return workTag

    ############################################################## # ↓
    ## entry
    ############################################################## # ↑
    def parseLines(self):
        """Form an AST for the code and produce a new version of the source."""
        inAst = parse(''.join(self.lines), self.inFilename)
        # Visit all the nodes in our tree and apply Doxygen tags to the source.
        self.visit(inAst)

    ############################################################## # ↓
    ## output
    ############################################################## # ↑
    def getLines(self):
        """Return the modified file once processing has been completed."""
        return linesep.join(line.rstrip() for line in self.lines)


def main():
    """
    Starts the parser on the file given by the filename as the first
    argument on the command line.
    """
    from optparse import OptionParser, OptionGroup
    from os import sep
    from os.path import basename
    from sys import argv, exit as sysExit

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

    # Figure out what is being requested.
    (options, inFilename) = optParse()
    ## ------------------------------
    # Read contents of input file.
    inFile = open(inFilename, encoding="utf8", mode="rU")
    lines = inFile.readlines()
    inFile.close()
    # Create the abstract syntax tree for the input file.
    astWalker = AstWalker(lines, options, inFilename)
    astWalker.parseLines()
    # Output the modified source.
    print(astWalker.getLines())


# See if we're running as a script.
if __name__ == "__main__":
    main()
