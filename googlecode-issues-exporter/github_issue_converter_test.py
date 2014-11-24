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

import collections
import httplib
import json
import issue_migration
import unittest
from urlparse import urlparse


# The GitHub username.
GITHUB_USERNAME = "username"
# The GitHub repo name.
GITHUB_REPO = "repo"
# The GitHub oauth token.
GITHUB_TOKEN = "oauth_token"
# The URL used for calls to GitHub.
GITHUB_API_URL = "https://api.github.com"


class FakeGitHubService(issue_migration.GitHubService):
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

  def AddSuccessfulResponse(self):
    """Adds a succesfull response with no content to the reponse queue."""
    self.AddResponse()

  def AddFailureResponse(self):
    """Adds a failed response with no content to the reponse queue."""
    self.AddResponse(httplib.BAD_REQUEST)

  def AddResponse(self, response=httplib.OK, content=None):
    status = {"status": response}
    full_response = {}
    full_response["status"] = status
    full_response["content"] = content if content else {}
    self._action_queue.append(full_response)

  def _PerformHttpRequest(self):
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
    return self._PerformHttpRequest()

  def PerformPostRequest(self, url, body):
    """Makes a POST request.

    Args:
      url: The URL to make the call to.
      body: The body of the request.

    Returns:
      A tuple of a fake response and content
    """
    return self._PerformHttpRequest()

  def PerformPatchRequest(self, url, body):
    """Makes a PATCH request.

    Args:
      url: The URL to make the call to.
      body: The body of the request.

    Returns:
      A tuple of a fake response and content
    """
    return self._PerformHttpRequest()


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

  def request(self, url, method, body=None):  # pylint: disable=g-bad-name
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
    self.github_service = issue_migration.GitHubService(
        GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN,
        http_instance=self.http_mock)

  def testSuccessfulRequestSuccess(self):
    success = issue_migration._CheckSuccessful(
        self.http_mock.response_success)
    self.assertTrue(success)

  def testSuccessfulRequestFailure(self):
    failure = issue_migration._CheckSuccessful(
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
    (expected_scheme, expected_domain, expected_path, expected_params,
     expected_query, expected_fragment) = urlparse(uri)
    expected_query_list = expected_query.split("&")

    (actual_scheme, actual_domain, actual_path, actual_params, actual_query,
     actual_fragment) = urlparse(self.http_mock.last_url)
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


class TestGitHubUserService(unittest.TestCase):
  """Tests for the GitHubUserService."""

  def setUp(self):
    self.github_service = FakeGitHubService(GITHUB_USERNAME,
                                            GITHUB_REPO,
                                            GITHUB_TOKEN)
    self.github_user_service = issue_migration.GitHubUserService(
        self.github_service)

  def testIsUserTrue(self):
    is_user = self.github_user_service.IsUser("username123")
    self.assertTrue(is_user)

  def testIsUserFalse(self):
    self.github_service.AddFailureResponse()
    is_user = self.github_user_service.IsUser("username321")
    self.assertFalse(is_user)


class TestGitHubIssueService(unittest.TestCase):
  """Tests for the GitHubIssueService."""

  def setUp(self):
    self.http_mock = Http2Mock()
    self.github_service = issue_migration.GitHubService(
        GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN,
        http_instance=self.http_mock)
    self.github_issue_service = issue_migration.GitHubIssueService(
        self.github_service)

  def testCreateIssue(self):
    issue_body = {"body": "issue"}
    self.github_issue_service.CreateIssue(issue_body)
    self.assertEqual(self.http_mock.last_method, "POST")
    uri = ("%s/repos/%s/%s/issues?access_token=%s" %
           (GITHUB_API_URL, GITHUB_USERNAME, GITHUB_REPO, GITHUB_TOKEN))
    self.assertEqual(self.http_mock.last_url, uri)
    self.assertEqual(self.http_mock.last_body, json.dumps(issue_body))

  def testCloseIssue(self):
    self.github_issue_service.CloseIssue(123)
    self.assertEqual(self.http_mock.last_method, "PATCH")
    uri = ("%s/repos/%s/%s/issues/%d?access_token=%s" %
           (GITHUB_API_URL, GITHUB_USERNAME, GITHUB_REPO, 123, GITHUB_TOKEN))
    self.assertEqual(self.http_mock.last_url, uri)
    self.assertEqual(self.http_mock.last_body,
                     json.dumps({"state": "closed"}))

  def testCreateComment(self):
    comment_body = "stuff"
    self.github_issue_service.CreateComment(123, comment_body)
    self.assertEqual(self.http_mock.last_method, "POST")
    uri = ("%s/repos/%s/%s/issues/%d/comments?access_token=%s" %
           (GITHUB_API_URL, GITHUB_USERNAME, GITHUB_REPO, 123, GITHUB_TOKEN))
    self.assertEqual(self.http_mock.last_url, uri)
    self.assertEqual(self.http_mock.last_body,
                     json.dumps({"body": comment_body}))

  def testGetIssueNumber(self):
    issue = {"number": 1347}
    issue_number = self.github_issue_service.GetIssueNumber(issue)
    self.assertEqual(1347, issue_number)

  def testIsIssueOpenOpen(self):
    issue = {"state": "open"}
    issue_open = self.github_issue_service.IsIssueOpen(issue)
    self.assertTrue(issue_open)

  def testIsIssueOpenClosed(self):
    issue = {"state": "closed"}
    issue_open = self.github_issue_service.IsIssueOpen(issue)
    self.assertFalse(issue_open)

  def testGetIssues(self):
    fake_github_service = FakeGitHubService(GITHUB_USERNAME,
                                            GITHUB_REPO,
                                            GITHUB_TOKEN)
    github_issue_service = issue_migration.GitHubIssueService(
        fake_github_service)
    fake_github_service.AddFailureResponse()
    with self.assertRaises(IOError):
      github_issue_service.GetIssues()


class TestIssueExporter(unittest.TestCase):
  """Tests for the GitHubIssueService."""

  def setUp(self):
    assignee_map = "user@email.com:userone\nuser2@gmail.com:usertwo"
    self.github_service = FakeGitHubService(GITHUB_USERNAME,
                                            GITHUB_REPO,
                                            GITHUB_TOKEN)
    self.issue_exporter = issue_migration.IssueExporter(self.github_service,
                                                        {},  # Issue data
                                                        assignee_map)
    self.issue_exporter.Init()

  def testCreateAssigneeMap(self):
    self.assertEqual(2, len(self.issue_exporter._assignee_map))

  def testCreateAssigneeMapNoData(self):
    self.issue_exporter = issue_migration.IssueExporter(self.github_service,
                                                        {})
    self.issue_exporter.Init()
    self.assertEqual(0, len(self.issue_exporter._assignee_map))

  def testCreateAssigneeMapNotUser(self):
    self.github_service.AddFailureResponse()
    with self.assertRaises(issue_migration.InvalidUserError):
      self.issue_exporter._CreateAssigneeMap()

  def testCreateAssigneeMapBadMap(self):
    self.issue_exporter._assignee_data = "user@email.com:userone:fail"
    with self.assertRaises(issue_migration.InvalidUserMappingError):
      self.issue_exporter._CreateAssigneeMap()

  def testGetIssueAssignee(self):
    issue = {"owner": {"kind": "projecthosting#issuePerson",
                       "name": "user@email.com"
                      }}
    email = self.issue_exporter._GetIssueAssignee(issue)
    self.assertEqual("userone", email)

  def testGetIssueAssigneeNoAssignee(self):
    email = self.issue_exporter._GetIssueAssignee({})
    self.assertEqual(GITHUB_USERNAME, email)

  def testGetIssueAssigneeOwner(self):
    issue = {"owner": {"kind": "projecthosting#issuePerson",
                       "name": "notauser@email.com"
                      }}
    email = self.issue_exporter._GetIssueAssignee(issue)
    self.assertEqual(GITHUB_USERNAME, email)

  def testGetAllPreviousIssues(self):
    self.assertEqual(0, len(self.issue_exporter._previously_created_issues))
    content = [{"title": "issue_title"}]
    self.github_service.AddResponse(content=content)
    self.issue_exporter._GetAllPreviousIssues()
    self.assertEqual(1, len(self.issue_exporter._previously_created_issues))
    self.assertTrue("issue_title" in
                    self.issue_exporter._previously_created_issues)

  def testCreateGitHubIssue(self):
    content = {"number": 1234}
    self.github_service.AddResponse(content=content)

    issue = {"state": "open", "title": "issue_title"}
    issue_number = self.issue_exporter._CreateGitHubIssue(issue)
    self.assertEqual(1234, issue_number)

  def testCreateGitHubIssueClosedIssue(self):
    content = {"number": 1234}
    self.github_service.AddResponse(content=content)

    issue = {"state": "closed", "title": "issue_title"}
    issue_number = self.issue_exporter._CreateGitHubIssue(issue)
    self.assertEqual(1234, issue_number)

  def testCreateGitHubIssueFailedOpenRequest(self):
    self.github_service.AddFailureResponse()
    issue = {"state": "open", "title": "issue_title"}
    issue_number = self.issue_exporter._CreateGitHubIssue(issue)
    self.assertEqual(-1, issue_number)

  def testCreateGitHubIssueFailedCloseRequest(self):
    content = {"number": 1234}
    self.github_service.AddResponse(content=content)
    self.github_service.AddFailureResponse()
    issue = {"state": "closed", "title": "issue_title"}
    issue_number = self.issue_exporter._CreateGitHubIssue(issue)
    self.assertEqual(1234, issue_number)

  def testCreateGitHubComments(self):
    self.assertEqual(0, self.issue_exporter._comment_number)
    comments = [{"content": "one"},
                {"content": "two"},
                {"content": "three"},
                {"content": "four"}]
    self.issue_exporter._CreateGitHubComments(comments, 1234)
    self.assertEqual(4, self.issue_exporter._comment_number)

  def testCreateGitHubCommentsFailure(self):
    self.github_service.AddFailureResponse()
    self.assertEqual(0, self.issue_exporter._comment_number)
    comments = [{"content": "one"},
                {"content": "two"},
                {"content": "three"},
                {"content": "four"}]
    self.issue_exporter._CreateGitHubComments(comments, 1234)
    self.assertEqual(4, self.issue_exporter._comment_number)

  def testStart(self):
    self.issue_exporter._issue_json_data = [
        {
            "id": "1",
            "title": "Title1",
            "state": "open",
            "items": [{"content": "one"},
                      {"content": "two"},
                      {"content": "three"}],
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User1"
                     }
        },
        {
            "id": "2",
            "title": "Title2",
            "state": "closed",
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User2"
                     }
        },
        {
            "id": "3",
            "title": "Title3",
            "state": "closed",
            "items": [{"content": "one"}],
            "owner": {"kind": "projecthosting#issuePerson",
                      "name": "User3"
                     }
        }]

    self.github_service.AddResponse(content={"number": 1234})
    self.github_service.AddSuccessfulResponse()
    self.github_service.AddSuccessfulResponse()
    self.github_service.AddSuccessfulResponse()
    self.github_service.AddResponse(content={"number": 4321})
    self.github_service.AddSuccessfulResponse()
    self.github_service.AddResponse(content={"number": 2314})

    self.issue_exporter.Start()

    self.assertEqual(3, self.issue_exporter._issue_total)
    self.assertEqual(3, self.issue_exporter._issue_number)
    # Comment counts are per issue and should match the numbers from the last
    # issue created.
    self.assertEqual(1, self.issue_exporter._comment_number)
    self.assertEqual(1, self.issue_exporter._comment_total)

  def testStartSkipAlreadyCreatedIssues(self):
    self.issue_exporter._previously_created_issues.add("Title1")
    self.issue_exporter._issue_json_data = [{"title": "Title1"}]
    self.issue_exporter.Start()
    self.assertEqual(1, self.issue_exporter._issue_total)
    self.assertEqual(0, self.issue_exporter._issue_number)

if __name__ == "__main__":
  unittest.main()
