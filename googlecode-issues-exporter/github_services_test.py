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

"""Tests for the GitHub Services."""

# pylint: disable=missing-docstring,protected-access

import json
import unittest
import urlparse

import issues
import github_services

from issues_test import DEFAULT_USERNAME
from issues_test import SINGLE_COMMENT
from issues_test import SINGLE_ISSUE
from issues_test import REPO

# The GitHub username.
GITHUB_USERNAME = DEFAULT_USERNAME
# The GitHub repo name.
GITHUB_REPO = REPO
# The GitHub oauth token.
GITHUB_TOKEN = "oauth_token"
# The URL used for calls to GitHub.
GITHUB_API_URL = github_services.GITHUB_API_URL


class TestGitHubService(unittest.TestCase):
  """Tests for the GitHubService."""

  def setUp(self):
    self.http_mock = github_services.Http2Mock()
    self.github_service = github_services.GitHubService(
        GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN,
        rate_limit=False,
        http_instance=self.http_mock)

  def testSuccessfulRequestSuccess(self):
    success = github_services._CheckSuccessful(
        self.http_mock.response_success)
    self.assertTrue(success)

  def testSuccessfulRequestFailure(self):
    failure = github_services._CheckSuccessful(
        self.http_mock.response_failure)
    self.assertFalse(failure)

  def testGetRemainingRequestsRequestsLeft(self):
    self.http_mock.content = {"rate": {"remaining": "500"}}
    requests = self.github_service._GetRemainingRequests()
    self.assertEqual(requests, 500)

  def testGetRemainingRequestsNoRequestsLeft(self):
    self.http_mock.content = {"rate": {"remaining": "0"}}
    requests = self.github_service._GetRemainingRequests()
    self.assertEqual(requests, 0)

  def testGetRemainingRequestsBadResponse(self):
    self.http_mock.content = {"bad": "content"}
    requests = self.github_service._GetRemainingRequests()
    self.assertEqual(requests, 0)

  def testRequestLimitReachedLimitReached(self):
    self.http_mock.content = {"rate": {"remaining": "0"}}
    limit_reached = self.github_service._RequestLimitReached()
    self.assertTrue(limit_reached)

  def testRequestLimitReachedLimitNotReached(self):
    self.http_mock.content = {"rate": {"remaining": "500"}}
    limit_reached = self.github_service._RequestLimitReached()
    self.assertFalse(limit_reached)

  def testHttpRequest(self):
    response, content = self.github_service._PerformHttpRequest("GET", "/test")
    self.assertEqual(response, self.http_mock.response_success)
    self.assertEqual(content, {})
    self.assertEqual(self.http_mock.last_method, "GET")
    uri = ("%s/test?access_token=%s" % (GITHUB_API_URL, GITHUB_TOKEN))
    self.assertEqual(self.http_mock.last_url, uri)

  def testHttpRequestParams(self):
    params = {"one": 1, "two": 2}
    response, content = self.github_service._PerformHttpRequest("POST",
                                                                "/test",
                                                                params=params)
    self.assertEqual(response, self.http_mock.response_success)
    self.assertEqual(content, {})
    self.assertEqual(self.http_mock.last_method, "POST")

    uri = ("%s/test?access_token=%s&one=1&two=2" %
           (GITHUB_API_URL, GITHUB_TOKEN))
    # pylint: disable=unpacking-non-sequence
    (expected_scheme, expected_domain, expected_path, expected_params,
     expected_query, expected_fragment) = urlparse.urlparse(uri)
    expected_query_list = expected_query.split("&")

    # pylint: disable=unpacking-non-sequence
    (actual_scheme, actual_domain, actual_path, actual_params, actual_query,
     actual_fragment) = urlparse.urlparse(self.http_mock.last_url)
    actual_query_list = actual_query.split("&")

    self.assertEqual(expected_scheme, actual_scheme)
    self.assertEqual(expected_domain, actual_domain)
    self.assertEqual(expected_path, actual_path)
    self.assertEqual(expected_params, actual_params)
    self.assertEqual(expected_fragment, actual_fragment)
    self.assertItemsEqual(expected_query_list, actual_query_list)

  def testGetRequest(self):
    self.github_service.PerformGetRequest("/test")
    self.assertEqual(self.http_mock.last_method, "GET")

  def testPostRequest(self):
    self.github_service.PerformPostRequest("/test", "")
    self.assertEqual(self.http_mock.last_method, "POST")

  def testPatchRequest(self):
    self.github_service.PerformPatchRequest("/test", "")
    self.assertEqual(self.http_mock.last_method, "PATCH")


class TestUserService(unittest.TestCase):
  """Tests for the UserService."""

  def setUp(self):
    self.github_service = github_services.FakeGitHubService(GITHUB_USERNAME,
                                                            GITHUB_REPO,
                                                            GITHUB_TOKEN)
    self.github_user_service = github_services.UserService(
        self.github_service)

  def testIsUserTrue(self):
    is_user = self.github_user_service.IsUser("username123")
    self.assertTrue(is_user)

  def testIsUserFalse(self):
    self.github_service.AddFailureResponse()
    is_user = self.github_user_service.IsUser("username321")
    self.assertFalse(is_user)


class TestIssueService(unittest.TestCase):
  """Tests for the IssueService."""

  def setUp(self):
    self.http_mock = github_services.Http2Mock()
    self.github_service = github_services.GitHubService(
        GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN,
        rate_limit=False,
        http_instance=self.http_mock)
    self.github_issue_service = github_services.IssueService(
        self.github_service, comment_delay=0)

  def testCreateIssue(self):
    issue_body = {
        "body": (
            "```\none\n```\n\nOriginal issue reported on code.google.com by"
            " `a_uthor` on last year\n"
            "- **Labels added**: added-label\n"
            "- **Labels removed**: removed-label\n"),
        "assignee": "default_username",
        "labels": ["awesome", "great"],
        "title": "issue_title",
    }
    self.http_mock.content = {"number": 1}
    issue_number = self.github_issue_service.CreateIssue(SINGLE_ISSUE)
    self.assertEqual(self.http_mock.last_method, "POST")
    uri = ("%s/repos/%s/%s/issues?access_token=%s" %
           (GITHUB_API_URL, GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN))
    self.assertEqual(self.http_mock.last_url, uri)
    self.assertEqual(self.http_mock.last_body, json.dumps(issue_body))
    self.assertEqual(1, issue_number)

  def testCloseIssue(self):
    self.github_issue_service.CloseIssue(123)
    self.assertEqual(self.http_mock.last_method, "PATCH")
    uri = ("%s/repos/%s/%s/issues/%d?access_token=%s" %
           (GITHUB_API_URL, GITHUB_USERNAME, GITHUB_REPO, 123, GITHUB_TOKEN))
    self.assertEqual(self.http_mock.last_url, uri)
    self.assertEqual(self.http_mock.last_body,
                     json.dumps({"state": "closed"}))

  def testCreateComment(self):
    comment_body = (
        "```\none\n```\n\nOriginal issue reported on code.google.com "
        "by `a_uthor` on last year\n"
        "- **Labels added**: added-label\n"
        "- **Labels removed**: removed-label\n")
    self.github_issue_service.CreateComment(1, SINGLE_COMMENT)
    self.assertEqual(self.http_mock.last_method, "POST")
    uri = ("%s/repos/%s/%s/issues/%d/comments?access_token=%s" %
           (GITHUB_API_URL, GITHUB_USERNAME, GITHUB_REPO, 1, GITHUB_TOKEN))
    self.assertEqual(self.http_mock.last_url, uri)
    self.assertEqual(self.http_mock.last_body,
                     json.dumps({"body": comment_body}))

  def testGetIssueNumber(self):
    issue = {"number": 1347}
    issue_number = self.github_issue_service._GetIssueNumber(issue)
    self.assertEqual(1347, issue_number)

  # TODO(chris): Test filtering out issue responses a "pull_request" key.
  def testGetIssues(self):
    fake_github_service = github_services.FakeGitHubService(GITHUB_USERNAME,
                                                            GITHUB_REPO,
                                                            GITHUB_TOKEN)
    github_issue_service = github_services.IssueService(
        fake_github_service, comment_delay=0)
    fake_github_service.AddFailureResponse()
    with self.assertRaises(IOError):
      github_issue_service.GetIssues()


if __name__ == "__main__":
  unittest.main(buffer=True)
