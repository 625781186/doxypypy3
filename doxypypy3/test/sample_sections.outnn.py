#!/usr/bin/env python
# encoding: utf-8
## @brief Sample documentation the arbitrary section handling.
#
#Related to issue #7 [1].
#
#[1]: https://github.com/Feneric/doxypypy/issues/7
#



## @brief A simple function of two arguments.
#
#    This function takes two arguments, but does absolutely nothing with them.
#    However, it sends out a friendly greeting to the world.
#
#
# @param		arg1	The first argument
# @param		arg2	The second argument
#
# @return
#        A string stating "Hello World"
#
# @b Examples
# @code
#        >>> function(1, 2)
#        "Hello World"
#        >>> function('a', 'b')
#        "Hello World"
# @endcode
#
# @par Intent
#        The intent is to demonstrate sections like this one within docstrings.
#        How they behave with multiple lines.
# @par
#        And how they behave with multiple paragraphs.
#        That contain multiple lines.
#
#    Paragraphs standing by themselves without indentation, should be left alone.
#
def function(arg1, arg2):
    return "Hello World"
