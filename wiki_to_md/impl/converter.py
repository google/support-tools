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
"""Handles conversion of Wiki files."""
import urlparse

from . import constants


class Converter(object):
  """Class that handles the actual parsing and generation."""

  # A map of HTML tags to a list of the supported args for that tag.
  _BASIC_HTML_ARGS = ["title", "dir", "lang"]
  _BASIC_HTML_SIZEABLE_ARGS = (_BASIC_HTML_ARGS +
                               ["border", "height", "width", "align"])
  _BASIC_HTML_TABLE_ARGS = (_BASIC_HTML_SIZEABLE_ARGS +
                            ["valign", "cellspacing", "cellpadding"])
  _ALLOWED_HTML_TAGS = {
      "a": _BASIC_HTML_ARGS + ["href"],
      "b": _BASIC_HTML_ARGS,
      "br": _BASIC_HTML_ARGS,
      "blockquote": _BASIC_HTML_ARGS,
      "code": _BASIC_HTML_ARGS + ["language"],
      "dd": _BASIC_HTML_ARGS,
      "div": _BASIC_HTML_ARGS,
      "dl": _BASIC_HTML_ARGS,
      "dt": _BASIC_HTML_ARGS,
      "em": _BASIC_HTML_ARGS,
      "font": _BASIC_HTML_ARGS + ["face", "size", "color"],
      "h1": _BASIC_HTML_ARGS,
      "h2": _BASIC_HTML_ARGS,
      "h3": _BASIC_HTML_ARGS,
      "h4": _BASIC_HTML_ARGS,
      "h5": _BASIC_HTML_ARGS,
      "i": _BASIC_HTML_ARGS,
      "img": _BASIC_HTML_SIZEABLE_ARGS + ["src", "alt"],
      "li": _BASIC_HTML_ARGS,
      "ol": _BASIC_HTML_ARGS + ["type", "start"],
      "p": _BASIC_HTML_ARGS + ["align"],
      "pre": _BASIC_HTML_ARGS,
      "q": _BASIC_HTML_ARGS,
      "s": _BASIC_HTML_ARGS,
      "span": _BASIC_HTML_ARGS,
      "strike": _BASIC_HTML_ARGS,
      "strong": _BASIC_HTML_ARGS,
      "sub": _BASIC_HTML_ARGS,
      "sup": _BASIC_HTML_ARGS,
      "table": _BASIC_HTML_TABLE_ARGS,
      "tbody": _BASIC_HTML_TABLE_ARGS,
      "td": _BASIC_HTML_TABLE_ARGS,
      "tfoot": _BASIC_HTML_TABLE_ARGS,
      "th": _BASIC_HTML_TABLE_ARGS,
      "thead": _BASIC_HTML_TABLE_ARGS + ["colspan", "rowspan"],
      "tr": _BASIC_HTML_TABLE_ARGS + ["colspan", "rowspan"],
      "tt": _BASIC_HTML_ARGS,
      "u": _BASIC_HTML_ARGS,
      "ul": _BASIC_HTML_ARGS + ["type"],
      "var": _BASIC_HTML_ARGS,
  }

  # These plugins consume raw text.
  _RAW_PLUGINS = ["code", "wiki:comment", "pre"]

  # Parameters supported by the g:plusone plugin.
  _PLUSONE_ARGS = ["count", "size", "href"]

  # Parameters supported by the wiki:video plugin.
  _VIDEO_ARGS = ["url", "width", "height"]
  _VIDEO_DEFAULT_WIDTH = "425"
  _VIDEO_DEFAULT_HEIGHT = "344"

  def __init__(
      self,
      pragma_handler,
      formatting_handler,
      warning_method,
      project,
      wikipages):
    """Create a converter.

    Args:
        pragma_handler: Handler for parsed pragmas.
        formatting_handler: Handler for parsed formatting rules.
        warning_method: A function to call to display a warning message.
        project: The name of the Google Code project for the Wiki page.
        wikipages: Wiki pages assumed to exist for auto-linking.
    """
    self._pragma_handler = pragma_handler
    self._formatting_handler = formatting_handler
    self._warning_method = warning_method
    self._wikipages = wikipages
    self._project = project

  def Convert(self, input_stream, output_stream):
    """Converts a file in Google Code Wiki format to Github-flavored Markdown.

    Args:
        input_stream: Input Wiki file.
        output_stream: Output Markdown file.
    """
    # For simpler processing just load the entire file into memory.
    input_lines = input_stream.readlines()
    input_line = 1

    # First extract pragmas, which must be placed at the top of the file.
    input_line = self._ExtractPragmas(input_line, input_lines, output_stream)

    # Now ignore any starting vertical whitespace.
    input_line = self._MoveToMain(input_line, input_lines, output_stream)

    # At the main text, begin processing.
    input_line = self._ProcessBody(input_line, input_lines, output_stream)

    # Done, but sanity check the amount of input processed.
    remaining_lines = len(input_lines) - input_line + 1
    if remaining_lines != 0:
      self._warning_method(
          input_line,
          u"Processing completed, but not all lines were processed. "
          "Remaining lines: {0}.".format(remaining_lines))

  def _ExtractPragmas(self, input_line, input_lines, output_stream):
    """Extracts pragmas from a given input.

    Args:
        input_line: Current line number being processed.
        input_lines: Input Wiki file lines.
        output_stream: Output Markdown file.
    Returns:
        The new value of input_line after processing.
    """
    for line in input_lines[input_line - 1:]:
      pragma_match = constants.PRAGMA_RE.match(line)
      if not pragma_match:
        # Found all the pragmas.
        break

      # Found a pragma, strip it and pass it to the handler.
      pragma_type, pragma_value = pragma_match.groups()

      self._pragma_handler.HandlePragma(
          input_line,
          output_stream,
          pragma_type.strip(),
          pragma_value.strip())

      # Moving on to the next line.
      input_line += 1

    return input_line

  def _MoveToMain(self, input_line, input_lines, unused_output_stream):
    """Move the input line position to the main body, after pragmas.

    Args:
        input_line: Current line number being processed.
        input_lines: Input Wiki file lines.
    Returns:
        The new value of input_line after processing.
    """
    for line in input_lines[input_line - 1:]:
      if line.strip():
        # Skipped all the whitespace.
        break

      # Moving on to the next line.
      input_line += 1

    return input_line

  def _ProcessBody(self, input_line, input_lines, output_stream):
    """The process core.

    It is a simple loop that tries to match formatting rules
    then pass it to the correct handler. It processes the matches
    in the same order as Google Code's wiki parser.

    Args:
        input_line: Current line number being processed.
        input_lines: Input Wiki file lines.
        output_stream: Output Markdown file.
    Returns:
        The new value of input_line after processing.
    """
    # State tracked during processing:
    self._code_block_depth = 0  # How many code block openings we've seen.
    self._code_block_lines = []  # What lines we've collected for a code block.
    self._indents = []  # 2-tuple of indent position and list type.
    self._open_tags = []  # List of open tags, like bold or italic.
    self._table_columns = []  # Table column sizes, taken from the header row.
    self._table_column = 0  # Current column in the table body, or zero if none.
    self._plugin_stack = []  # Current stack of plugins and their parameters.

    first_line = True
    for line in input_lines[input_line - 1:]:
      stripped_line = line.strip()

      self._ProcessLine(
          first_line,
          input_line,
          line,
          stripped_line,
          output_stream)

      # Moving on to the next line.
      input_line += 1
      first_line = False

    if self._code_block_depth:
      # Forgotten code block ending, close it implicitly.
      code = "".join(self._code_block_lines)
      self._formatting_handler.HandleText(input_line, output_stream, code)
      self._formatting_handler.HandleCodeBlockClose(input_line, output_stream)

    return input_line

  def _ProcessLine(
      self,
      first_line,
      input_line,
      line,
      stripped_line,
      output_stream):
    """Processes a single line, depending on state.

    Args:
        first_line: True if this is the first line, false otherwise.
        input_line: Current line number being processed.
        line: The raw line string.
        stripped_line: The line string, stripped of surrounding whitepsace.
        output_stream: Output Markdown file.
    Returns:
        The new value of input_line after processing.
    """
    # Check for the start of a code block.
    if constants.START_CODEBLOCK_RE.match(stripped_line):
      if self._code_block_depth == 0:
        # Start a new collection of lines.
        self._code_block_lines = []
      else:
        # Just an embedded code block.
        self._code_block_lines.append(line)
      self._code_block_depth += 1
      return

    # Check for the end of a code block.
    if constants.END_CODEBLOCK_RE.match(stripped_line):
      self._code_block_depth -= 1
      if self._code_block_depth == 0:
        # Closed the highest-level code block, handle it.
        self._formatting_handler.HandleEscapedText(
            input_line,
            output_stream,
            "\n")
        self._formatting_handler.HandleCodeBlockOpen(
            input_line,
            output_stream,
            None)
        code = "".join(self._code_block_lines)
        self._formatting_handler.HandleText(input_line, output_stream, code)
        self._formatting_handler.HandleCodeBlockClose(input_line, output_stream)
      else:
        # Just closed an embedded clode block.
        self._code_block_lines.append(line)
      return

    # Check if we're in a code block.
    # If we are, just put the raw text into code_block_lines.
    if self._code_block_depth != 0:
      self._code_block_lines.append(line)
      return

    # For empty lines, close all formatting.
    if not stripped_line:
      if not self._ConsumeTextForPlugin():
        self._SetCurrentList(input_line, 0, " ", output_stream)
        self._CloseTags(input_line, output_stream)

        if self._table_columns:
          self._formatting_handler.HandleTableClose(input_line, output_stream)
        self._table_columns = []
        self._table_column = 0

      self._formatting_handler.HandleParagraphBreak(input_line, output_stream)
      return

    # Non-empty line, finish the previous line's newline.
    if not first_line:
      self._formatting_handler.HandleEscapedText(
          input_line,
          output_stream,
          "\n")

    # Now check if we're processing within a list.
    indent_pos = constants.INDENT_RE.match(line).end()
    if (indent_pos and indent_pos < len(line) and
        not self._ConsumeTextForPlugin()):
      list_type = constants.LIST_TYPES.get(line[indent_pos], "blockquote")

      if self._SetCurrentList(input_line, indent_pos, list_type, output_stream):
        # Blockquotes take the entire remainder of the line,
        # but everything else skips the list symbol plus the space after.
        # (In case there is no space after, the first character is skipped;
        # we will warn if this is detected, as it was probably unintended.)
        if list_type == "blockquote":
          line = line[indent_pos:]
        else:
          if line[indent_pos + 1] != " ":
            self._warning_method(
                input_line,
                u"Missing space after list symbol: {0}, "
                "'{1}' was removed instead."
                .format(line[indent_pos], line[indent_pos + 1]))
          line = line[indent_pos + 2:]

        stripped_line = line.strip()
      else:
        # Reset to no indent.
        self._SetCurrentList(input_line, 0, " ", output_stream)

    # Finally, split the line into formatting primitives.
    # We do so without whitespace so we can catch line breaks across tags.
    if constants.LINE_FORMAT_RE.match(stripped_line):
      self._ProcessMatch(
          input_line,
          constants.LINE_FORMAT_RE,
          stripped_line,
          output_stream)
    else:
      self._ProcessMatch(
          input_line,
          constants.TEXT_FORMAT_RE,
          stripped_line,
          output_stream)

    self._CloseTableRow(input_line, output_stream)

  def _SetCurrentList(self, input_line, indent_pos, list_type, output_stream):
    """Set the current list level based on the indentation.

    Args:
      input_line: Current line number being processed.
      indent_pos: How far into the line we are indented.
      list_type: What the type of the list should be.
      output_stream: Output Markdown file.
    Returns:
      True if we are in a list item, False otherwise.
    """
    # Pop and close the lists until we hit a
    # list that is at the current position and type
    while self._indents and self._indents[-1][0] >= indent_pos:
      indents_top = self._indents[-1]
      if indents_top[0] == indent_pos and indents_top[1] == list_type:
        break

      self._formatting_handler.HandleListClose(input_line, output_stream)
      self._indents.pop()

    # If we just popped everything off, we're not in a list.
    if indent_pos == 0:
      return False

    if not self._indents or indent_pos >= self._indents[-1][0]:
      # Add a new indentation if this is the first item overall,
      # or the first item at this indentation position.
      if not self._indents or indent_pos > self._indents[-1][0]:
        self._indents.append((indent_pos, list_type))

      # Add the leading Markdown for the list.
      indentation_level = len(self._indents)
      if list_type == "numeric":
        self._formatting_handler.HandleNumericListOpen(
            input_line,
            output_stream,
            indentation_level)
      elif list_type == "bullet":
        self._formatting_handler.HandleBulletListOpen(
            input_line,
            output_stream,
            indentation_level)
      elif list_type == "blockquote":
        self._formatting_handler.HandleBlockQuoteOpen(
            input_line,
            output_stream,
            indentation_level)
      else:
        self._warning_method(
            input_line,
            u"Bad list type: '{0}'".format(list_type))

    return True

  def _OpenTag(self, input_line, tag, output_stream):
    """Open a tag and add it to the open tags list.

    Args:
      input_line: Current line number being processed.
      tag: Tag to open.
      output_stream: Output Markdown file.
    """
    handler = getattr(
        self._formatting_handler, u"Handle{0}Open".format(tag), None)
    if handler:
      handler(input_line, output_stream)
    else:
      self._warning_method(input_line, u"Bad open tag: '{0}'".format(tag))

    self._open_tags.append(tag)

  def _CloseTag(self, input_line, tag, output_stream):
    """Close a tag and remove it from the open tags list.

    Args:
      input_line: Current line number being processed.
      tag: Tag to close.
      output_stream: Output Markdown file.
    """
    handler = getattr(
        self._formatting_handler, u"Handle{0}Close".format(tag), None)
    if handler:
      handler(input_line, output_stream)
    else:
      self._warning_method(input_line, u"Bad close tag: '{0}'".format(tag))

    self._open_tags.remove(tag)

  def _CloseTags(self, input_line, output_stream):
    """Close all tags.

    Args:
      input_line: Current line number being processed.
      output_stream: Output Markdown file.
    """
    for tag in self._open_tags:
      self._CloseTag(input_line, tag, output_stream)

  def _CloseTableRow(self, input_line, output_stream):
    """Close table row, if any.

    Args:
      input_line: Current line number being processed.
      output_stream: Output Markdown file.
    """
    if self._table_columns:
      if self._table_column != 1:
        self._formatting_handler.HandleTableRowEnd(input_line, output_stream)

      # Check if we just finished the header row.
      if not self._table_column:
        self._formatting_handler.HandleTableHeader(
            input_line,
            output_stream,
            self._table_columns)

      # In a table body, set the current column to 1.
      self._table_column = 1

  def _ConsumeTextForPlugin(self):
    """Check if text should be consumed raw for a plugin.

    Returns:
      True if the current plugin is consuming raw text, false otherwise.
    """
    return (self._plugin_stack and
            self._plugin_stack[-1]["id"] in self._RAW_PLUGINS)

  def _ProcessMatch(self, input_line, match_regex, line, output_stream):
    """Process text, using a regex to match against.

    Args:
      input_line: Current line number being processed.
      match_regex: Regex to match the line against.
      line: The line being processed.
      output_stream: Output Markdown file.
    """
    lastpos = 0
    for fullmatch in match_regex.finditer(line):
      # Add text before the match as regular text.
      if lastpos < fullmatch.start():
        starting_line = line[lastpos:fullmatch.start()]
        if self._ConsumeTextForPlugin():
          self._formatting_handler.HandleText(
              input_line,
              output_stream,
              starting_line)
        else:
          self._formatting_handler.HandleEscapedText(
              input_line,
              output_stream,
              starting_line)

      for rulename, match in fullmatch.groupdict().items():
        if match is not None:
          if self._ConsumeTextForPlugin() and rulename != "PluginEnd":
            self._formatting_handler.HandleText(
                input_line,
                output_stream,
                match)
          else:
            handler = getattr(self, u"_Handle{0}".format(rulename), None)
            handler(input_line, match, output_stream)

      lastpos = fullmatch.end()

    # Add remainder of the line as regular text.
    if lastpos < len(line):
      remaining_line = line[lastpos:]
      if self._ConsumeTextForPlugin():
        self._formatting_handler.HandleText(
            input_line,
            output_stream,
            remaining_line)
      else:
        self._formatting_handler.HandleEscapedText(
            input_line,
            output_stream,
            remaining_line)

  def _HandleHeading(self, input_line, match, output_stream):
    """Handle a heading formatter.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    match = match.strip()

    # Count the equals on the left side.
    leftequalcount = 0
    for char in match:
      if char != "=":
        break
      leftequalcount += 1

    # Count the equals on the right side.
    rightequalcount = 0
    for char in reversed(match):
      if char != "=":
        break
      rightequalcount += 1

    # Users often forget to have the same number of equals signs on
    # both sides. Rather than simply error out, we say the level is
    # the number of equals signs on the left side.
    header_level = leftequalcount

    # If the level is greater than 6, the header is invalid and the contents
    # are parsed as if no header markup were provided.
    if header_level > 6:
      header_level = None

    # Everything else is the heading text.
    heading_text = match[leftequalcount:-rightequalcount].strip()

    if header_level:
      self._formatting_handler.HandleHeaderOpen(
          input_line,
          output_stream,
          header_level)

    self._ProcessMatch(
        input_line,
        constants.TEXT_FORMAT_RE,
        heading_text,
        output_stream)

    if header_level:
      self._formatting_handler.HandleHeaderClose(
          input_line,
          output_stream,
          header_level)

  def _HandleHRule(self, input_line, unused_match, output_stream):
    """Handle a heading formatter.

    Args:
      input_line: Current line number being processed.
      unused_match: Matched text.
      output_stream: Output Markdown file.
    """
    self._formatting_handler.HandleHRule(input_line, output_stream)

  def _HandleBold(self, input_line, unused_match, output_stream):
    """Handle a bold formatter.

    Args:
      input_line: Current line number being processed.
      unused_match: Matched text.
      output_stream: Output Markdown file.
    """
    self._HandleTag(input_line, "Bold", output_stream)

  def _HandleItalic(self, input_line, unused_match, output_stream):
    """Handle a italic formatter.

    Args:
      input_line: Current line number being processed.
      unused_match: Matched text.
      output_stream: Output Markdown file.
    """
    self._HandleTag(input_line, "Italic", output_stream)

  def _HandleStrikethrough(self, input_line, unused_match, output_stream):
    """Handle a strikethrough formatter.

    Args:
      input_line: Current line number being processed.
      unused_match: Matched text.
      output_stream: Output Markdown file.
    """
    self._HandleTag(input_line, "Strikethrough", output_stream)

  def _HandleSuperscript(self, input_line, match, output_stream):
    """Handle superscript.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    self._formatting_handler.HandleSuperscript(input_line, output_stream, match)

  def _HandleSubscript(self, input_line, match, output_stream):
    """Handle subscript.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    self._formatting_handler.HandleSubscript(input_line, output_stream, match)

  def _HandleInlineCode(self, input_line, match, output_stream):
    """Handle inline code, method one.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    self._formatting_handler.HandleInlineCode(input_line, output_stream, match)

  def _HandleInlineCode2(self, input_line, match, output_stream):
    """Handle inline code, method two.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    self._formatting_handler.HandleInlineCode(input_line, output_stream, match)

  def _HandleTableCell(self, input_line, match, output_stream):
    """Handle a table cell.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    # Table cells end previous formatting.
    self._CloseTags(input_line, output_stream)

    # Count the pipes to calculate the column span.
    pipecount = 0
    for char in match:
      if char != "|":
        break
      pipecount += 1

    span = pipecount / 2

    # Now output the cell, tracking the size of the contents.
    self._formatting_handler.HandleTableCellBorder(input_line, output_stream)

    starting_pos = output_stream.tell()
    self._ProcessMatch(
        input_line,
        constants.TEXT_FORMAT_RE,
        match[pipecount:],
        output_stream)
    ending_pos = output_stream.tell()

    # Handle the cell width, either tracking or padding.
    cell_width = ending_pos - starting_pos
    if not self._table_column:
      # In the header row, track the column sizes.
      self._table_columns.append(cell_width)
    else:
      # In the table body, pad the cell (for prettier raw text viewing).
      header_cell_width = self._table_columns[self._table_column - 1]
      remaining_width = header_cell_width - cell_width
      if remaining_width > 0:
        padding = " " * remaining_width
        self._formatting_handler.HandleEscapedText(
            input_line,
            output_stream,
            padding)

      self._table_column += 1

    if span > 1:
      self._warning_method(
          input_line,
          "Multi-span cells are not directly supported in GFM. They have been "
          "emulated by adding empty cells. This may give the correct rendered "
          "result, but the plain-text representation may be noisy. Consider "
          "removing the multi-span cells from your table, or using HTML.")
      while span > 1:
        # Empty cell.
        self._formatting_handler.HandleTableCellBorder(
            input_line,
            output_stream)
        self._formatting_handler.HandleEscapedText(
            input_line,
            output_stream,
            " ")
        self._table_columns.append(1)

        span -= 1

  def _HandleTableRowEnd(self, input_line, unused_match, output_stream):
    """Handle a table row ending.

    Args:
      input_line: Current line number being processed.
      unused_match: Matched text.
      output_stream: Output Markdown file.
    """
    # Table cells end previous formatting.
    self._CloseTags(input_line, output_stream)

    self._CloseTableRow(input_line, output_stream)

  def _HandleUrl(self, input_line, match, output_stream):
    """Handle an auto-linked URL.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    self._formatting_handler.HandleLink(input_line, output_stream, match, None)

  def _HandleUrlBracket(self, input_line, match, output_stream):
    """Handle a bracketed URL.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    # First, strip the brackets off to get to the URL and description.
    core = match[1:-1]

    # Now strip out the description.
    parts = constants.WHITESPACE_RE.split(core, 1)
    if len(parts) == 1:
      url = parts[0]
      description = None
    else:
      url = parts[0]
      description = parts[1]

    self._formatting_handler.HandleLink(
        input_line,
        output_stream,
        url,
        description)

  def _HandleWikiWord(self, input_line, match, output_stream):
    """Handle a wiki word.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    if match[0] == "!":
      self._formatting_handler.HandleEscapedText(
          input_line,
          output_stream,
          match[1:])
    elif match not in self._wikipages:
      self._formatting_handler.HandleEscapedText(
          input_line,
          output_stream,
          match)
    else:
      self._formatting_handler.HandleWiki(
          input_line,
          output_stream,
          match,
          None)

  def _HandleWikiWordBracket(self, input_line, match, output_stream):
    """Handle a bracketed wiki word.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    # First, strip the brackets off to get to the wiki and description.
    core = match[1:-1]

    # Now strip out the description.
    parts = constants.WHITESPACE_RE.split(core, 1)
    if len(parts) == 1:
      wiki = parts[0]
      description = None
    else:
      wiki = parts[0]
      description = parts[1]

    self._formatting_handler.HandleWiki(
        input_line,
        output_stream,
        wiki,
        description)

  def _HandleIssueLink(self, input_line, match, output_stream):
    """Handle an auto-linked issue.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    issue = match[len("issue"):].strip()
    prefix = match[:-len(issue)]

    self._formatting_handler.HandleIssue(
        input_line,
        output_stream,
        prefix,
        issue)

  def _HandleRevisionLink(self, input_line, match, output_stream):
    """Handle an auto-linked revision.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    if match[1].lower() == "e":
      revision = match[len("revision"):].strip()
    else:
      revision = match[len("r"):].strip()
    prefix = match[:-len(revision)]

    self._formatting_handler.HandleRevision(
        input_line,
        output_stream,
        prefix,
        revision)

  def _HandlePlugin(self, input_line, match, output_stream):
    """Handle a plugin tag.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    # Plugins close formatting tags.
    self._CloseTags(input_line, output_stream)

    # Get the core of the tag, check if this is also an end tag.
    if match.endswith("/>"):
      core = match[1:-2]
      has_end = True
    else:
      core = match[1:-1]
      has_end = False

    # Extract the ID for the plugin.
    plugin_id = constants.PLUGIN_ID_RE.match(core).group(0)
    core_params = core[len(plugin_id):].strip()

    # Extract the parameters for the plugin.
    params = {}
    for name, value in constants.PLUGIN_PARAM_RE.findall(core_params):
      # Remove quotes from the value, if they exist
      if value.startswith("'"):
        value = value.strip("'")
      elif value.startswith("\""):
        value = value.strip("\"")
      params[name] = value

    # Now figure out what to do with the plugin.
    if plugin_id in self._ALLOWED_HTML_TAGS:
      self._HandlePluginHtml(
          input_line,
          plugin_id,
          params,
          has_end,
          output_stream)
    elif plugin_id == "g:plusone":
      self._HandlePluginGPlus(
          input_line,
          plugin_id,
          params,
          output_stream)
    elif plugin_id == "wiki:comment":
      self._HandlePluginWikiComment(
          input_line,
          plugin_id,
          params,
          output_stream)
    elif plugin_id == "wiki:gadget":
      self._HandlePluginWikiGadget(input_line, match, output_stream)
    elif plugin_id == "wiki:video":
      self._HandlePluginWikiVideo(
          input_line,
          plugin_id,
          params,
          output_stream)
    elif plugin_id == "wiki:toc":
      self._HandlePluginWikiToc(input_line, match, output_stream)
    else:
      self._warning_method(
          input_line,
          u"Unknown plugin was given, outputting "
          "as plain text:\n\t{0}".format(match))
      # Wiki syntax put this class of error on its own line.
      self._formatting_handler.HandleEscapedText(
          input_line,
          output_stream,
          u"\n\n{0}\n\n".format(match))

    # Add plugin and parameters to the stack.
    if not has_end:
      plugin_info = {"id": plugin_id, "params": params}
      self._plugin_stack.append(plugin_info)

  def _HandlePluginHtml(
      self,
      input_line,
      plugin_id,
      params,
      has_end,
      output_stream):
    """Handle a plugin tag for HTML.

    Args:
      input_line: Current line number being processed.
      plugin_id: The plugin ID.
      params: The plugin params.
      has_end: Plugin has an end tag.
      output_stream: Output Markdown file.
    """
    # Filter the parameters. These are only filtered for output,
    # they still have the effect of being usable variables.
    allowed_parameters = self._ALLOWED_HTML_TAGS[plugin_id]
    filtered_params = {}
    for name, value in params.items():
      if name in allowed_parameters:
        filtered_params[name] = value
      else:
        self._warning_method(
            input_line,
            u"The following parameter was given for the '{0}' tag, "
            "but will not be present in the outputted HTML:\n\t'{1}': '{2}'"
            .format(plugin_id, name, value))

    if plugin_id == "code":
      self._formatting_handler.HandleCodeBlockOpen(
          input_line,
          output_stream,
          filtered_params.get("language"))
    else:
      self._formatting_handler.HandleHtmlOpen(
          input_line,
          output_stream,
          plugin_id,
          filtered_params,
          has_end)

  def _HandlePluginGPlus(
      self,
      input_line,
      plugin_id,
      params,
      output_stream):
    """Handle a plugin tag for +1 button.

    Args:
      input_line: Current line number being processed.
      plugin_id: The plugin ID.
      params: The plugin params.
      output_stream: Output Markdown file.
    """
    filtered_params = {}
    for name, value in params.items():
      if name in self._PLUSONE_ARGS:
        filtered_params[name] = value
      else:
        self._warning_method(
            input_line,
            u"The following parameter was given for the '{0}' tag, "
            "but will not be present in the outputted HTML:\n\t'{1}': '{2}'"
            .format(plugin_id, name, value))

    self._formatting_handler.HandleGPlusOpen(
        input_line,
        output_stream,
        filtered_params)

  def _HandlePluginWikiComment(
      self,
      input_line,
      plugin_id,
      params,
      output_stream):
    """Handle a plugin tag for a wiki comment.

    Args:
      input_line: Current line number being processed.
      plugin_id: The plugin ID.
      params: The plugin params.
      output_stream: Output Markdown file.
    """
    for name, value in params.items():
      self._warning_method(
          input_line,
          u"The following parameter was given for the '{0}' tag, "
          "but will not be present in the outputted HTML:\n\t'{1}': '{2}'"
          .format(plugin_id, name, value))

    self._formatting_handler.HandleCommentOpen(input_line, output_stream)

  def _HandlePluginWikiGadget(self, input_line, match, output_stream):
    """Handle a plugin tag for a wiki gadget.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    self._warning_method(
        input_line,
        u"A wiki gadget was used, but this must be manually converted to a "
        "GFM-supported method, if possible. Outputting as plain text:\n\t{0}"
        .format(match))
    self._formatting_handler.HandleEscapedText(
        input_line,
        output_stream,
        match)

  def _HandlePluginWikiVideo(
      self,
      input_line,
      plugin_id,
      params,
      output_stream):
    """Handle a plugin tag for a wiki video.

    Args:
      input_line: Current line number being processed.
      plugin_id: The plugin ID.
      params: The plugin params.
      output_stream: Output Markdown file.
    """
    filtered_params = {}
    for name, value in params.items():
      if name in self._VIDEO_ARGS:
        filtered_params[name] = value
      else:
        self._warning_method(
            input_line,
            u"The following parameter was given for the '{0}' tag, "
            "but will not be present in the outputted HTML:\n\t'{1}': '{2}'"
            .format(plugin_id, name, value))

    if "url" in filtered_params:
      width = filtered_params.get("width", self._VIDEO_DEFAULT_WIDTH)
      height = filtered_params.get("height", self._VIDEO_DEFAULT_HEIGHT)
      extracted = urlparse.urlparse(filtered_params["url"])
      query = urlparse.parse_qs(extracted.query)
      video_id = query.get("v", [""])[0]
      if not video_id and extracted.path.startswith("/v/"):
        video_id = extracted.path[3:]
      if not constants.YOUTUBE_VIDEO_ID_RE.match(video_id):
        output = ("wiki:video: cannot find YouTube "
                  "video id within parameter \"url\".")
        self._warning_method(
            input_line,
            u"Video plugin has invalid video ID, outputting error:\n\t{0}"
            .format(output))
        # Wiki syntax put this class of error on its own line.
        self._formatting_handler.HandleEscapedText(
            input_line,
            output_stream,
            u"\n\n{0}\n\n".format(output))
      else:
        self._formatting_handler.HandleVideoOpen(
            input_line,
            output_stream,
            video_id,
            width,
            height)
    else:
      output = "wiki:video: missing mandatory parameter \"url\"."
      self._warning_method(
          input_line,
          u"Video plugin is missing 'url' parameter, outputting error:\n\t{0}"
          .format(output))
      # Wiki syntax put this class of error on its own line.
      self._formatting_handler.HandleEscapedText(
          input_line,
          output_stream,
          u"\n\n{0}\n\n".format(output))

  def _HandlePluginWikiToc(self, input_line, match, output_stream):
    """Handle a plugin tag for a wiki table of contents.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    self._warning_method(
        input_line,
        u"A table of contents plugin was used for this wiki:\n"
        "\t{0}\n"
        "The Gollum wiki system supports table of content generation.\n"
        "See https://github.com/gollum/gollum/wiki for more information.\n"
        "It has been removed."
        .format(match))

  def _HandlePluginEnd(self, input_line, match, output_stream):
    """Handle a plugin ending tag.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    core = match[2:-1]
    plugin_id = constants.PLUGIN_ID_RE.match(core).group(0)

    if self._plugin_stack and self._plugin_stack[-1]["id"] == plugin_id:
      self._plugin_stack.pop()

      if plugin_id in self._ALLOWED_HTML_TAGS:
        if plugin_id == "code":
          self._formatting_handler.HandleCodeBlockClose(
              input_line,
              output_stream)
        else:
          self._formatting_handler.HandleHtmlClose(
              input_line,
              output_stream,
              plugin_id)
      elif plugin_id == "g:plusone":
        self._formatting_handler.HandleGPlusClose(input_line, output_stream)
      elif plugin_id == "wiki:comment":
        self._formatting_handler.HandleCommentClose(input_line, output_stream)
      elif plugin_id == "wiki:gadget":
        # A warning was already issued on the opening tag.
        self._formatting_handler.HandleEscapedText(
            input_line,
            output_stream,
            match)
      elif plugin_id == "wiki:video":
        self._formatting_handler.HandleVideoClose(input_line, output_stream)
      elif plugin_id == "wiki:toc":
        # A warning was already issued on the opening tag.
        pass
      else:
        self._warning_method(
            input_line,
            u"Unknown but matching plugin end was given, outputting "
            "as plain text:\n\t{0}".format(match))
        # Wiki syntax put this class of error on its own line.
        self._formatting_handler.HandleEscapedText(
            input_line,
            output_stream,
            u"\n\n{0}\n\n".format(match))
    else:
      self._warning_method(
          input_line,
          u"Unknown/unmatched plugin end was given, outputting "
          "as plain text with errors:\n\t{0}".format(match))
      # Wiki syntax put this class of error on its own line,
      # with a prefix error message, and did not display the tag namespace.
      tag_without_ns = plugin_id.split(":", 1)[-1]
      self._formatting_handler.HandleEscapedText(
          input_line,
          output_stream,
          u"\n\nUnknown end tag for </{0}>\n\n".format(tag_without_ns))

  def _HandleVariable(self, input_line, match, output_stream):
    """Handle a variable.

    Args:
      input_line: Current line number being processed.
      match: Matched text.
      output_stream: Output Markdown file.
    """
    output = None
    instructions = None

    # If the variable is defined somewhere in the plugin stack, use it.
    if self._plugin_stack:
      value = None
      for plugin_info in reversed(self._plugin_stack):
        if match in plugin_info["params"]:
          value = plugin_info["params"][match]
          break

      if value:
        output = value

    # Otherwise, it needs to be globally-defined.
    if not output and match == "username":
      output = "(TODO: Replace with username.)"
      instructions = ("On Google Code this would have been replaced with the "
                      "username of the current user, but GitHub has no "
                      "direct support for equivalent behavior. It has been "
                      "replaced with\n\t{0}\nConsider removing this altogether."
                      .format(output))
    elif not output and match == "email":
      output = "(TODO: Replace with email address.)"
      instructions = ("On Google Code this would have been replaced with the "
                      "email address of the current user, but GitHub has no "
                      "direct support for equivalent behavior. It has been "
                      "replaced with\n\t{0}\nConsider removing this altogether."
                      .format(output))
    elif not output and match == "project":
      if self._project:
        output = self._project
        instructions = (u"It has been replaced with static text containing the "
                        "name of the project:\n\t{0}".format(self._project))
      else:
        output = "(TODO: Replace with project name.)"
        instructions = ("Because no project name was specified, the text has "
                        "been replaced with:\n\t{0}".format(output))

    # Not defined anywhere, just treat as regular text.
    if not output:
      # Add surrounding %% back on.
      output = u"%%{0}%%".format(match)

    self._formatting_handler.HandleEscapedText(
        input_line,
        output_stream,
        output)
    if instructions:
      self._warning_method(
          input_line,
          u"A variable substitution was performed with %%{0}%%. {1}"
          .format(match, instructions))

  def _HandleTag(self, input_line, tag, output_stream):
    """Handle a tag, which has an opening and closing.

    Args:
      input_line: Current line number being processed.
      tag: The tag to handle.
      output_stream: Output Markdown file.
    """
    if tag not in self._open_tags:
      self._OpenTag(input_line, tag, output_stream)
    else:
      self._CloseTag(input_line, tag, output_stream)
