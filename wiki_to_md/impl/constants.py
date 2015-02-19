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
"""Constants used during conversion."""
import re


# These are the various different matching possibilities Google Code
# recognizes. As matches are made, the respective handler class method is
# is called, which can do what it wishes with the match.

# The pragmas:
PRAGMA_NAMES = ["summary", "labels", "sidebar"]
PRAGMA_RE = re.compile(r"^#(" + "|".join(PRAGMA_NAMES) + r")(.*)$")

# Whitespace:
WHITESPACE_RE = re.compile(r"\s+")
INDENT_RE = re.compile(r"\A\s*")

# Code blocks:
START_CODEBLOCK_RE = re.compile(r"^{{{$")
END_CODEBLOCK_RE = re.compile(r"^}}}$")

# Line rules. These rules consume an entire line:
LINE_FORMAT_RULES = [
    r"""(?P<HRule>
         ^
         ----+
         $
         )""",
    r"""(?P<Heading>
         ^
         =+\s*    # Matches the leading delimiter
         .*       # Matches the heading title text
         \s*=+\s* # Matches the trailing delimiter
         $
        )""",
]
LINE_FORMAT_RE = re.compile("(?x)" + "|".join(LINE_FORMAT_RULES), re.UNICODE)

# General formatting rules:
SIMPLE_FORMAT_RULE = r"""
    (?P<{0}>
      (?:
        (?<=\W|_)    # Match only if preceded by an authorized delimiter
        {1}           # The opening format character
      ) |
      (?:
        {1}           # Or match the closing format character...
        (?=\W|_)     # But only if followed by an authorized delimiter
      ) |

      (?:
        ^            # Or match the format character at the start of a line...
        {1}
      ) |
      (?:
        {1}           # Or at the end of a line.
        $
      )
    )
    """

URL_SCHEMA_RULE = r"(https?|ftp|nntp|news|mailto|telnet|file|irc)"
OPTIONAL_DESC_RULE = r"(?:\s+[^]]+)?"

VALID_PAGENAME = r"(([A-Za-z0-9][A-Za-z0-9_]*)?[A-Za-z0-9])"

# Link anchors use the Fragment ID pattern from RFC 1630.
# Dropping the quotes for security considerations.
XALPHA_RULE = r"[A-Za-z0-9%$-_@.&!*\(\),]"

# Only WikiWords matching this pattern are detected and autolinked in the text.
WIKIWORD_AUTOLINK_RULE = (
    r"(?:[A-Z][a-z0-9]+_*)+(?:[A-Z][a-z0-9]+)(?:[#]{0}*?)?".format(XALPHA_RULE))
WIKIWORD_RULE = r"(?:{0}?(?:[#]{1}*?)?)".format(VALID_PAGENAME, XALPHA_RULE)

# "Plugins" are anything that looks like an XML/HTML tag.
PLUGIN_NAME = r"[a-zA-Z0-9_\-]+"  # Matches a plugin name.
PLUGIN_ID = r"({0}:)?{0}".format(PLUGIN_NAME)  # Matches a namespace and name.
PLUGIN_PARAM = r"""({0})\s*=\s*("[^"]*"|'[^']*'|\S+)""".format(PLUGIN_NAME)
PLUGIN = r"<{0}(?:\s+{1})*\s*/?>".format(PLUGIN_ID, PLUGIN_PARAM)
PLUGIN_END = r"</{0}>".format(PLUGIN_ID)

PLUGIN_ID_RE = re.compile(PLUGIN_ID, re.UNICODE)
PLUGIN_PARAM_RE = re.compile(PLUGIN_PARAM, re.UNICODE)
PLUGIN_RE = re.compile(PLUGIN, re.UNICODE)
PLUGIN_END_RE = re.compile(PLUGIN_END, re.UNICODE)

TEXT_FORMAT_RULES = [
    SIMPLE_FORMAT_RULE.format("Bold", r"\*"),
    SIMPLE_FORMAT_RULE.format("Italic", "_"),
    SIMPLE_FORMAT_RULE.format("Strikethrough", "~~"),
    r"\^(?P<Superscript>.+?)\^",
    r",,(?P<Subscript>.+?),,",
    r"`(?P<InlineCode>.+?)`",
    r"\{\{\{(?P<InlineCode2>.+?)\}\}\}",
    r"""# Matches an entire table cell
        (?P<TableCell>
         (?:\|\|)+      # Any number of start markers, to support rowspan
         .*?            # Text of the table cell
         (?=\|\|)       # Assertion that we have a table cell end
         )""",
    r"(?P<TableRowEnd>\|\|\s*$)",
    r"""# Matches a freestanding URL in the source text.
        (?P<Url>
         \b(?:{0}://|(mailto:)) # Matches supported URL schemas
         [^\s'\"<]+             # Match at least one character that is
                                # authorized within a URL.
         [^\s'\"<.,}})\]]+      # After that, match all the way up to the first
                                # character that looks like a terminator.
        )""".format(URL_SCHEMA_RULE),
    r"""# Matches bracketed URLs: [http://foo.bar An optional description]
        (?P<UrlBracket>
         \[
          (?:{0}://|(mailto:)) # Matches supported URL schemas
          [^]\s]+              # Matches up to the closing bracket or whitespace
          {1}                  # Matches the optional URL description
         \]
        )""".format(URL_SCHEMA_RULE, OPTIONAL_DESC_RULE),
    r"""# Matches a WikiWord embedded in the text.
        (?:
         (?<![A-Za-z0-9\[])  # Matches the WikiWord only if it's not preceded
                             # by an alphanumeric character or a bracket.

         (?P<WikiWord>
          !?   # The WikiWord is preceded by an optional exclamation
               # mark, which makes it not a link. However, we still
               # need to match it as being a link, so that we can strip
               # the exclamation mark from the resulting plaintext WikiWord.

          {0}  # The WikiWord itself
         )

         (?![A-Za-z0-9]) # Matches the WikiWord only if it's not followed
                         # by alphanumeric characters.
        )""".format(WIKIWORD_AUTOLINK_RULE),
    r"""# Matches a forced/named WikiLink: [WikiWord an optional description]
        (?P<WikiWordBracket>
         \[
          {0}  # Matches the WikiWord
          {1}  # Matches the optional WikiLink description
         \]
        )""".format(WIKIWORD_RULE, OPTIONAL_DESC_RULE),
    r"""# Matches an issue reference.
        (?P<IssueLink>
        (
        \b([Ii][Ss][Ss][Uu][Ee]|[Bb][Uu][Gg])\s*\#?
        )
        \d+\b
        )
        """,
    r"""# Matches a revision reference.
        (?P<RevisionLink>
        (
        \b[Rr]([Ee][Vv][Ii][Ss][Ii][Oo][Nn]\s*\#?)?
        )
        \d+\b
        )
        """,
    r"(?P<Plugin>{0})".format(PLUGIN),
    r"(?P<PluginEnd>{0})".format(PLUGIN_END),
    r"""# Matches a variable being used, defined in a plugin or globally.
        %%(?P<Variable>[\w|_|\-]+)%%"""
]
TEXT_FORMAT_RE = re.compile("(?x)" + "|".join(TEXT_FORMAT_RULES), re.UNICODE)

# For verification of YouTube video IDs.
YOUTUBE_VIDEO_ID_RE = re.compile("^[a-zA-Z0-9_-]+$")

# List types:
LIST_TYPES = {
    "1": "numeric",
    "#": "numeric",
    "*": "bullet",
    " ": "blockquote",
}
