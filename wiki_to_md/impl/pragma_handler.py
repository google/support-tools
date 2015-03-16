# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Handles converting of pragmas."""


class PragmaHandler(object):
  """Class that handles the conversion of pragmas."""

  def __init__(self, warning_method):
    """Create a pragma handler.

    Args:
        warning_method: A function to call to display a warning message.
    """
    self._warning_method = warning_method

  def HandlePragma(self,
                   input_line,
                   unused_output_stream,
                   pragma_type,
                   pragma_value):
    """Handle a parsed pragma directive.

    Args:
        input_line: The line number this match occurred on.
        unused_output_stream: Output Markdown file.
        pragma_type: The pragma's type.
        pragma_value: The pragma's value, trimmed.
    """
    # There is no meaningful equivalent to any of the pragmas
    # Google Code supports, so simply notify the user a pragma
    # was matched and that they might want to do something about it.
    if pragma_type == "summary":
      self._warning_method(
          input_line,
          u"A summary pragma was used for this wiki:\n"
          "\t{0}\n"
          "Consider moving it to an introductory paragraph."
          .format(pragma_value))
    elif pragma_type == "sidebar":
      self._warning_method(
          input_line,
          u"A sidebar pragma was used for this wiki:\n"
          "\t{0}\n"
          "The Gollum wiki system supports sidebars, and by converting "
          "{0}.wiki to _Sidebar.md it can be used as a sidebar.\n"
          "See https://github.com/gollum/gollum/wiki for more information."
          .format(pragma_value))
    else:
      self._warning_method(
          input_line,
          u"The following pragma has been ignored:\n"
          "\t#{0} {1}\n"
          "Consider expressing the same information in a different manner."
          .format(pragma_type, pragma_value))
