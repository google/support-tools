# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Tests for the BitBucket Services."""

# pylint: disable=missing-docstring,protected-access

import unittest

import bitbucket_issue_converter
import issues

from issues_test import DEFAULT_USERNAME
from issues_test import SINGLE_COMMENT
from issues_test import SINGLE_ISSUE
from issues_test import COMMENT_ONE
from issues_test import COMMENT_TWO
from issues_test import COMMENT_THREE
from issues_test import COMMENTS_DATA
from issues_test import NO_ISSUE_DATA
from issues_test import USER_MAP


# The BitBucket username.
BITBUCKET_USERNAME = DEFAULT_USERNAME
# The BitBucket repo name.
BITBUCKET_REPO = "repo"


class TestUserService(unittest.TestCase):
  """Tests for the UserService."""

  def setUp(self):
    self._bitbucket_user_service = bitbucket_issue_converter.UserService()

  def testIsUser123(self):
    is_user = self._bitbucket_user_service.IsUser("username123")
    self.assertTrue(is_user)

  def testIsUser321(self):
    is_user = self._bitbucket_user_service.IsUser("username321")
    self.assertTrue(is_user)


class TestIssueService(unittest.TestCase):
  """Tests for the IssueService."""

  def setUp(self):
    self._bitbucket_issue_service = bitbucket_issue_converter.IssueService()
    self.maxDiff = None

  def testCreateIssue(self):
    issue_body = {
        "assignee": "a_uthor",
        "content": ("Original [issue 1](https://code.google.com/p/repo/issues" +
                 "/detail?id=1) created by a_uthor on last year:\n\none"),
        "content_updated_on": "last month",
        "created_on": "last year",
        "id": 1,
        "kind": "bug",
        "priority": "minor",
        "reporter": None,
        "status": "resolved",
        "title": "issue_title",
        "updated_on": "last year",
    }
    issue_number = self._bitbucket_issue_service.CreateIssue(SINGLE_ISSUE)
    self.assertEqual(1, issue_number)
    actual = self._bitbucket_issue_service._bitbucket_issues[0]
    self.assertEqual(issue_body, actual)

  def testCloseIssue(self):
    # no-op
    self._bitbucket_issue_service.CloseIssue(123)

  def testCreateComment(self):
    comment_body = {
        "content": (
            "Comment [#1](https://code.google.com/p/repo/issues/detail" +
            "?id=1#c1) originally posted by a_uthor on last year:\n\none"),
        "created_on": "last year",
        "id": 1,
        "issue": 1,
        "updated_on": "last year",
        "user": "a_uthor",
    }
    self._bitbucket_issue_service.CreateComment(
        1, "1", SINGLE_COMMENT, BITBUCKET_REPO)
    actual = self._bitbucket_issue_service._bitbucket_comments[0]
    self.assertEqual(comment_body, actual)


class TestIssueExporter(unittest.TestCase):
  """Tests for the IssueService."""

  def setUp(self):
    self._bitbucket_user_service = bitbucket_issue_converter.UserService()
    self._bitbucket_issue_service = bitbucket_issue_converter.IssueService()
    self.issue_exporter = issues.IssueExporter(
        self._bitbucket_issue_service, self._bitbucket_user_service,
        NO_ISSUE_DATA, BITBUCKET_REPO, USER_MAP)
    self.issue_exporter.Init()

  def testGetAllPreviousIssues(self):
    self.assertEqual(0, len(self.issue_exporter._previously_created_issues))
    self.issue_exporter._GetAllPreviousIssues()
    self.assertEqual(0, len(self.issue_exporter._previously_created_issues))

  def testCreateIssue(self):
    issue_number = self.issue_exporter._CreateIssue(SINGLE_ISSUE)
    self.assertEqual(1, issue_number)

  def testCreateComments(self):
    self.assertEqual(0, self.issue_exporter._comment_number)
    self.issue_exporter._CreateComments(COMMENTS_DATA, 1234, SINGLE_ISSUE)
    self.assertEqual(4, self.issue_exporter._comment_number)

  def testStart(self):
    self.issue_exporter._issue_json_data = [
        {
            "id": "1",
            "title": "Title1",
            "state": "open",
            "status": "New",
            "comments": {
                "items": [COMMENT_ONE, COMMENT_TWO, COMMENT_THREE],
            },
            "labels": ["Type-Issue", "Priority-High"],
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User1"
                     },
            "published": "last year",
            "updated": "last month",
        },
        {
            "id": "2",
            "title": "Title2",
            "state": "closed",
            "status": "Fixed",
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User2"
                     },
            "labels": [],
            "comments": {
                "items": [COMMENT_ONE],
            },
            "published": "last month",
            "updated": "last week",
        },
        {
            "id": "3",
            "title": "Title3",
            "state": "closed",
            "status": "WontFix",
            "comments": {
                "items": [COMMENT_ONE, COMMENT_TWO],
            },
            "labels": ["Type-Defect"],
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User3"
                     },
            "published": "last week",
            "updated": "yesterday",
        }]

    self.issue_exporter.Start()

    self.assertEqual(3, self.issue_exporter._issue_total)
    self.assertEqual(3, self.issue_exporter._issue_number)
    # Comment counts are per issue and should match the numbers from the last
    # issue created, minus one for the first comment, which is really
    # the issue description.
    self.assertEqual(1, self.issue_exporter._comment_number)
    self.assertEqual(1, self.issue_exporter._comment_total)


if __name__ == "__main__":
  unittest.main(buffer=True)
