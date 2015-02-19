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
"""Handles converting of formatting."""
import cgi

from . import constants


class FormattingHandler(object):
  """Class that handles the conversion of formatting."""

  # Links with these URL schemas are auto-linked by GFM.
  _GFM_AUTO_URL_SCHEMAS = ("http://", "https://")

  # Images that were inlined automatically by Wiki syntax
  # had to have these URL schemas and image extensions.
  _IMAGE_URL_SCHEMAS = ("http://", "https://", "ftp://")
  _IMAGE_EXTENSIONS = (".png", ".gif", ".jpg", ".jpeg", ".svg")

  # Template for linking to a video.
  _VIDEO_TEMPLATE = (
      "<a href='http://www.youtube.com/watch?feature=player_embedded&v={0}' "
      "target='_blank'><img src='http://img.youtube.com/vi/{0}/0.jpg' "
      "width='{1}' height={2} /></a>")

  # Formatting tags for list-to-HTML conversion.
  _HTML_LIST_TAGS = {
      "Numeric list": {
          "ListTag": "ol",
          "ItemTag": "li",
      },
      "Bulleted list": {
          "ListTag": "ul",
          "ItemTag": "li",
      },
      "Blockquote": {
          "ListTag": "blockquote",
          "ItemTag": None,
      },
  }

  # Formatting tags for formatting-to-HTML conversion.
  _HTML_FORMAT_TAGS = {
      "Bold": {
          "Markdown": "**",
          "HTML": "b",
      },
      "Italic": {
          "Markdown": "_",
          "HTML": "i",
      },
      "Strikethrough": {
          "Markdown": "~~",
          "HTML": "del",
      },
  }

  # How a single indentation is outputted.
  _SINGLE_INDENTATION = " " * 2

  def __init__(self, warning_method, project, issue_map, symmetric_headers):
    """Create a formatting handler.

    Args:
        warning_method: A function to call to display a warning message.
        project: The name of the Google Code project for the Wiki page.
        issue_map: A dictionary of Google Code issues to GitHub issues.
        symmetric_headers: True if header denotations are symmetric.
    """
    self._warning_method = warning_method
    self._project = project
    self._issue_map = issue_map
    self._symmetric_headers = symmetric_headers

    # GFM has a quirk with nested blockquotes where a blank line is needed
    # after closing a nested blockquote while continuing into another.
    self._last_blockquote_indent = 0

    # GFM will not apply formatting if whitespace surrounds the text being
    # formatted, but Wiki will. To work around this, we maintain a buffer
    # of text to be outputted, and when the tag is closed we can trim the
    # buffer before applying formatting. If the trimmed buffer is empty, we
    # can omit the formatting altogether to avoid GFM rendering issues.
    self._format_buffer = []

    # GitHub won't render formatting within HTML tags. Track if this is the
    # case so we can issue a warning and try a work-around.
    self._in_html = 0  # Number of tags currently open.
    self._in_code_block = False  # If we're in a code block in HTML.
    self._has_written_text = False  # If we've written text since the last tag.
    self._list_tags = []  # If writing HTML for lists, the current list tags.
    self._table_status = None  # Where we are in outputting an HTML table.

    # GitHub doesn't support HTML comments, so as a workaround we give
    # a bogus and empty <a> tag, which renders as nothing.
    self._in_comment = False

  def HandleHeaderOpen(self, input_line, output_stream, header_level):
    """Handle the output for opening a header.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        header_level: The header level.
    """
    if self._in_html:
      tag = "h{0}".format(header_level)
      self.HandleHtmlOpen(input_line, output_stream, tag, {}, False)
    else:
      self._Write("#" * header_level + " ", output_stream)

  def HandleHeaderClose(
      self,
      input_line,
      output_stream,
      header_level):
    """Handle the output for closing a header.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        header_level: The header level.
    """
    if self._in_html:
      tag = "h{0}".format(header_level)
      self.HandleHtmlClose(input_line, output_stream, tag)
    else:
      if self._symmetric_headers:
        self._Write(" " + "#" * header_level, output_stream)

  def HandleHRule(self, input_line, output_stream):
    """Handle the output for a horizontal rule.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    if self._in_html:
      self.HandleHtmlOpen(input_line, output_stream, "hr", {}, True)
    else:
      # One newline needed before to separate from text, and not make a header.
      self._Write("\n---\n", output_stream)

  def HandleCodeBlockOpen(self, input_line, output_stream, specified_language):
    """Handle the output for starting a code block.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        specified_language: Language for the code block, or None.
    """
    if self._in_html:
      self._PrintHtmlWarning(input_line, "Code")
      self.HandleHtmlOpen(input_line, output_stream, "pre", {}, False)
      self.HandleHtmlOpen(input_line, output_stream, "code", {}, False)
    else:
      if not specified_language:
        specified_language = ""
      self._Write("```{0}\n".format(specified_language), output_stream)
    self._in_code_block = True

  def HandleCodeBlockClose(self, input_line, output_stream):
    """Handle the output for ending a code block.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    self._in_code_block = False
    if self._in_html:
      self.HandleHtmlClose(input_line, output_stream, "code")
      self.HandleHtmlClose(input_line, output_stream, "pre")
    else:
      self._Write("```", output_stream)

  def HandleNumericListOpen(
      self,
      input_line,
      output_stream,
      indentation_level):
    """Handle the output for the opening of a numeric list item.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        indentation_level: The indentation level for the item.
    """
    if self._in_html:
      self._HandleHtmlListOpen(
          input_line,
          output_stream,
          indentation_level,
          "Numeric list")
    else:
      self._Indent(output_stream, indentation_level)
      # Just using any number implies a numbered item,
      # so we take the easy route.
      self._Write("1. ", output_stream)

  def HandleBulletListOpen(
      self,
      input_line,
      output_stream,
      indentation_level):
    """Handle the output for the opening of a bulleted list item.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        indentation_level: The indentation level for the item.
    """
    if self._in_html:
      self._HandleHtmlListOpen(
          input_line,
          output_stream,
          indentation_level,
          "Bulleted list")
    else:
      self._Indent(output_stream, indentation_level)
      self._Write("* ", output_stream)

  def HandleBlockQuoteOpen(
      self,
      input_line,
      output_stream,
      indentation_level):
    """Handle the output for the opening of a block quote line.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        indentation_level: The indentation level for the item.
    """
    if self._in_html:
      self._HandleHtmlListOpen(
          input_line,
          output_stream,
          indentation_level,
          "Blockquote")
    else:
      if self._last_blockquote_indent > indentation_level:
        self._Write("\n", output_stream)
      self._last_blockquote_indent = indentation_level
      # Blockquotes are nested not by indentation but by nesting.
      self._Write("> " * indentation_level, output_stream)

  def HandleListClose(self, input_line, output_stream):
    """Handle the output for the closing of a list.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    if self._in_html:
      self._HandleHtmlListClose(input_line, output_stream)

  def HandleParagraphBreak(self, unused_input_line, output_stream):
    """Handle the output for a new paragraph.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    self._Write("\n", output_stream)

  def HandleBoldOpen(self, input_line, unused_output_stream):
    """Handle the output for starting bold formatting.

    Args:
        input_line: Current line number being processed.
        unused_output_stream: Output Markdown file.
    """
    if self._in_html:
      self._PrintHtmlWarning(input_line, "Bold")

    # Open up another buffer.
    self._format_buffer.append("")

  def HandleBoldClose(self, input_line, output_stream):
    """Handle the output for ending bold formatting.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    self._HandleFormatClose(input_line, output_stream, "Bold")

  def HandleItalicOpen(self, input_line, unused_output_stream):
    """Handle the output for starting italic formatting.

    Args:
        input_line: Current line number being processed.
        unused_output_stream: Output Markdown file.
    """
    if self._in_html:
      self._PrintHtmlWarning(input_line, "Italic")

    # Open up another buffer.
    self._format_buffer.append("")

  def HandleItalicClose(self, input_line, output_stream):
    """Handle the output for ending italic formatting.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    self._HandleFormatClose(input_line, output_stream, "Italic")

  def HandleStrikethroughOpen(self, input_line, unused_output_stream):
    """Handle the output for starting strikethrough formatting.

    Args:
        input_line: Current line number being processed.
        unused_output_stream: Output Markdown file.
    """
    if self._in_html:
      self._PrintHtmlWarning(input_line, "Strikethrough")

    # Open up another buffer.
    self._format_buffer.append("")

  def HandleStrikethroughClose(self, input_line, output_stream):
    """Handle the output for ending strikethrough formatting.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    self._HandleFormatClose(input_line, output_stream, "Strikethrough")

  def HandleSuperscript(self, unused_input_line, output_stream, text):
    """Handle the output for superscript text.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
        text: The text to output.
    """
    # Markdown currently has no dedicated markup for superscript.
    self._Write("<sup>{0}</sup>".format(text), output_stream)

  def HandleSubscript(self, unused_input_line, output_stream, text):
    """Handle the output for subscript text.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
        text: The text to output.
    """
    # Markdown currently has no dedicated markup for subscript.
    self._Write("<sub>{0}</sub>".format(text), output_stream)

  def HandleInlineCode(self, input_line, output_stream, code):
    """Handle the output for a code block.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        code: The code inlined.
    """
    if self._in_html:
      self.HandleHtmlOpen(input_line, output_stream, "code", {}, False)
      self.HandleText(input_line, output_stream, cgi.escape(code))
      self.HandleHtmlClose(input_line, output_stream, "code")
    else:
      # To render backticks within inline code, the surrounding tick count
      # must be one greater than the number of consecutive ticks in the code.
      # E.g.:
      #   `this is okay, no ticks in the code`
      #   `` `one consecutive tick in the code implies two in the delimiter` ``
      #   ``` `` `and two consecutive ticks in here implies three -> ```
      max_consecutive_ticks = 0
      consecutive_ticks = 0
      for char in code:
        if char == "`":
          consecutive_ticks += 1
          max_consecutive_ticks = max(max_consecutive_ticks, consecutive_ticks)
        else:
          consecutive_ticks = 0

      surrounding_ticks = "`" * (max_consecutive_ticks + 1)
      self._Write("{0} {1} {0}".format(surrounding_ticks, code), output_stream)

  def HandleTableCellBorder(self, input_line, output_stream):
    """Handle the output for a table cell border.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    if self._in_html:
      if not self._table_status:
        # Starting a new table.
        self._PrintHtmlWarning(input_line, "Table")
        self.HandleHtmlOpen(input_line, output_stream, "table", {}, False)
        self.HandleHtmlOpen(input_line, output_stream, "thead", {}, False)
        self.HandleHtmlOpen(input_line, output_stream, "th", {}, False)
        self._table_status = "header"
      elif self._table_status == "header":
        # Header cell. Close the previous cell, open the next one.
        self.HandleHtmlClose(input_line, output_stream, "th")
        self.HandleHtmlOpen(input_line, output_stream, "th", {}, False)
      elif self._table_status == "rowstart":
        # First row cell.
        self.HandleHtmlOpen(input_line, output_stream, "tr", {}, False)
        self.HandleHtmlOpen(input_line, output_stream, "td", {}, False)
        self._table_status = "row"
      elif self._table_status == "row":
        # Row cell. Close the previous cell, open the next one.
        self.HandleHtmlClose(input_line, output_stream, "td")
        self.HandleHtmlOpen(input_line, output_stream, "td", {}, False)
    else:
      self._Write("|", output_stream)

  def HandleTableRowEnd(self, input_line, output_stream):
    """Handle the output for a table row end.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    if self._in_html:
      if self._table_status == "header":
        # Closing header. Close the previous cell and header, start the body.
        self.HandleHtmlClose(input_line, output_stream, "th")
        self.HandleHtmlClose(input_line, output_stream, "thead")
        self.HandleHtmlOpen(input_line, output_stream, "tbody", {}, False)
      elif self._table_status == "row":
        # Closing row. Close the previous cell and row.
        self.HandleHtmlClose(input_line, output_stream, "td")
        self.HandleHtmlClose(input_line, output_stream, "tr")
      self._table_status = "rowstart"
    else:
      self._Write("|", output_stream)

  def HandleTableClose(self, input_line, output_stream):
    """Handle the output for a table end.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    if self._in_html:
      # HandleTableRowEnd will have been called by this point.
      # All we need to do is close the body and table.
      self.HandleHtmlClose(input_line, output_stream, "tbody")
      self.HandleHtmlClose(input_line, output_stream, "table")
      self._table_status = None

  def HandleTableHeader(self, input_line, output_stream, columns):
    """Handle the output for starting a table header.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        columns: Column sizes.
    """
    if self._in_html:
      return

    self.HandleText(input_line, output_stream, "\n")

    for column_width in columns:
      self.HandleTableCellBorder(input_line, output_stream)

      # Wiki tables are left-aligned, which takes one character to specify.
      self._Write(":{0}".format("-" * (column_width - 1)), output_stream)

    self.HandleTableCellBorder(input_line, output_stream)

  def HandleLink(self, input_line, output_stream, target, description):
    """Handle the output of a link.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        target: The target URL of the link.
        description: The description for the target.
    """
    # There are six cases to handle in general:
    # 1. Image link with image description:
    #   Link to image, using image from description as content.
    # 2. Image link with non-image description:
    #   Link to image, using description text as content.
    # 3. Image link with no description:
    #   Inline image.
    # 4. URL link with image description:
    #   Link to URL, using image from description as content.
    # 5. URL link with non-image description:
    #   Link to URL, using description text as content.
    # 6. URL link with no description:
    #   Link to URL, using URL as content.
    # Only in case 3 is no actual link present.
    is_image = target.endswith(self._IMAGE_EXTENSIONS)
    is_image_description = (description and
                            description.startswith(self._IMAGE_URL_SCHEMAS) and
                            description.endswith(self._IMAGE_EXTENSIONS))

    if self._in_html:
      self._PrintHtmlWarning(input_line, "Link")

      # Handle inline image case.
      if is_image and not description:
        self.HandleHtmlOpen(
            input_line,
            output_stream,
            "img",
            {"src": target},
            True)
      else:
        # Handle link cases.
        self.HandleHtmlOpen(
            input_line,
            output_stream,
            "a",
            {"href": target},
            False)
        if is_image_description:
          self.HandleHtmlOpen(
              input_line,
              output_stream,
              "img",
              {"src": description},
              True)
        else:
          description = description or target
          self._Write(cgi.escape(description), output_stream)
        self.HandleHtmlClose(input_line, output_stream, "a")
    else:
      # If description is None, this means that only the URL was given. We'd
      # like to let GFM auto-link it, because it's prettier. However, while Wiki
      # syntax would auto-link a variety of URL schemes, GFM only supports http
      # and https. In other cases and in the case of images, we explicitly link.
      is_autolinkable = target.startswith(self._GFM_AUTO_URL_SCHEMAS)
      autolink = (description is None) and is_autolinkable and (not is_image)

      if autolink:
        self._Write(target, output_stream)
      else:
        # If the descriptive text looks like an image URL, Wiki syntax would
        # make the link description an inlined image. We do this by setting
        # the output description to the syntax used to inline an image.
        if is_image_description:
          description = "![]({0})".format(description)
        elif description:
          description = self._Escape(description)
        else:
          description = target
          is_image_description = is_image

        # Prefix ! if linking to an image without a text description.
        prefix = "!" if is_image and is_image_description else ""

        output = "{0}[{1}]({2})".format(prefix, description, target)
        self._Write(output, output_stream)

  def HandleWiki(self, input_line, output_stream, target, text):
    """Handle the output of a wiki link.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        target: The target URL of the link.
        text: The description for the target.
    """
    # A wiki link is just like a regular link, except under the wiki directory.
    # At this point we make the text equal to the original target if unset.
    self.HandleLink(input_line, output_stream, "wiki/" + target, text or target)

  def HandleIssue(self, input_line, output_stream, prefix, issue):
    """Handle the output for an auto-linked issue.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        prefix: The text that came before the issue number.
        issue: The issue number.
    """
    handled = False

    # Preferred handler is to map the Google Code issue to a GitHub issue.
    if self._issue_map and issue in self._issue_map:
      migrated_issue_url = self._issue_map[issue]
      migrated_issue = migrated_issue_url.rsplit("/", 1)[1]
      self.HandleLink(
          input_line,
          output_stream,
          migrated_issue_url,
          "{0}{1}".format(prefix, migrated_issue))
      handled = True

      instructions = ("In the output, it has been linked to the migrated issue "
                      "on GitHub: {0}. Please verify this issue on GitHub "
                      "corresponds to the original issue on Google Code. "
                      .format(migrated_issue))
    elif self._issue_map:
      instructions = ("However, it was not found in the issue migration map; "
                      "please verify that this issue has been correctly "
                      "migrated to GitHub and that the issue mapping is put "
                      "in the issue migration map file. ")
    else:
      instructions = ("However, no issue migration map was specified. You "
                      "can use issue_migration.py to migrate your Google "
                      "Code issues to GitHub, and supply the resulting issue "
                      "migration map file to this converter. Your old issues "
                      "will be auto-linked to your migrated issues. ")

    # If we couldn't handle it in the map, try linking to the old issue.
    if not handled and self._project:
      old_link = ("https://code.google.com/p/{0}/issues/detail?id={1}"
                  .format(self._project, issue))
      self.HandleLink(
          input_line,
          output_stream,
          old_link,
          "{0}{1}".format(prefix, issue))
      handled = True

      instructions += ("As a placeholder, the text has been modified to "
                       "link to the original Google Code issue page:\n\t{0}"
                       .format(old_link))
    elif not handled:
      instructions += ("Additionally, because no project name was specified "
                       "the issue could not be linked to the original Google "
                       "Code issue page.")

    # Couldn't map it to GitHub nor could we link to the old issue.
    if not handled:
      output = "{0}{1} (on Google Code)".format(prefix, issue)
      self._Write(output, output_stream)
      handled = True

      instructions += ("The auto-link has been removed and the text has been "
                       "modified from '{0}{1}' to '{2}'."
                       .format(prefix, issue, output))

    self._warning_method(
        input_line,
        "Issue {0} was auto-linked. {1}".format(issue, instructions))

  def HandleRevision(self, input_line, output_stream, prefix, revision):
    """Handle the output for an auto-linked issue.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        prefix: The text that came before the revision number.
        revision: The revision number.
    """
    # Google Code only auto-linked revision numbers, not hashes, so
    # revision auto-linking cannot be done for the conversion.
    if self._project:
      old_link = ("https://code.google.com/p/{0}/source/detail?r={1}"
                  .format(self._project, revision))
      self.HandleLink(
          input_line,
          output_stream,
          old_link,
          "{0}{1}".format(prefix, revision))

      instructions = ("As a placeholder, the text has been modified to "
                      "link to the original Google Code source page:\n\t{0}"
                      .format(old_link))
    else:
      output = "{0}{1} (on Google Code)".format(prefix, revision)
      self._Write(output, output_stream)

      instructions = ("Additionally, because no project name was specified "
                      "the revision could not be linked to the original "
                      "Google Code source page. The auto-link has been removed "
                      "and the text has been modified from '{0}{1}' to '{2}'."
                      .format(prefix, revision, output))

    self._warning_method(
        input_line,
        "Revision {0} was auto-linked. SVN revision numbers are not sensible "
        "in Git; consider updating this link or removing it altogether. {1}"
        .format(revision, instructions))

  def HandleHtmlOpen(
      self,
      unused_input_line,
      output_stream,
      html_tag,
      params,
      has_end):
    """Handle the output for an opening HTML tag.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
        html_tag: The HTML tag name.
        params: The parameters for the tag.
        has_end: True if the tag was self-closed.
    """
    core_params = self._SerializeHtmlParams(params)
    core = "{0}{1}".format(html_tag, core_params)

    if has_end:
      output = "<{0} />".format(core)
    else:
      output = "<{0}>".format(core)
      self._in_html += 1

    self._Write(output, output_stream)

    self._has_written_text = False

  def HandleHtmlClose(self, unused_input_line, output_stream, html_tag):
    """Handle the output for an closing HTML tag.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
        html_tag: The HTML tag name.
    """
    self._Write("</{0}>".format(html_tag), output_stream)
    self._in_html -= 1
    self._has_written_text = False

  def HandleGPlusOpen(self, input_line, output_stream, unused_params):
    """Handle the output for opening a +1 button.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        unused_params: The parameters for the tag.
    """
    self._warning_method(
        input_line,
        "A Google+ +1 button was embedded on this page, but GitHub does not "
        "currently support this. Should it become supported in the future, "
        "see https://developers.google.com/+/web/+1button/ for more "
        "information.\nIt has been removed.")

  def HandleGPlusClose(self, unused_input_line, unused_output_stream):
    """Handle the output for closing a +1 button.

    Args:
        unused_input_line: Current line number being processed.
        unused_output_stream: Output Markdown file.
    """
    pass

  def HandleCommentOpen(self, input_line, output_stream):
    """Handle the output for opening a comment.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    self._warning_method(
        input_line,
        "A comment was used in the wiki file, but GitHub does not currently "
        "support Markdown or HTML comments. As a work-around, the comment will "
        "be placed in a bogus and empty <a> tag.")
    self._Write("<a href='Hidden comment: ", output_stream)
    self._in_comment = True

  def HandleCommentClose(self, unused_input_line, output_stream):
    """Handle the output for closing a comment.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    self._in_comment = False
    self._Write("'></a>", output_stream)

  def HandleVideoOpen(self, input_line, output_stream, video_id, width, height):
    """Handle the output for opening a video.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        video_id: The video ID to play.
        width: Width of the resulting widget.
        height: Height of the resulting widget.
    """
    self._warning_method(
        input_line,
        "GFM does not support embedding the YouTube player directly. Instead "
        "an image link to the video is being used, maintaining sizing options.")

    output = self._VIDEO_TEMPLATE.format(video_id, width, height)
    self._Write(output, output_stream)

  def HandleVideoClose(self, unused_input_line, output_stream):
    """Handle the output for closing a video.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    # Everything was handled on the open side.
    pass

  def HandleText(self, unused_input_line, output_stream, text):
    """Handle the output of raw text.

    Args:
        unused_input_line: Current line number being processed.
        output_stream: Output Markdown file.
        text: The text to output.
    """
    self._Write(text, output_stream)
    self._has_written_text = True

  def HandleEscapedText(self, input_line, output_stream, text):
    """Handle the output of text, which should be escaped for Markdown.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        text: The text to output.
    """
    # If we're in HTML, Markdown isn't processed anyway.
    if self._in_html:
      self.HandleText(input_line, output_stream, text)
    else:
      self.HandleText(input_line, output_stream, self._Escape(text))

  def _PrintHtmlWarning(self, input_line, kind):
    """Warn about HTML translation being performed.

    Args:
        input_line: Current line number being processed.
        kind: The kind of tag being changed.
    """
    self._warning_method(
        input_line,
        "{0} markup was used within HTML tags. Because GitHub does not "
        "support this, the tags have been translated to HTML. Please verify "
        "that the formatting is correct.".format(kind))

  def _HandleHtmlListOpen(
      self,
      input_line,
      output_stream,
      indentation_level,
      kind):
    """Handle the output for opening an HTML list.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        indentation_level: The indentation level for the item.
        kind: The kind of list being opened.
    """
    # Determine if this is a new list, and if a previous list was closed.
    if self._list_tags:
      top_tag = self._list_tags[-1]
      if top_tag["indent"] != indentation_level:
        # Opening a new nested list. Indentation level will always be greater,
        # because for it to have gone down, the list would have been closed.
        new_list = True
        closing = False
      elif top_tag["kind"] != kind:
        # Closed the previous list, started a new one.
        new_list = True
        closing = True
      else:
        # Same list, already opened.
        new_list = False
        closing = False
    else:
      new_list = True
      closing = False

    # If we need to, close the prior list.
    if closing:
      self._HandleHtmlListClose(input_line, output_stream)

    # Grab the tags we'll be using.
    list_tag = self._HTML_LIST_TAGS[kind]["ListTag"]
    item_tag = self._HTML_LIST_TAGS[kind]["ItemTag"]

    # If this is a new list, note it in the stack and open it.
    if new_list:
      new_tag = {
          "indent": indentation_level,
          "kind": kind,
      }
      self._list_tags.append(new_tag)

      self._PrintHtmlWarning(input_line, kind)
      self.HandleHtmlOpen(input_line, output_stream, list_tag, {}, False)
    else:
      # Not a new list, close the previously outputted item.
      if item_tag:
        self.HandleHtmlClose(input_line, output_stream, item_tag)

    # Open up a new list item
    if item_tag:
      self.HandleHtmlOpen(input_line, output_stream, item_tag, {}, False)

  def _HandleHtmlListClose(self, input_line, output_stream):
    """Handle the output for closing an HTML list.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
    """
    top_tag = self._list_tags[-1]
    kind = top_tag["kind"]
    self._list_tags.pop()

    # Grab the tags we'll be using.
    list_tag = self._HTML_LIST_TAGS[kind]["ListTag"]
    item_tag = self._HTML_LIST_TAGS[kind]["ItemTag"]

    # Close the previously outputted item and the list.
    if item_tag:
      self.HandleHtmlClose(input_line, output_stream, item_tag)

    self.HandleHtmlClose(input_line, output_stream, list_tag)

  def _HandleFormatClose(self, input_line, output_stream, kind):
    """Handle the output of a closing format tag.

    Args:
        input_line: Current line number being processed.
        output_stream: Output Markdown file.
        kind: The formatting kind.
    """
    if self._format_buffer:
      # End redirection.
      format_buffer = self._format_buffer[-1]
      self._format_buffer.pop()

      # Don't do anything if we didn't buffer, or it was only whitespace.
      format_buffer = format_buffer.strip()
      if not format_buffer:
        return

      if self._in_html:
        tag = self._HTML_FORMAT_TAGS[kind]["HTML"]
        self.HandleHtmlOpen(input_line, output_stream, tag, {}, False)
        self.HandleText(input_line, output_stream, format_buffer)
        self.HandleHtmlClose(input_line, output_stream, tag)
      else:
        tag = self._HTML_FORMAT_TAGS[kind]["Markdown"]
        self._Write("{0}{1}{0}".format(tag, format_buffer), output_stream)

    else:
      self._warning_method(input_line, "Re-closed '{0}', ignoring.".format(tag))

  def _Indent(self, output_stream, indentation_level):
    """Output indentation.

    Args:
        output_stream: Output Markdown file.
        indentation_level: Number of indentations to output.
    """
    self._Write(self._SINGLE_INDENTATION * indentation_level, output_stream)

  def _Escape(self, text):
    """Escape Wiki text to be suitable in Markdown.

    Args:
        text: Input Wiki text.
    Returns:
        Escaped text for Markdown.
    """
    text = text.replace("*", r"\*")
    text = text.replace("_", r"\_")

    # If we find a plugin-like bit of text, escape the angle-brackets.
    for plugin_re in [constants.PLUGIN_RE, constants.PLUGIN_END_RE]:
      while plugin_re.search(text):
        match = plugin_re.search(text)
        before_match = text[:match.start()]
        after_match = text[match.end():]
        escaped_match = match.group(0).replace("<", "&lt;").replace(">", "&gt;")
        text = "{0}{1}{2}".format(before_match, escaped_match, after_match)

    # In Markdown, if a newline is preceeded by two spaces it breaks the line.
    # For Wiki text, this is not the case, so we strip such endings off.
    while text.endswith("  \n"):
      text = text[:-len("  \n")] + "\n"

    return text

  def _SerializeHtmlParams(self, params):
    """Serialize parameters for an HTML tag.

    Args:
        params: The parameters for the tag.
    Returns:
        Serialized parameters.
    """
    core_params = ""
    for name, value in params.items():
      if "'" not in value:
        quote = "'"
      else:
        quote = "\""
      core_params += " {0}={1}{2}{1}".format(name, quote, value)

    return core_params

  def _Write(self, text, output_stream):
    """Write text to the output stream, taking into account any redirection.

    Args:
        text: Input raw text.
        output_stream: Output Markdown file.
    """
    if not text:
      return

    if not self._in_comment and self._in_html:
      if self._in_code_block:
        text = cgi.escape(text)

      if self._in_code_block or self._has_written_text:
        text = text.replace("\n", "<br>\n")

    if self._in_comment:
      text = text.replace("'", "\"")

    if self._format_buffer:
      # Buffering is occuring, add to buffer.
      self._format_buffer[-1] += text
    else:
      # No buffering occuring, just output it.
      output_stream.write(text)
