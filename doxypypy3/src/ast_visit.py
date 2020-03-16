# coding=utf-8

from ast import iter_fields, AST, Name, get_docstring

from icecream import ic

from .compile import RE, linesep


class AstVisit:
    def __init__(self, lines:list, options, inFilename:str):
        """Initialize a few class variables in preparation for our walk."""
        self.lines = lines
        self.options = options
        self.inFilename = inFilename
        self.docLines = []

        ic.configureOutput(includeContext=True)
        ic.enable() if self.options.debug else ic.disable()


    def generic_visit(self, node, **kwargs):
        """
        Extract useful information from relevant nodes including docstrings.

        This is virtually identical to the standard version contained in
        NodeVisitor.  It is only overridden because we're tracking extra
        information (the hierarchy of containing nodes) not preserved in
        the original.
        """
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        self.visit(item, containingNodes=kwargs['containingNodes'])
            elif isinstance(value, AST):
                self.visit(value, containingNodes=kwargs['containingNodes'])

    def visit(self, node, **kwargs):
        """
        Visit a node and extract useful information from it.

        This is virtually identical to the standard version contained in
        NodeVisitor.  It is only overridden because we're tracking extra
        information (the hierarchy of containing nodes) not preserved in
        the original.
        """
        containingNodes = kwargs.get('containingNodes', [])
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, containingNodes=containingNodes)

    def _getFullPathName(self, containingNodes):
        """
        Returns the full node hierarchy rooted at module name.

        The list representing the full path through containing nodes
        (starting with the module itself) is returned.
        """
        assert isinstance(containingNodes, list)
        return [(self.options.fullPathNamespace, 'module')] + containingNodes

    def visit_Module(self, node, **kwargs):
        """
        Handles the module-level docstring.

        Process the module-level docstring and create appropriate Doxygen tags
        if autobrief option is set.
        """

        ic("# Module {0}{1}".format(self.options.fullPathNamespace, linesep))
        if get_docstring(node):
            self._processDocstring(node)
        # Visit any contained nodes (in this case pretty much everything).
        self.generic_visit(node, containingNodes=kwargs.get('containingNodes',
                                                            []))

    def visit_Assign(self, node, **kwargs):
        """
        Handles assignments within code.

        Variable assignments in Python are used to represent interface
        attributes in addition to basic variables.  If an assignment appears
        to be an attribute, it gets labeled as such for Doxygen.  If a variable
        name uses Python mangling or is just a bed lump, it is labeled as
        private for Doxygen.
        """
        lineNum = node.lineno - 1
        # Assignments have one Doxygen-significant special case:
        # interface attributes.
        match = RE._attributeRE.match(self.lines[lineNum])
        if match:
            self.lines[lineNum] = '{0}## @property {1}{2}{0}# {3}{2}' \
                                  '{0}# @hideinitializer{2}{4}{2}'.format(
                match.group(1),
                match.group(2),
                linesep,
                match.group(3),
                self.lines[lineNum].rstrip()
            )

            ic("# Attribute {0.id}{1}".format(node.targets[0],
                                                            linesep))
        if isinstance(node.targets[0], Name):
            match = RE._indentRE.match(self.lines[lineNum])
            indentStr = match and match.group(1) or ''
            restrictionLevel = self._checkMemberName(node.targets[0].id)
            if restrictionLevel:
                self.lines[lineNum] = '{0}## @var {1}{2}{0}' \
                                      '# @hideinitializer{2}{0}# @{3}{2}{4}{2}'.format(
                    indentStr,
                    node.targets[0].id,
                    linesep,
                    restrictionLevel,
                    self.lines[lineNum].rstrip()
                )
        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=kwargs['containingNodes'])

    def visit_Call(self, node, **kwargs):
        """
        Handles function calls within code.

        Function calls in Python are used to represent interface implementations
        in addition to their normal use.  If a call appears to mark an
        implementation, it gets labeled as such for Doxygen.
        """
        lineNum = node.lineno - 1
        # Function calls have one Doxygen-significant special case:  interface
        # implementations.
        match = RE._implementsRE.match(self.lines[lineNum])
        if match:
            self.lines[lineNum] = '{0}## @implements {1}{2}{0}{3}{2}'.format(
                match.group(1), match.group(2), linesep,
                self.lines[lineNum].rstrip())

            ic("# Implements {0}{1}".format(match.group(1),
                                                          linesep))
        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=kwargs['containingNodes'])
    # import snoop
    # #snoop.install(out="snoop.log")
    # @snoop.snoop(depth=2)
    def visit_FunctionDef(self, node, **kwargs):
        """
        Handles function definitions within code.

        Process a function's docstring, keeping well aware of the function's
        context and whether or not it's part of an interface definition.
        """

        ic("# Function {0.name}{1}".format(node, linesep))
        # Push either 'interface' or 'class' onto our containing nodes
        # hierarchy so we can keep track of context.  This will let us tell
        # if a function is nested within another function or even if a class
        # is nested within a function.
        containingNodes = kwargs.get('containingNodes', []) or []
        containingNodes.append((node.name, 'function'))
        if self.options.topLevelNamespace:
            fullPathNamespace = self._getFullPathName(containingNodes)
            contextTag = '.'.join(pathTuple[0] for pathTuple in fullPathNamespace)
            modifiedContextTag = self._processMembers(node, contextTag)
            tail = '@namespace {0}'.format(modifiedContextTag)
        else:
            tail = self._processMembers(node, '')
        if get_docstring(node):
            self._processDocstring(node, tail,
                                   containingNodes=containingNodes)
        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=containingNodes)
        # Remove the item we pushed onto the containing nodes hierarchy.
        containingNodes.pop()

    def visit_ClassDef(self, node, **kwargs):
        """
        Handles class definitions within code.

        Process the docstring.  Note though that in Python Class definitions
        are used to define interfaces in addition to classes.
        If a class definition appears to be an interface definition tag it as an
        interface definition for Doxygen.  Otherwise tag it as a class
        definition for Doxygen.
        """
        lineNum = node.lineno - 1
        # Push either 'interface' or 'class' onto our containing nodes
        # hierarchy so we can keep track of context.  This will let us tell
        # if a function is a method or an interface method definition or if
        # a class is fully contained within another class.
        containingNodes = kwargs.get('containingNodes', []) or []
        match = RE._interfaceRE.match(self.lines[lineNum])
        if match:

            ic("# Interface {0.name}{1}".format(node, linesep))
            containingNodes.append((node.name, 'interface'))
        else:

            ic("# Class {0.name}{1}".format(node, linesep))
            containingNodes.append((node.name, 'class'))
        if self.options.topLevelNamespace:
            fullPathNamespace = self._getFullPathName(containingNodes)
            contextTag = '.'.join(pathTuple[0] for pathTuple in fullPathNamespace)
            tail = '@namespace {0}'.format(contextTag)
        else:
            tail = ''
        # Class definitions have one Doxygen-significant special case:
        # interface definitions.
        if match:
            contextTag = '{0}{1}# @interface {2}'.format(tail,
                                                         linesep,
                                                         match.group(1))
        else:
            contextTag = tail
        contextTag = self._processMembers(node, contextTag)
        if get_docstring(node):
            self._processDocstring(node, contextTag,
                                   containingNodes=containingNodes)
        # Visit any contained nodes.
        self.generic_visit(node, containingNodes=containingNodes)
        # Remove the item we pushed onto the containing nodes hierarchy.
        containingNodes.pop()
