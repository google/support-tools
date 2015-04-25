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

import collections
import httplib
import json
import unittest
import urlparse

import github_issue_converter
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
from issues_test import REPO


# The GitHub username.
GITHUB_USERNAME = DEFAULT_USERNAME
# The GitHub repo name.
GITHUB_REPO = REPO
# The GitHub oauth token.
GITHUB_TOKEN = "oauth_token"
# The URL used for calls to GitHub.
GITHUB_API_URL = "https://api.github.com"


class FakeGitHubService(github_issue_converter.GitHubService):
  """A fake of the GitHubService.

  This also allows for queueing of responses and there content into a reponse
  queue. For example if you wanted a successful response and then a failure you
  would call AddSuccessfulResponse and then AddFailureResponse. Then when a call
  to _PerformHttpRequest is made the succesful response is made.  The next call
  would then return the failed response.

  If no responses are in the queue a succesful request with no content is
  returned.

  Attributes:
      github_owner_username: The username of the owner of the repository.
      github_repo_name: The GitHub repository name.
      github_oauth_token: The oauth token to use for the requests.
  """

  # pylint: disable=super-init-not-called
  def __init__(self, github_owner_username, github_repo_name,
               github_oauth_token):
    """Initialize the FakeGitHubService.

    Args:
      github_owner_username: The username of the owner of the repository.
      github_repo_name: The GitHub repository name.
      github_oauth_token: The oauth token to use for the requests.

    """
    self.github_owner_username = github_owner_username
    self.github_repo_name = github_repo_name
    self._github_oauth_token = github_oauth_token
    self._action_queue = collections.deque([])

  def AddSuccessfulResponse(self, content=None):
    """Adds a succesfull response with no content to the reponse queue."""
    self.AddResponse(content=content)

  def AddFailureResponse(self):
    """Adds a failed response with no content to the reponse queue."""
    self.AddResponse(httplib.BAD_REQUEST)

  def AddResponse(self, response=httplib.OK, content=None):
    status = {"status": response}
    full_response = {}
    full_response["status"] = status
    full_response["content"] = content if content else {}
    self._action_queue.append(full_response)

  def _PerformHttpRequest(self, method, url, body="{}", params=None):
    if not self._action_queue:
      return {"status": httplib.OK}, {}

    full_response = self._action_queue.popleft()
    return (full_response["status"], full_response["content"])

  def PerformGetRequest(self, url, params=None):
    """Makes a fake GET request.

    Args:
      url: The URL to make the call to.
      params: A dictionary of parameters to be used in the http call.

    Returns:
      A tuple of a fake response and fake content.
    """
    return self._PerformHttpRequest("GET", url, params=params)

  def PerformPostRequest(self, url, body):
    """Makes a POST request.

    Args:
      url: The URL to make the call to.
      body: The body of the request.

    Returns:
      A tuple of a fake response and content
    """
    return self._PerformHttpRequest("POST", url, body=body)

  def PerformPatchRequest(self, url, body):
    """Makes a PATCH request.

    Args:
      url: The URL to make the call to.
      body: The body of the request.

    Returns:
      A tuple of a fake response and content
    """
    return self._PerformHttpRequest("PATCH", url, body=body)


class Http2Mock(object):
  """Mock httplib2.Http object.  Only mocks out the request function.

  This mock keeps track of the last url, method and body called.

  Attributes:
    response_success: Fake successful HTTP response.
    response_failure: Fake failure HTTP response.
    response: The response of the next HTTP request.
    content: The content of the next HTTP request.
    last_url: The last URL that an HTTP request was made to.
    last_method: The last method that an HTTP request was made to.
    last_body: The last body method that an HTTP request was made to.

  """
  response_success = {"status": httplib.OK}
  response_failure = {"status": httplib.BAD_REQUEST}

  def __init__(self):
    """Initialize the Http2Mock."""
    self.response = self.response_success
    self.content = {}
    self.last_url = None
    self.last_method = None
    self.last_body = None

  def request(self, url, method, headers=None, body=None):
    """Makes a fake HTTP request.

    Args:
      url: The url to make the call to.
      method: The type of call. POST, GET, etc.
      body: The request of the body.

    Returns:
      A tuple of a response and its content.
    """
    self.last_url = url
    self.last_method = method
    self.last_body = body
    return (self.response, json.dumps(self.content))


class TestGitHubService(unittest.TestCase):
  """Tests for the GitHubService."""

  def setUp(self):
    self.http_mock = Http2Mock()
    self.github_service = github_issue_converter.GitHubService(
        GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN,
        rate_limit=False,
        http_instance=self.http_mock)

  def testSuccessfulRequestSuccess(self):
    success = github_issue_converter._CheckSuccessful(
        self.http_mock.response_success)
    self.assertTrue(success)

  def testSuccessfulRequestFailure(self):
    failure = github_issue_converter._CheckSuccessful(
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
    self.github_service = FakeGitHubService(GITHUB_USERNAME,
                                            GITHUB_REPO,
                                            GITHUB_TOKEN)
    self.github_user_service = github_issue_converter.UserService(
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
    self.http_mock = Http2Mock()
    self.github_service = github_issue_converter.GitHubService(
        GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN,
        rate_limit=False,
        http_instance=self.http_mock)
    self.github_issue_service = github_issue_converter.IssueService(
        self.github_service, comment_delay=0)

  def testCreateIssue(self):
    issue_body = {
        "body": ("Original [issue 1](https://code.google.com/p/repo/issues" +
                 "/detail?id=1) created by a_uthor on last year:\n\none"),
        "assignee": "a_uthor",
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
        "Comment [#1](https://code.google.com/p/repo/issues/detail" +
        "?id=1#c1) originally posted by a_uthor on last year:\n\none")
    self.github_issue_service.CreateComment(
        1, "1", SINGLE_COMMENT, GITHUB_REPO)
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

  def testGetIssues(self):
    fake_github_service = FakeGitHubService(GITHUB_USERNAME,
                                            GITHUB_REPO,
                                            GITHUB_TOKEN)
    github_issue_service = github_issue_converter.IssueService(
        fake_github_service, comment_delay=0)
    fake_github_service.AddFailureResponse()
    with self.assertRaises(IOError):
      github_issue_service.GetIssues()


class TestIssueExporter(unittest.TestCase):
  """Tests for the IssueService."""

  def setUp(self):
    self.github_service = FakeGitHubService(GITHUB_USERNAME,
                                            GITHUB_REPO,
                                            GITHUB_TOKEN)
    self.github_user_service = github_issue_converter.UserService(
        self.github_service)
    self.github_issue_service = github_issue_converter.IssueService(
        self.github_service, comment_delay=0)
    self.issue_exporter = issues.IssueExporter(
        self.github_issue_service, self.github_user_service,
        NO_ISSUE_DATA, GITHUB_REPO, USER_MAP)
    self.issue_exporter.Init()

    self.TEST_ISSUE_DATA = [
        {
            "id": "1",
            "title": "Title1",
            "state": "open",
            "comments": {
                "items": [COMMENT_ONE, COMMENT_TWO, COMMENT_THREE],
            },
            "labels": ["Type-Issue", "Priority-High"],
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User1"
                     },
        },
        {
            "id": "2",
            "title": "Title2",
            "state": "closed",
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User2"
                     },
            "labels": [],
            "comments": {
                "items": [COMMENT_ONE],
            },
        },
        {
            "id": "3",
            "title": "Title3",
            "state": "closed",
            "comments": {
                "items": [COMMENT_ONE, COMMENT_TWO],
            },
            "labels": ["Type-Defect"],
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User3"
                     }
        }]


  def testGetAllPreviousIssues(self):
    self.assertEqual(0, len(self.issue_exporter._previously_created_issues))
    content = [{"id": 1, "title": "issue_title", "comments": 2}]
    self.github_service.AddResponse(content=content)
    self.issue_exporter._GetAllPreviousIssues()
    self.assertEqual(1, len(self.issue_exporter._previously_created_issues))
    self.assertTrue(1 in self.issue_exporter._previously_created_issues)
    self.assertEqual("issue_title",
                     self.issue_exporter._previously_created_issues[1]["title"])
    self.assertEqual(2,
                     self.issue_exporter._previously_created_issues[1]["comment_count"])

  def testCreateIssue(self):
    content = {"number": 1234}
    self.github_service.AddResponse(content=content)

    issue_number = self.issue_exporter._CreateIssue(SINGLE_ISSUE)
    self.assertEqual(1234, issue_number)

  def testCreateIssueFailedOpenRequest(self):
    self.github_service.AddFailureResponse()
    with self.assertRaises(issues.ServiceError):
      self.issue_exporter._CreateIssue(SINGLE_ISSUE)

  def testCreateIssueFailedCloseRequest(self):
    content = {"number": 1234}
    self.github_service.AddResponse(content=content)
    self.github_service.AddFailureResponse()
    issue_number = self.issue_exporter._CreateIssue(SINGLE_ISSUE)
    self.assertEqual(1234, issue_number)

  def testCreateComments(self):
    self.assertEqual(0, self.issue_exporter._comment_number)
    self.issue_exporter._CreateComments(COMMENTS_DATA, 1234, SINGLE_ISSUE)
    self.assertEqual(4, self.issue_exporter._comment_number)

  def testCreateCommentsFailure(self):
    self.github_service.AddFailureResponse()
    self.assertEqual(0, self.issue_exporter._comment_number)
    with self.assertRaises(issues.ServiceError):
      self.issue_exporter._CreateComments(COMMENTS_DATA, 1234, SINGLE_ISSUE)

  def testStart(self):
    self.issue_exporter._issue_json_data = self.TEST_ISSUE_DATA

    # Note: Some responses are from CreateIssues, others are from CreateComment.
    self.github_service.AddResponse(content={"number": 1})
    self.github_service.AddResponse(content={"number": 10})
    self.github_service.AddResponse(content={"number": 11})
    self.github_service.AddResponse(content={"number": 2})
    self.github_service.AddResponse(content={"number": 20})
    self.github_service.AddResponse(content={"number": 3})
    self.github_service.AddResponse(content={"number": 30})

    self.issue_exporter.Start()

    self.assertEqual(3, self.issue_exporter._issue_total)
    self.assertEqual(3, self.issue_exporter._issue_number)
    # Comment counts are per issue and should match the numbers from the last
    # issue created, minus one for the first comment, which is really
    # the issue description.
    self.assertEqual(1, self.issue_exporter._comment_number)
    self.assertEqual(1, self.issue_exporter._comment_total)

  def testStart_SkipAlreadyCreatedIssues(self):
    self.issue_exporter._previously_created_issues["1"] = {
        "title": "Title1",
        "comment_count": 3
        }
    self.issue_exporter._previously_created_issues["2"] = {
        "title": "Title2",
        "comment_count": 1
        }
    self.issue_exporter._issue_json_data = self.TEST_ISSUE_DATA

    self.github_service.AddResponse(content={"number": 3})

    self.issue_exporter.Start()

    self.assertEqual(2, self.issue_exporter._skipped_issues)
    self.assertEqual(3, self.issue_exporter._issue_total)
    self.assertEqual(3, self.issue_exporter._issue_number)

  def testStart_ReAddMissedComments(self):
    self.issue_exporter._previously_created_issues["1"] = {
        "title": "Title1",
        "comment_count": 1  # Missing 2 comments.
        }
    self.issue_exporter._issue_json_data = self.TEST_ISSUE_DATA

    # First requests to re-add comments, then create issues.
    self.github_service.AddResponse(content={"number": 11})

    self.github_service.AddResponse(content={"number": 2})
    self.github_service.AddResponse(content={"number": 20})
    self.github_service.AddResponse(content={"number": 3})
    self.github_service.AddResponse(content={"number": 30})

    self.issue_exporter.Start()
    self.assertEqual(1, self.issue_exporter._skipped_issues)
    self.assertEqual(3, self.issue_exporter._issue_total)
    self.assertEqual(3, self.issue_exporter._issue_number)


  def testStart_GetErrorIfGoogleCodeAndGitHubDoNotMatch(self):
    self.issue_exporter._previously_created_issues["1"] = {
        "title": "Title1"}
    self.issue_exporter._previously_created_issues["2"] = {
        "title": "< not issue #2's title >"}
    self.issue_exporter._issue_json_data = self.TEST_ISSUE_DATA

    with self.assertRaises(RuntimeError):
      self.issue_exporter.Start()

  def testStart_GetErrorIfCreatedGitHubIDDoesNotMatch(self):
    self.issue_exporter._issue_json_data = self.TEST_ISSUE_DATA

    # Note: Some responses are from CreateIssues, others are from CreateComment.
    self.github_service.AddResponse(content={"number": 1})
    self.github_service.AddResponse(content={"number": 10})
    self.github_service.AddResponse(content={"number": 11})
    self.github_service.AddResponse(content={"number": 3})  # Expects next issue ID 2.

    with self.assertRaises(RuntimeError):
      self.issue_exporter.Start()


if __name__ == "__main__":
  unittest.main(buffer=True)
