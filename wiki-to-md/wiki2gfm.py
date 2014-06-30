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
"""Tool to convert Google Code Wiki files to GitHub-flavored Markdown.

  Reference for Google Code Wiki:
      https://code.google.com/p/support/wiki/WikiSyntax

  Reference for Github-flavored Markdown:
      https://help.github.com/articles/github-flavored-markdown

  The conversion process is not always able to be made; for example,
  wiki pragma statements have no direct equivalent for GFM. In cases
  where no direct conversion can be made, or the input may have unexpected
  output, a warning will be issued.

  To use this tool:
  1. TODO(ngorski): Simple steps to follow.
"""
import argparse

import codecs
import os
import sys

from impl import converter as converter_mod
from impl import formatting_handler as formatting_handler_mod
from impl import pragma_handler as pragma_handler_mod


def PrintWarning(input_line, message):
  """Print a warning.

  When a conversion cannot be done or may be unreliable/inexact,
  a warning will be printed to stdout notifying the user of this.

  Args:
    input_line: The line number this warning occurred on.
    message: The warning message.
  """
  print "Warning (line {0} of input file):\n{1}\n".format(input_line, message)


def main(args):
  """The main function.

  Args:
     args: The command line arguments.
  """
  parser = argparse.ArgumentParser(
      description="Converts a Google Code wiki page to GitHub-flavored "
      "Markdown. For more information, see TODO(ngorski).")

  parser.add_argument("--input_file", required=True,
                      help="The input Google Code Wiki file")
  parser.add_argument("--output_file", required=True,
                      help="The output GitHub-flavored Markdown file")
  parser.add_argument("--project", required=False,
                      help="The name of the project for the Wiki")
  parser.add_argument("--wikipages_list", nargs="*",
                      help="The list of wiki pages that are assumed to exist "
                      "for the purpose of auto-linking to other pages")
  parser.add_argument("--wikipages_path", nargs="*",
                      help="The list of paths containing wiki pages that are "
                      "assumed to exist for the purpose of auto-linking to "
                      "other pages")
  symmetric_headers_help = ("Controls if the output of header level "
                            "indicators are made symmetric. E.g. '### Header' "
                            "if disabled, and '### Header ###' if enabled")
  parser.add_argument("--symmetric_headers", dest="symmetric_headers",
                      action="store_true", help=symmetric_headers_help)
  parser.add_argument("--no_symmetric_headers", dest="symmetric_headers",
                      action="store_false", help=symmetric_headers_help)
  parser.set_defaults(feature=False)

  parsed_args, unused_unknown_args = parser.parse_known_args(args)

  with codecs.open(parsed_args.input_file, "rU", "utf-8") as input_stream:
    with codecs.open(parsed_args.output_file, "wU", "utf-8") as output_stream:
      # Create the master list of wiki pages assumed to exist.
      wikipages = parsed_args.wikipages_list or []
      wikipages.append(parsed_args.input_file)

      if parsed_args.wikipages_path:
        # Add all the .wiki files in all the given paths.
        for path in parsed_args.wikipages_path:
          for f in os.listdir(path):
            if f.endswith(".wiki"):
              wikipages.append(f[:-len(".wiki")])

      # TODO(ngorski): Get from a file that the issue migration script provides.
      issue_map = {}

      # Prepare the handlers and converter.
      pragma_handler = pragma_handler_mod.PragmaHandler(PrintWarning)
      formatting_handler = formatting_handler_mod.FormattingHandler(
          PrintWarning,
          parsed_args.project,
          issue_map,
          parsed_args.symmetric_headers)
      converter = converter_mod.Converter(
          pragma_handler,
          formatting_handler,
          PrintWarning,
          parsed_args.project,
          wikipages)

      # And perform the conversion.
      converter.Convert(input_stream, output_stream)


if __name__ == "__main__":
  main(sys.argv)
