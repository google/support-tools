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
"""Tests for wiki2gfm."""
import codecs
import StringIO
import unittest

from impl import converter
from impl import formatting_handler
from impl import pragma_handler


class BaseTest(unittest.TestCase):
  """Base test for wiki2gfm tests."""

  def setUp(self):
    """Create a base test."""
    self.warnings = []
    self.output = StringIO.StringIO()

    self.pragma_handler = pragma_handler.PragmaHandler(self._TrackWarning)
    self.formatting_handler = formatting_handler.FormattingHandler(
        self._TrackWarning,
        project="test",
        issue_map={123: "https://github.com/abcxyz/test/issues/789"},
        symmetric_headers=False)
    self.converter = converter.Converter(
        self.pragma_handler,
        self.formatting_handler,
        self._TrackWarning,
        project="test",
        wikipages=["TestPage"])

  def assertOutput(self, expected_output):
    """Assert that specific output was written.

    Args:
        expected_output: The expected value of the output.
    """
    self.assertEquals(expected_output, self.output.getvalue())

  def assertNoOutput(self, expected_output):
    self.assertNotEqual(expected_output, self.output.getvalue())

  def assertWarning(self, warning_contents, occurrences=1):
    """Assert that a warning was issued containing the given contents.

    This searches all tracked warnings for the contents.

    Args:
        warning_contents: Text that the warning was expected to contain.
        occurrences: The number of occurrences of the warning contents.
    """
    occurrences_found = 0
    for warning in self.warnings:
      if warning_contents in warning[1]:
        occurrences_found += 1

    if occurrences_found != occurrences:
      self.fail("Failed to find '{0}' in {1} warnings (found it in {2})."
                .format(warning_contents, occurrences, occurrences_found))

  def assertNoWarnings(self):
    """Assert that no warnings were issued."""
    self.assertListEqual([], self.warnings)

  def _TrackWarning(self, input_line, message):
    """Track a warning by storing it in memory.

    Args:
      input_line: Line the warning was issued on.
      message: The warning message.
    """
    self.warnings.append((input_line, message))


class TestPragmaHandler(BaseTest):
  """Tests the pragma handler."""

  def testSummaryPragmaGivesWarning(self):
    self.pragma_handler.HandlePragma(1, self.output, "summary", "abc")

    self.assertWarning("summary")

  def testSidebarPragmaGivesWarning(self):
    self.pragma_handler.HandlePragma(1, self.output, "sidebar", "abc")

    self.assertWarning("sidebar")

  def testUnknownPragmaGivesWarning(self):
    self.pragma_handler.HandlePragma(1, self.output, "fail!", "abc")

    self.assertWarning("fail!")


class TestFormattingHandler(BaseTest):
  """Tests the formatting handler."""

  def testHandleHeaderOpen(self):
    self.formatting_handler.HandleHeaderOpen(1, self.output, 3)

    self.assertOutput("### ")
    self.assertNoWarnings()

  def testHandleHeaderOpenInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleHeaderOpen(1, self.output, 3)

    self.assertOutput("<h3>")
    self.assertNoWarnings()

  def testHandleHeaderClose(self):
    self.formatting_handler.HandleHeaderClose(1, self.output, 3)

    self.assertOutput("")  # No header closing markup by default.
    self.assertNoWarnings()

  def testHandleHeaderCloseInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleHeaderClose(1, self.output, 3)

    self.assertOutput("</h3>")
    self.assertNoWarnings()

  def testHandleHeaderCloseSymmetric(self):
    self.formatting_handler._symmetric_headers = True
    self.formatting_handler.HandleHeaderClose(1, self.output, 3)

    self.assertOutput(" ###")
    self.assertNoWarnings()

  def testHandleHeaderCloseSymmetricInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler._symmetric_headers = True
    self.formatting_handler.HandleHeaderClose(1, self.output, 3)

    self.assertOutput("</h3>")
    self.assertNoWarnings()

  def testHandleHRule(self):
    self.formatting_handler.HandleHRule(1, self.output)

    self.assertOutput("\n---\n")
    self.assertNoWarnings()

  def testHandleHRuleInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleHRule(1, self.output)

    self.assertOutput("<hr />")
    self.assertNoWarnings()

  def testHandleCodeBlockOpen(self):
    self.formatting_handler.HandleCodeBlockOpen(1, self.output, None)

    self.assertOutput("```\n")
    self.assertNoWarnings()

  def testHandleCodeBlockOpenInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleCodeBlockOpen(1, self.output, None)

    self.assertOutput("<pre><code>")
    self.assertWarning("Code markup was used")

  def testHandleCodeBlockOpenWithLanguage(self):
    self.formatting_handler.HandleCodeBlockOpen(1, self.output, "idris")

    self.assertOutput("```idris\n")
    self.assertNoWarnings()

  def testHandleCodeBlockOpenWithLanguageInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleCodeBlockOpen(1, self.output, "idris")

    self.assertOutput("<pre><code>")
    self.assertWarning("Code markup was used")

  def testHandleCodeBlockClose(self):
    self.formatting_handler.HandleCodeBlockClose(1, self.output)

    self.assertOutput("```")
    self.assertNoWarnings()

  def testHandleCodeBlockCloseInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleCodeBlockClose(1, self.output)

    self.assertOutput("</code></pre>")
    self.assertNoWarnings()

  def testHandleNumericList(self):
    self.formatting_handler.HandleNumericListOpen(1, self.output, 1)
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleNumericListOpen(2, self.output, 1)
    self.formatting_handler.HandleText(2, self.output, "b\n")
    self.formatting_handler.HandleNumericListOpen(3, self.output, 2)
    self.formatting_handler.HandleText(3, self.output, "c\n")
    self.formatting_handler.HandleListClose(4, self.output)  # Closing 2.
    self.formatting_handler.HandleNumericListOpen(4, self.output, 1)
    self.formatting_handler.HandleText(4, self.output, "d\n")
    self.formatting_handler.HandleListClose(5, self.output)  # Closing 1.

    self.assertOutput("  1. a\n  1. b\n    1. c\n  1. d\n")
    self.assertNoWarnings()

  def testHandleNumericListInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleNumericListOpen(1, self.output, 1)
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleNumericListOpen(2, self.output, 1)
    self.formatting_handler.HandleText(2, self.output, "b\n")
    self.formatting_handler.HandleNumericListOpen(3, self.output, 2)
    self.formatting_handler.HandleText(3, self.output, "c\n")
    self.formatting_handler.HandleListClose(4, self.output)  # Closing 2.
    self.formatting_handler.HandleNumericListOpen(4, self.output, 1)
    self.formatting_handler.HandleText(4, self.output, "d\n")
    self.formatting_handler.HandleListClose(5, self.output)  # Closing 1.

    self.assertOutput("<ol><li>a\n</li><li>b\n<ol><li>c\n</li></ol></li>"
                      "<li>d\n</li></ol>")
    self.assertWarning("Numeric list markup was used", occurrences=2)

  def testHandleBulletList(self):
    self.formatting_handler.HandleBulletListOpen(1, self.output, 1)
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleBulletListOpen(2, self.output, 1)
    self.formatting_handler.HandleText(2, self.output, "b\n")
    self.formatting_handler.HandleBulletListOpen(3, self.output, 2)
    self.formatting_handler.HandleText(3, self.output, "c\n")
    self.formatting_handler.HandleListClose(4, self.output)  # Closing 2.
    self.formatting_handler.HandleBulletListOpen(4, self.output, 1)
    self.formatting_handler.HandleText(4, self.output, "d\n")
    self.formatting_handler.HandleListClose(5, self.output)  # Closing 1.

    self.assertOutput("  * a\n  * b\n    * c\n  * d\n")
    self.assertNoWarnings()

  def testHandleBulletListInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleBulletListOpen(1, self.output, 1)
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleBulletListOpen(2, self.output, 1)
    self.formatting_handler.HandleText(2, self.output, "b\n")
    self.formatting_handler.HandleBulletListOpen(3, self.output, 2)
    self.formatting_handler.HandleText(3, self.output, "c\n")
    self.formatting_handler.HandleListClose(4, self.output)  # Closing 2.
    self.formatting_handler.HandleBulletListOpen(4, self.output, 1)
    self.formatting_handler.HandleText(4, self.output, "d\n")
    self.formatting_handler.HandleListClose(5, self.output)  # Closing 1.

    self.assertOutput("<ul><li>a\n</li><li>b\n<ul><li>c\n</li></ul></li>"
                      "<li>d\n</li></ul>")
    self.assertWarning("Bulleted list markup was used", occurrences=2)

  def testHandleBlockQuote(self):
    self.formatting_handler.HandleBlockQuoteOpen(1, self.output, 1)
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleBlockQuoteOpen(2, self.output, 1)
    self.formatting_handler.HandleText(2, self.output, "b\n")
    self.formatting_handler.HandleBlockQuoteOpen(3, self.output, 2)
    self.formatting_handler.HandleText(3, self.output, "c\n")
    self.formatting_handler.HandleListClose(4, self.output)  # Closing 2.
    self.formatting_handler.HandleBlockQuoteOpen(4, self.output, 1)
    self.formatting_handler.HandleText(4, self.output, "d\n")
    self.formatting_handler.HandleListClose(5, self.output)  # Closing 1.

    self.assertOutput("> a\n> b\n> > c\n\n> d\n")
    self.assertNoWarnings()

  def testHandleBlockQuoteInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleBlockQuoteOpen(1, self.output, 1)
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleBlockQuoteOpen(2, self.output, 1)
    self.formatting_handler.HandleText(2, self.output, "b\n")
    self.formatting_handler.HandleBlockQuoteOpen(3, self.output, 2)
    self.formatting_handler.HandleText(3, self.output, "c\n")
    self.formatting_handler.HandleListClose(4, self.output)  # Closing 2.
    self.formatting_handler.HandleBlockQuoteOpen(4, self.output, 1)
    self.formatting_handler.HandleText(4, self.output, "d\n")
    self.formatting_handler.HandleListClose(5, self.output)  # Closing 1.

    self.assertOutput("<blockquote>a\nb<br>\n<blockquote>c\n</blockquote>"
                      "d\n</blockquote>")
    self.assertWarning("Blockquote markup was used", occurrences=2)

  def testHandleParagraphBreak(self):
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleParagraphBreak(2, self.output)
    self.formatting_handler.HandleText(3, self.output, "b\n")

    self.assertOutput("a\n\nb\n")
    self.assertNoWarnings()

  def testHandleParagraphBreakInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleText(1, self.output, "a\n")
    self.formatting_handler.HandleParagraphBreak(2, self.output)
    self.formatting_handler.HandleText(3, self.output, "b\n")

    self.assertOutput("a\n<br>\nb<br>\n")
    self.assertNoWarnings()

  def testHandleBold(self):
    self.formatting_handler.HandleBoldOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleBoldClose(3, self.output)

    self.assertOutput("**xyz**")
    self.assertNoWarnings()

  def testHandleBoldInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleBoldOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleBoldClose(3, self.output)

    self.assertOutput("<b>xyz</b>")
    self.assertWarning("Bold markup was used")

  def testHandleItalic(self):
    self.formatting_handler.HandleItalicOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleItalicClose(3, self.output)

    self.assertOutput("_xyz_")
    self.assertNoWarnings()

  def testHandleItalicInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleItalicOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleItalicClose(3, self.output)

    self.assertOutput("<i>xyz</i>")
    self.assertWarning("Italic markup was used")

  def testHandleStrikethrough(self):
    self.formatting_handler.HandleStrikethroughOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleStrikethroughClose(3, self.output)

    self.assertOutput("~~xyz~~")
    self.assertNoWarnings()

  def testHandleStrikethroughInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleStrikethroughOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleStrikethroughClose(3, self.output)

    self.assertOutput("<del>xyz</del>")
    self.assertWarning("Strikethrough markup was used")

  def testHandleSuperscript(self):
    self.formatting_handler.HandleSuperscript(1, self.output, "xyz")

    self.assertOutput("<sup>xyz</sup>")
    self.assertNoWarnings()

  def testHandleSuperscriptInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleSuperscript(1, self.output, "xyz")

    self.assertOutput("<sup>xyz</sup>")
    self.assertNoWarnings()

  def testHandleSubscript(self):
    self.formatting_handler.HandleSubscript(1, self.output, "xyz")

    self.assertOutput("<sub>xyz</sub>")
    self.assertNoWarnings()

  def testHandleSubscriptInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleSubscript(1, self.output, "xyz")

    self.assertOutput("<sub>xyz</sub>")
    self.assertNoWarnings()

  def testHandleInlineCode(self):
    self.formatting_handler.HandleInlineCode(1, self.output, "xyz")

    self.assertOutput("` xyz `")
    self.assertNoWarnings()

  def testHandleInlineCodeInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleInlineCode(1, self.output, "xyz")

    self.assertOutput("<code>xyz</code>")
    self.assertNoWarnings()

  # Table handling is tested in the Converter tests,
  # as the interactions are multiple and handled there.

  def testHandleLink(self):
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com", None)

    self.assertOutput("http://example.com")
    self.assertNoWarnings()

  def testHandleLinkInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com", None)

    self.assertOutput("<a href='http://example.com'>http://example.com</a>")
    self.assertWarning("Link markup was used")

  def testHandleLinkWithDescription(self):
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com", "Description")

    self.assertOutput("[Description](http://example.com)")
    self.assertNoWarnings()

  def testHandleLinkWithDescriptionInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com", "Description")

    self.assertOutput("<a href='http://example.com'>Description</a>")
    self.assertWarning("Link markup was used")

  def testHandleLinkWithImageDescription(self):
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com", "http://example.com/a.png")

    self.assertOutput("[![](http://example.com/a.png)](http://example.com)")
    self.assertNoWarnings()

  def testHandleLinkWithImageDescriptionInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com", "http://example.com/a.png")

    self.assertOutput("<a href='http://example.com'>"
                      "<img src='http://example.com/a.png' /></a>")
    self.assertWarning("Link markup was used")

  def testHandleImageLink(self):
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com/a.png", None)

    self.assertOutput("![http://example.com/a.png](http://example.com/a.png)")
    self.assertNoWarnings()

  def testHandleImageLinkInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com/a.png", None)

    self.assertOutput("<img src='http://example.com/a.png' />")
    self.assertWarning("Link markup was used")

  def testHandleImageLinkWithDescription(self):
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com/a.png", "Description")

    self.assertOutput("[Description](http://example.com/a.png)")
    self.assertNoWarnings()

  def testHandleImageLinkWithDescriptionInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com/a.png", "Description")

    self.assertOutput("<a href='http://example.com/a.png'>Description</a>")
    self.assertWarning("Link markup was used")

  def testHandleImageLinkWithImageDescription(self):
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com/a.png", "http://example.com/b.png")

    self.assertOutput("![![](http://example.com/b.png)]"
                      "(http://example.com/a.png)")
    self.assertNoWarnings()

  def testHandleImageLinkWithImageDescriptionInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleLink(
        1, self.output, "http://example.com/a.png", "http://example.com/b.png")

    self.assertOutput("<a href='http://example.com/a.png'>"
                      "<img src='http://example.com/b.png' /></a>")
    self.assertWarning("Link markup was used")

  def testHandleWiki(self):
    self.formatting_handler.HandleWiki(1, self.output, "TestPage", "Test Page")

    self.assertOutput("[Test Page](wiki/TestPage)")
    self.assertNoWarnings()

  def testHandleWikiInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleWiki(1, self.output, "TestPage", "Test Page")

    self.assertOutput("<a href='wiki/TestPage'>Test Page</a>")
    self.assertWarning("Link markup was used")

  def testHandleIssue(self):
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 123)

    self.assertOutput("[issue 789](https://github.com/abcxyz/test/issues/789)")
    self.assertWarning("Issue 123 was auto-linked")
    self.assertWarning("In the output, it has been linked to the "
                       "migrated issue on GitHub: 789.")

  def testHandleIssueInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 123)

    self.assertOutput("<a href='https://github.com/abcxyz/test/issues/789'>"
                      "issue 789</a>")
    self.assertWarning("Link markup was used")
    self.assertWarning("Issue 123 was auto-linked")
    self.assertWarning("In the output, it has been linked to the "
                       "migrated issue on GitHub: 789.")

  def testHandleIssueNotInMap(self):
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("[issue 456](https://code.google.com/p/"
                      "test/issues/detail?id=456)")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, it was not found in the issue migration map")
    self.assertWarning("As a placeholder, the text has been modified to "
                       "link to the original Google Code issue page")

  def testHandleIssueNotInMapInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("<a href='https://code.google.com/p/"
                      "test/issues/detail?id=456'>issue 456</a>")
    self.assertWarning("Link markup was used")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, it was not found in the issue migration map")
    self.assertWarning("As a placeholder, the text has been modified to "
                       "link to the original Google Code issue page")

  def testHandleIssueNoMap(self):
    self.formatting_handler._issue_map = None
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("[issue 456](https://code.google.com/p/"
                      "test/issues/detail?id=456)")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, no issue migration map was specified")
    self.assertWarning("As a placeholder, the text has been modified to "
                       "link to the original Google Code issue page")

  def testHandleIssueNoMapInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler._issue_map = None
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("<a href='https://code.google.com/p/"
                      "test/issues/detail?id=456'>issue 456</a>")
    self.assertWarning("Link markup was used")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, no issue migration map was specified")
    self.assertWarning("As a placeholder, the text has been modified to "
                       "link to the original Google Code issue page")

  def testHandleIssueNotInMapNoProject(self):
    self.formatting_handler._project = None
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("issue 456 (on Google Code)")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, it was not found in the issue migration map")
    self.assertWarning("Additionally, because no project name was specified "
                       "the issue could not be linked to the original Google "
                       "Code issue page.")
    self.assertWarning("The auto-link has been removed")

  def testHandleIssueNotInMapNoProjectInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler._project = None
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("issue 456 (on Google Code)")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, it was not found in the issue migration map")
    self.assertWarning("Additionally, because no project name was specified "
                       "the issue could not be linked to the original Google "
                       "Code issue page.")
    self.assertWarning("The auto-link has been removed")

  def testHandleIssueNoMapNoProject(self):
    self.formatting_handler._issue_map = None
    self.formatting_handler._project = None
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("issue 456 (on Google Code)")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, no issue migration map was specified")
    self.assertWarning("Additionally, because no project name was specified "
                       "the issue could not be linked to the original Google "
                       "Code issue page.")
    self.assertWarning("The auto-link has been removed")

  def testHandleIssueNoMapNoProjectInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler._issue_map = None
    self.formatting_handler._project = None
    self.formatting_handler.HandleIssue(1, self.output, "issue ", 456)

    self.assertOutput("issue 456 (on Google Code)")
    self.assertWarning("Issue 456 was auto-linked")
    self.assertWarning("However, no issue migration map was specified")
    self.assertWarning("Additionally, because no project name was specified "
                       "the issue could not be linked to the original Google "
                       "Code issue page.")
    self.assertWarning("The auto-link has been removed")

  def testHandleRevision(self):
    self.formatting_handler.HandleRevision(1, self.output, "revision ", 7)

    self.assertOutput("[revision 7](https://code.google.com/p/"
                      "test/source/detail?r=7)")
    self.assertWarning("Revision 7 was auto-linked")
    self.assertWarning("As a placeholder, the text has been modified to "
                       "link to the original Google Code source page")

  def testHandleRevisionInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleRevision(1, self.output, "revision ", 7)

    self.assertOutput("<a href='https://code.google.com/p/"
                      "test/source/detail?r=7'>revision 7</a>")
    self.assertWarning("Link markup was used")
    self.assertWarning("Revision 7 was auto-linked")
    self.assertWarning("As a placeholder, the text has been modified to "
                       "link to the original Google Code source page")

  def testHandleRevisionNoProject(self):
    self.formatting_handler._project = None
    self.formatting_handler.HandleRevision(1, self.output, "revision ", 7)

    self.assertOutput("revision 7 (on Google Code)")
    self.assertWarning("Revision 7 was auto-linked")
    self.assertWarning("Additionally, because no project name was specified "
                       "the revision could not be linked to the original "
                       "Google Code source page.")
    self.assertWarning("The auto-link has been removed")

  def testHandleRevisionNoProjectInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler._project = None
    self.formatting_handler.HandleRevision(1, self.output, "revision ", 7)

    self.assertOutput("revision 7 (on Google Code)")
    self.assertWarning("Revision 7 was auto-linked")
    self.assertWarning("Additionally, because no project name was specified "
                       "the revision could not be linked to the original "
                       "Google Code source page.")
    self.assertWarning("The auto-link has been removed")

  def testHandleInHtml(self):
    self.formatting_handler.HandleHtmlOpen(
        1, self.output, "tag", {"a": "1", "b": "2"}, False)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleHtmlClose(3, self.output, "tag")

    self.assertOutput("<tag a='1' b='2'>xyz</tag>")
    self.assertNoWarnings()

  def testHandleHtmlInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleHtmlOpen(
        1, self.output, "tag", {"a": "1", "b": "2"}, False)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleHtmlClose(3, self.output, "tag")

    self.assertOutput("<tag a='1' b='2'>xyz</tag>")
    self.assertNoWarnings()

  def testHandleInHtmlSelfClose(self):
    self.formatting_handler.HandleHtmlOpen(
        1, self.output, "tag", {"a": "1", "b": "2"}, True)

    self.assertOutput("<tag a='1' b='2' />")
    self.assertNoWarnings()

  def testHandleHtmlSelfCloseInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleHtmlOpen(
        1, self.output, "tag", {"a": "1", "b": "2"}, True)

    self.assertOutput("<tag a='1' b='2' />")
    self.assertNoWarnings()

  def testHandleGPlus(self):
    self.formatting_handler.HandleGPlusOpen(1, self.output, None)
    self.formatting_handler.HandleGPlusClose(1, self.output)

    self.assertNoOutput("(TODO: Link to Google+ page.)")
    self.assertWarning("A Google+ +1 button was embedded on this page")

  def testHandleGPlusInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleGPlusOpen(1, self.output, None)
    self.formatting_handler.HandleGPlusClose(1, self.output)

    self.assertNoOutput("(TODO: Link to Google+ page.)")
    self.assertWarning("A Google+ +1 button was embedded on this page")

  def testHandleComment(self):
    self.formatting_handler.HandleCommentOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleCommentClose(3, self.output)

    self.assertOutput("<a href='Hidden comment: xyz'></a>")
    self.assertWarning("A comment was used in the wiki file")

  def testHandleCommentInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleCommentOpen(1, self.output)
    self.formatting_handler.HandleText(2, self.output, "xyz")
    self.formatting_handler.HandleCommentClose(3, self.output)

    self.assertOutput("<a href='Hidden comment: xyz'></a>")
    self.assertWarning("A comment was used in the wiki file")

  def testHandleVideo(self):
    self.formatting_handler.HandleVideoOpen(
        1, self.output, "FiARsQSlzDc", 320, 240)
    self.formatting_handler.HandleVideoClose(1, self.output)

    self.assertOutput("<a href='http://www.youtube.com/watch?"
                      "feature=player_embedded&v=FiARsQSlzDc' target='_blank'>"
                      "<img src='http://img.youtube.com/vi/FiARsQSlzDc/0.jpg' "
                      "width='320' height=240 /></a>")
    self.assertWarning("GFM does not support embedding the YouTube player")

  def testHandleVideoInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleVideoOpen(
        1, self.output, "FiARsQSlzDc", 320, 240)
    self.formatting_handler.HandleVideoClose(1, self.output)

    self.assertOutput("<a href='http://www.youtube.com/watch?"
                      "feature=player_embedded&v=FiARsQSlzDc' target='_blank'>"
                      "<img src='http://img.youtube.com/vi/FiARsQSlzDc/0.jpg' "
                      "width='320' height=240 /></a>")
    self.assertWarning("GFM does not support embedding the YouTube player")

  def testHandleText(self):
    self.formatting_handler.HandleText(1, self.output, "xyz")

    self.assertOutput("xyz")
    self.assertNoWarnings()

  def testHandleTextInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleText(1, self.output, "xyz")

    self.assertOutput("xyz")
    self.assertNoWarnings()

  def testHandleEscapedText(self):
    self.formatting_handler.HandleEscapedText(1, self.output, "**_xyz_** <a>")

    self.assertOutput("\\*\\*\\_xyz\\_\\*\\* &lt;a&gt;")
    self.assertNoWarnings()

  def testHandleEscapedTextInHtml(self):
    self.formatting_handler._in_html = 1
    self.formatting_handler.HandleEscapedText(1, self.output, "**_xyz_** <a>")

    self.assertOutput("**_xyz_** <a>")
    self.assertNoWarnings()


class TestConverter(BaseTest):
  """Tests the converter."""

  def testExamplePage(self):
    with codecs.open("example.wiki", "rU", "utf-8") as example_input:
      with codecs.open("example.md", "rU", "utf-8") as example_output:
        self.converter.Convert(example_input, self.output)

        self.assertOutput(example_output.read())


if __name__ == "__main__":
  unittest.main()
