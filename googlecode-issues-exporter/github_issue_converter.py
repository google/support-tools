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

"""Tool for uploading Google Code issues to GitHub.

  Issue migration from Google Code to GitHub.
  This tools allows you to easily move your downloaded Google Code issues to
  GitHub.

  To use this tool:
  1. Follow the instructions at https://code.google.com/p/support-tools/ to
     download your issues from Google.
  2. Go to https://github.com/settings/applications and create a new "Personal
     Access Token".
  3. Get the GitHub username of the owner of the repository and the repositories
     name you wish to add the issues to. For example username: TheDoctor and
     repository: SonicScrewdriver
  4. (Optional) If this option is skipped all issues will be assigned to the
     owner of the repo.  Make a file that contains a mapping from the Google
     Code email address to the GitHub username for each user you wish to assign
     issues too.  The file should be newline seperated with one user per line.
     The email address and username should be colon (':') seperated. For example
     a file may look like this:
       <Google Code Email>:<GitHub Username>
       myemail@gmail.com:coolperson
       otheruser@gmail.com:userother
  5. Then run the command:
       python ./issue_migration.py \
         --github_oauth_token=<oauth-token> \
         --github_owner_username=<your-github-username> \
         --github_repo_name=<repository-name> \
         --issue_file_path=<path-to-issue-file> \
         --user_file_path="<optional-path-to-user-mapping-file>"
"""

import argparse
import json
import sys
import time
import urllib

import httplib2
import issues


# The URL used for calls to GitHub.
GITHUB_API_URL = "https://api.github.com"
# The maximum number of retries to make for an HTTP request that has failed.
MAX_HTTP_REQUESTS = 3
# The time (in seconds) to wait before trying to see if more requests are
# available.
REQUEST_CHECK_TIME = 60 * 5
# GitHub orders the comments based on time alone, and because we upload ours
# relatively quickly we need a delay to keep things being posted in
# chronological order.
COMMENT_DELAY = 0.5


def _CheckSuccessful(response):
  """Checks if the request was successful.

  Args:
    response: An HTTP response that contains a mapping from 'status' to an
              HTTP response code integer.

  Returns:
    True if the request was succesful.
  """
  return "status" in response and 200 <= int(response["status"]) < 300


class GitHubService(object):
  """A connection to GitHub.

  Handles basic HTTP operations to the GitHub API.

  Attributes:
      github_owner_username: The username of the owner of the repository.
      github_repo_name: The GitHub repository name.
      rate_limit: Whether or not to rate limit API calls.
  """

  def __init__(self, github_owner_username, github_repo_name,
               github_oauth_token, rate_limit, http_instance=None):
    """Initialize the GitHubService.

    Args:
      github_owner_username: The username of the owner of the repository.
      github_repo_name: The GitHub repository name.
      github_oauth_token: The oauth token to use for the requests.
      http_instance: The HTTP instance to use, if not set a default will be
          used.
    """
    self.github_owner_username = github_owner_username
    self.github_repo_name = github_repo_name
    self._github_oauth_token = github_oauth_token
    self._rate_limit = rate_limit
    self._http = http_instance if http_instance else httplib2.Http()

  def _PerformHttpRequest(self, method, url, body="{}", params=None):
    """Attemps to make an HTTP request for given method, url, body and params.

    If the request fails try again 'MAX_HTTP_REQUESTS' number of times.  If the
    request fails due to the the request limit being hit, wait until more
    requests can be made.

    Args:
      method: The HTTP request method as a string ('GET', 'POST', etc.).
      url: The URL to make the call to.
      body: The body of the request.
      params: A dictionary of parameters to be used in the http call.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    headers = { "User-Agent": "GoogleCodeIssueExporter/1.0" }
    query = params.copy() if params else {}
    query["access_token"] = self._github_oauth_token
    request_url = "%s%s?%s" % (GITHUB_API_URL, url, urllib.urlencode(query))
    requests = 0
    while requests < MAX_HTTP_REQUESTS:
      requests += 1
      response, content = self._http.request(request_url, method,
                                             headers=headers, body=body)
      if _CheckSuccessful(response):
        return response, json.loads(content)
      elif self._RequestLimitReached():
        requests -= 1
        self._WaitForApiThrottlingToEnd()
    return response, json.loads(content)

  def PerformGetRequest(self, url, params=None):
    """Makes a GET request.

    Args:
      url: The URL to make the call to.
      params: A dictionary of parameters to be used in the http call.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    return self._PerformHttpRequest("GET", url, params=params)

  def PerformPostRequest(self, url, body):
    """Makes a POST request.

    Args:
      url: The URL to make the call to.
      body: The body of the request.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    if self._rate_limit and self._rate_limit in ["True", "true"]:
      # Add a delay to all outgoing request to GitHub, as to not trigger their
      # anti-abuse mechanism. This is separate from your typical rate limit, and
      # only applies to certain API calls (like creating issues). And, alas, the
      # exact quota is undocumented. So the value below is simply a guess. See:
      # https://developer.github.com/v3/#abuse-rate-limits
      req_min = 15
      time.sleep(60 / req_min)
    return self._PerformHttpRequest("POST", url, body)

  def PerformPatchRequest(self, url, body):
    """Makes a PATCH request.

    Args:
      url: The URL to make the call to.
      body: The body of the request.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    return self._PerformHttpRequest("PATCH", url, body)

  def _GetRemainingRequests(self):
    """Gets the number of remaining requests the user has this hour.

    Makes GET request to GitHub to get the number of remaining requests before
    the hourly request limit is reached.

    Returns:
      The number of remaining requests.
    """
    url = ("%s/rate_limit?access_token=%s" %
           (GITHUB_API_URL, self._github_oauth_token))
    _, content = self._http.request(url, "GET")
    content = json.loads(content)
    if "rate" in content and "remaining" in content["rate"]:
      return int(content["rate"]["remaining"])
    return 0

  def _RequestLimitReached(self):
    """Returns true if the request limit has been reached."""
    return self._GetRemainingRequests() == 0

  def _WaitForApiThrottlingToEnd(self):
    """Waits until the user is allowed to make more requests."""
    sys.stdout.write("Hourly request limit reached. Waiting for new limit, "
                     "checking every %d minutes" % (REQUEST_CHECK_TIME/60))
    while True:
      sys.stdout.write(".")
      sys.stdout.flush()
      time.sleep(REQUEST_CHECK_TIME)
      if not self._RequestLimitReached():
        return


class UserService(issues.UserService):
  """GitHub user operations.

  Handles user operations on the GitHub API.
  """

  GITHUB_USERS_URL = "/users"

  def __init__(self, github_service):
    """Initialize the UserService.

    Args:
      github_service: The GitHub service.
    """
    self._github_service = github_service

  def _GetUser(self, username):
    """Gets a GitHub user.

    Args:
      username: The GitHub username to get.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    user_url = "%s/%s" % (self.GITHUB_USERS_URL, username)
    return self._github_service.PerformGetRequest(user_url)

  def IsUser(self, username):
    """Checks if the GitHub user exists.

    Args:
      username: The GitHub username to check.

    Returns:
      True if the username exists.
    """
    response, _ = self._GetUser(username)
    return _CheckSuccessful(response)


class IssueService(issues.IssueService):
  """GitHub issue operations.

  Handles creating and updating issues and comments on the GitHub API.
  """

  def __init__(self, github_service, comment_delay=COMMENT_DELAY):
    """Initialize the IssueService.

    Args:
      github_service: The GitHub service.
    """
    self._github_service = github_service
    self._comment_delay = comment_delay
    # If the repo is of the form "login/reponame" then don't inject the
    # username as it (or the organization) is already embedded.
    if '/' in self._github_service.github_repo_name:
      self._github_issues_url = "/repos/%s/issues" % \
          self._github_service.github_repo_name
    else:
      self._github_issues_url = ("/repos/%s/%s/issues" %
                                 (self._github_service.github_owner_username,
                                  self._github_service.github_repo_name))

  def GetIssues(self, state="open"):
    """Gets all of the issue for the GitHub repository.

    Args:
      state: The state of the repository can be either 'open' or 'closed'.

    Returns:
      The list of all of the issues for the given repository.

    Raises:
      IOError: An error occurred accessing previously created issues.
    """
    github_issues = []
    params = {"state": state, "per_page": 100, "page": 0}
    while True:
      params["page"] += 1
      response, content = self._github_service.PerformGetRequest(
          self._github_issues_url, params=params)
      if not _CheckSuccessful(response):
        raise IOError("Failed to retrieve previous issues.\n\n%s" % content)
      if not content:
        return github_issues
      else:
        github_issues += content
    return github_issues

  def CreateIssue(self, googlecode_issue):
    """Creates a GitHub issue.

    Args:
      googlecode_issue: An instance of GoogleCodeIssue

    Returns:
      The issue number of the new issue.

    Raises:
      issues.ServiceError: An error occurred creating the issue.
    """
    issue_title = googlecode_issue.GetTitle()
    # It is not possible to create a Google Code issue without a title, but you
    # can edit an issue to remove its title afterwards.
    if issue_title.isspace():
      issue_title = "<empty title>"
    issue = {
        "title": issue_title,
        "body": googlecode_issue.GetDescription(),
        "assignee": googlecode_issue.GetOwner(),
        "labels": googlecode_issue.GetLabels(),
    }
    response, content = self._github_service.PerformPostRequest(
        self._github_issues_url, json.dumps(issue))

    if not _CheckSuccessful(response):
      # Newline character at the beginning of the line to allows for in-place
      # updating of the counts of the issues and comments.
      raise issues.ServiceError(
          "\nFailed to create issue #%d '%s'.\n\n\n"
          "Response:\n%s\n\n\nContent:\n%s" % (
              googlecode_issue.GetId(), issue_title, response, content))

    return self._GetIssueNumber(content)

  def CloseIssue(self, issue_number):
    """Closes a GitHub issue.

    Args:
      issue_number: The issue number.

    Raises:
      issues.ServiceError: An error occurred closing the issue.
    """
    issue_url = "%s/%d" % (self._github_issues_url, issue_number)
    json_state = json.dumps({"state": "closed"})
    response, content = self._github_service.PerformPatchRequest(
        issue_url, json_state)
    if not _CheckSuccessful(response):
      raise issues.ServiceError("\nFailed to close issue #%s.\n%s" % (
          issue_number, content))

  def CreateComment(self, issue_number, googlecode_comment):
    """Creates a comment on a GitHub issue.

    Args:
      issue_number: The issue number on GitHub to post to.
      googlecode_comment: A GoogleCodeComment instance.

    Raises:
      issues.ServiceError: An error occurred creating the comment.
    """
    comment_url = "%s/%d/comments" % (self._github_issues_url, issue_number)
    comment = googlecode_comment.GetDescription()

    json_body = json.dumps({"body": comment})
    response, content = self._github_service.PerformPostRequest(
        comment_url, json_body)

    if not _CheckSuccessful(response):
      raise issues.ServiceError(
          "\nFailed to create issue comment for issue #%d\n\n"
          "Response:\n%s\n\nContent:\n%s\n\n" %
          (issue_number, response, content))
    time.sleep(self._comment_delay)

  def _GetIssueNumber(self, content):
    """Get the issue number from a newly created GitHub issue.

    Args:
      content: The content from an HTTP response.

    Returns:
      The GitHub issue number.
    """
    assert "number" in content, "Getting issue number from: %s" % content
    return content["number"]


def ExportIssues(github_owner_username, github_repo_name, github_oauth_token,
                 issue_file_path, project_name, user_file_path, rate_limit):
  """Exports all issues for a given project.
  """
  github_service = GitHubService(
      github_owner_username, github_repo_name, github_oauth_token,
      rate_limit)
  issue_service = IssueService(github_service)
  user_service = UserService(github_service)

  issue_data = issues.LoadIssueData(issue_file_path, project_name)
  user_map = issues.LoadUserData(user_file_path, user_service)

  # Add a special "user_requesting_export" user, which comes in handy.
  user_map["user_requesting_export"] = github_owner_username

  issue_exporter = issues.IssueExporter(
      issue_service, user_service, issue_data, project_name, user_map)

  try:
    issue_exporter.Init()
    issue_exporter.Start()
    print "\nDone!\n"
  except IOError, e:
    print "[IOError] ERROR: %s" % e
  except issues.InvalidUserError, e:
    print "[InvalidUserError] ERROR: %s" % e


def main(args):
  """The main function.

  Args:
    args: The command line arguments.

  Raises:
    ProjectNotFoundError: The user passed in an invalid project name.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument("--github_oauth_token", required=True,
                      help="You can generate an oauth token here: "
                      "https://github.com/settings/applications")
  parser.add_argument("--github_owner_username", required=True,
                      help="The project ownsers GitHub username")
  parser.add_argument("--github_repo_name", required=True,
                      help="The GitHub repository you wish to add the issues"
                      "to.")
  parser.add_argument("--issue_file_path", required=True,
                      help="The path to the file containing the issues from"
                      "Google Code.")
  parser.add_argument("--project_name", required=True,
                      help="The name of the Google Code project you wish to"
                      "export")
  parser.add_argument("--user_file_path", required=False,
                      help="The path to the file containing a mapping from"
                      "email address to github username.")
  parser.add_argument("--rate_limit", required=False, default="True",
                     help="Rate limit GitHub requests to not run into"
                     "anti-abuse limits.")
  parsed_args, _ = parser.parse_known_args(args)

  ExportIssues(
      parsed_args.github_owner_username, parsed_args.github_repo_name,
      parsed_args.github_oauth_token, parsed_args.issue_file_path,
      parsed_args.project_name, parsed_args.user_file_path,
      parsed_args.rate_limit)


if __name__ == "__main__":
  main(sys.argv)
