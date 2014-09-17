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
         --assignee_file_path="<optional-path-to-user-mapping-file>"
"""

import argparse
import json
import re
import sys
import time
import urllib

import httplib2


# The URL used for calls to GitHub.
GITHUB_API_URL = "https://api.github.com"
# The maximum number of retries to make for an HTTP request that has failed.
MAX_HTTP_REQUESTS = 3
# The time (in seconds) to wait before trying to see if more requests are
# available.
REQUEST_CHECK_TIME = 60 * 5
# A real kludge. GitHub orders the comments based on time alone, and because
# we upload ours relatively quickly we need at least a second in between
# comments to keep them in chronological order.
COMMENT_DELAY = 2


class Error(Exception):
  """Base error class."""


class InvalidUserError(Error):
  """Error for an invalid user."""


class InvalidUserMappingError(Error):
  """Error for an invalid user mapping file."""


class ProjectNotFoundError(Error):
  """Error for a non-existent project."""


def _CheckSuccessful(response):
  """Checks if the request was successful.

  Args:
    response: An HTTP response that contains a mapping from 'status' to an
              HTTP response code integer.

  Returns:
    True if the request was succesful.
  """
  return "status" in response and 200 <= int(response["status"]) < 300


def _FixUpComment(comment):
  formatted = []
  preformat_rest_of_comment = False
  for line in comment.split("\n"):
    if re.match(r'^#+ ', line) or re.match(r'^Index: ', line):
      preformat_rest_of_comment = True
    elif '--- cut here ---' in line:
      preformat_rest_of_comment = True
    if preformat_rest_of_comment:
      formatted.append("    %s" % line)
    else:
      # "#3" style commends get converted into links to issue #3, etc.
      # We don't want this. There's no way to escape this so put a non
      # breaking space to prevent.
      line = re.sub("#(\d+)", "#&nbsp;\g<1>", line)
      formatted.append(line)
  return '\n'.join(formatted)


class GitHubService(object):
  """A connection to GitHub.

  Handles basic HTTP operations to the GitHub API.

  Attributes:
      github_owner_username: The username of the owner of the repository.
      github_repo_name: The GitHub repository name.
  """

  def __init__(self, github_owner_username, github_repo_name,
               github_oauth_token, http_instance=None):
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
    query = params.copy() if params else {}
    query["access_token"] = self._github_oauth_token
    request_url = "%s%s?%s" % (GITHUB_API_URL, url, urllib.urlencode(query))
    requests = 0
    while requests < MAX_HTTP_REQUESTS:
      requests += 1
      response, content = self._http.request(request_url, method, body)
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


class GitHubUserService(object):
  """GitHub user operations.

  Handles user operations on the GitHub API.
  """

  GITHUB_USERS_URL = "/users"

  def __init__(self, github_service):
    """Initialize the GitHubUserService.

    Args:
      github_service: The GitHub service.
    """
    self._github_service = github_service

  def GetUser(self, username):
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
    response, _ = self.GetUser(username)
    return _CheckSuccessful(response)


class GitHubIssueService(object):
  """GitHub issue operations.

  Handles creating and updating issues and comments on the GitHub API.
  """

  def __init__(self, github_service):
    """Initialize the GitHubIssueService.


    Args:
      github_service: The GitHub service.
    """
    self._github_service = github_service
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
    issues = []
    params = {"state": state, "per_page": 100, "page": 0}
    while True:
      params["page"] += 1
      response, content = self._github_service.PerformGetRequest(
          self._github_issues_url, params=params)
      if not _CheckSuccessful(response):
        raise IOError("Failed to retrieve previous issues.")
      if not content:
        return issues
      else:
        issues += content

  def CreateIssue(self, issue):
    """Creates a GitHub issue.

    Args:
      issue: A dictionary matching the GitHub JSON format for a create request.
             The dictionary will be encoded to JSON.
             https://developer.github.com/v3/issues/#create-an-issue.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    return self._github_service.PerformPostRequest(
        self._github_issues_url, json.dumps(issue))

  def CloseIssue(self, issue_number):
    """Closes a GitHub issue.

    Args:
      issue_number: The issue number.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    issue_url = "%s/%d" % (self._github_issues_url, issue_number)
    json_state = json.dumps({"state": "closed"})
    return self._github_service.PerformPatchRequest(issue_url, json_state)

  def CreateComment(self, issue_number, issue_id, comment, author, comment_date,
                    comment_id, project_name):
    """Creates a comment on a GitHub issue.

    Args:
      issue_number: The issue number.
      issue_id: The Google Code issue id.
      comment: The comment text.
      author: The author of the comment.
      comment_date: The date the comment was made.
      comment_id: The Google Code comment id.
      project_name: The Google Code project name.

    Returns:
      A tuple of an HTTP response (https://developer.github.com/v3/#schema) and
      its content from the server which is decoded JSON.
    """
    comment_url = "%s/%d/comments" % (self._github_issues_url, issue_number)
    if comment == '':
      comment = '&lt;empty&gt;'
    else:
      comment = _FixUpComment(comment)

    orig_comment_url = "https://code.google.com/p/%s/issues/detail?id=%s#c%s" % \
        (project_name, issue_id, comment_id)

    comment = "Comment [#%s](%s) originally posted by %s on %s:\n\n%s" % \
        (comment_id, orig_comment_url, author, comment_date, comment)
    json_body = json.dumps({"body": comment})
    return self._github_service.PerformPostRequest(comment_url, json_body)

  def GetIssueNumber(self, content):
    """Get the issue number from a newly created GitHub issue.

    Args:
      content: The content from an HTTP response.

    Returns:
      The GitHub issue number.
    """
    return content["number"]

  def IsIssueOpen(self, issue):
    """Check if an issue is marked as open.

    Args:
      issue: A dictionary matching the GitHub JSON format for a get request.
             https://developer.github.com/v3/issues/#get-a-single-issue.

    Returns:
      True if the issue was open.
    """
    return "state" in issue and issue["state"] == "open"


class IssueExporter(object):
  """Issue Migration.

  Handles the uploading issues from Google Code to GitHub.
  """

  def __init__(self, github_service, issue_json_data, project_name,
               assignee_data=None):
    """Initialize the IssueExporter.

    Args:
      github_service: The GitHub service.
      issue_json_data: A data object of issues from Google Code.
      assignee_data: A string of email addresses mapped to GitHub usernames
          that are separated by ':'.  Each couple is separated by a newline.
    """
    self._github_service = github_service
    self._github_owner_username = self._github_service.github_owner_username
    self._issue_json_data = issue_json_data
    self._assignee_data = assignee_data

    self._issue_service = None
    self._user_service = None
    self._previously_created_issues = set()
    self._assignee_map = {}
    self._project_name = project_name

    self._issue_total = 0
    self._issue_number = 0
    self._comment_number = 0
    self._comment_total = 0

  def Init(self):
    """Initialize the needed variables."""
    self._issue_service = GitHubIssueService(self._github_service)
    self._user_service = GitHubUserService(self._github_service)
    self._GetAllPreviousIssues()
    self._CreateAssigneeMap()

  def _CreateAssigneeMap(self):
    """Create a mapping from Google Code email address to GitHub usernames.

    If there is an issue creating this mapping (An invalid file or invalid
    username) the program will exit so the user can fix the issue.

    Raises:
      InvalidUserError: The user passed in a invalid GitHub username.
      InvalidUserMappingError: The user passed in an invalid data object.
    """
    if self._assignee_data is None:
      return

    user_map_list = self._assignee_data.split("\n")
    for line in filter(None, user_map_list):
      if line.startswith('#'):
        continue
      user_map = line.split(":")
      if len(user_map) is 2:
        username = user_map[1].strip()
        if not self._user_service.IsUser(username):
          raise InvalidUserError("%s is not a GitHub User" % username)
        self._assignee_map[user_map[0].strip()] = username
      else:
        raise InvalidUserMappingError("Failed to create mapping for %s" % line)

  def _GetIssueAssignee(self, issue_json):
    """Get a GitHub username from a Google Code issue.

    Args:
      issue_json: A Google Code issue in as an object.

    Returns:
      The GitHub username associated with the Google Code issue or the
      repository owner if no mapping or email address in the Google Code
      issue exists.
    """
    if "owner" in issue_json:
      owner_name = issue_json["owner"]["name"]
      if owner_name in self._assignee_map:
        return self._assignee_map[owner_name]

    return self._github_owner_username

  def _GetAllPreviousIssues(self):
    """Gets all previously uploaded issues.

    Creates a hash of the issue titles, they will be unique as the Google Code
    issue number is in each title.
    """
    print "Getting any previously added issues..."
    open_issues = self._issue_service.GetIssues("open")
    closed_issues = self._issue_service.GetIssues("closed")
    issues = open_issues + closed_issues
    for issue in issues:
      self._previously_created_issues.add(issue["title"])

  def UpdatedIssueFeed(self):
    """Update issue count 'feed'.

    This displays the current status of the script to the user.
    """
    feed_string = ("\rIssue: %d/%d -> Comment: %d/%d        " %
                   (self._issue_number, self._issue_total,
                    self._comment_number, self._comment_total))
    sys.stdout.write(feed_string)
    sys.stdout.flush()

  def _CreateGitHubIssue(self, issue_json):
    """Converts an issue from Google Code to GitHub.

    This will take the Google Code issue and create a corresponding issue on
    GitHub.  If the issue on Google Code was closed it will also be closed on
    GitHub.

    Args:
      issue_json: A Google Code issue in as an object.

    Returns:
      The issue number assigned by GitHub or -1 if there was an error.
    """
    issue_title = issue_json["title"]
    is_open = self._issue_service.IsIssueOpen(issue_json)
    # Remove the state as it is no longer needed.
    del issue_json["state"]
    response, content = self._issue_service.CreateIssue(issue_json)

    if not _CheckSuccessful(response):
      # Newline character at the beginning of the line to allows for in-place
      # updating of the counts of the issues and comments.
      print "\nFailed to create issue: %s" % (issue_title)
      return -1, False
    issue_number = self._issue_service.GetIssueNumber(content)

    return issue_number, is_open

  def _CreateGitHubComments(self, comments, issue_number, issue_id):
    """Converts a list of issue comment from Google Code to GitHub.

    This will take a list of Google Code issue comments and create
    corresponding comments on GitHub for the given issue number.

    Args:
      comments: A list of comments (each comment is just a string).
      issue_number: The GitHub issue number.
    """
    self._comment_total = len(comments)
    self._comment_number = 0

    for comment in comments:
      self._comment_number += 1
      self.UpdatedIssueFeed()
      response, _ = self._issue_service.CreateComment(issue_number,
                                                      issue_id,
                                                      comment["content"],
                                                      comment["author"]["name"],
                                                      comment["published"],
                                                      comment["id"],
                                                      self._project_name)

      if not _CheckSuccessful(response):
        print ("\nFailed to create issue comment (%s) for GitHub issue #%d"
               % (comment["content"], issue_number))
      time.sleep(COMMENT_DELAY)

  def Start(self):
    """The primary function that runs this script.

    This will traverse the issues and attempt to create each issue and its
    comments.

    Raises:
      InvalidUserError: The user passed in a invalid GitHub username.
      InvalidUserMappingError: The user passed in an invalid data object.
    """
    self._issue_total = len(self._issue_json_data)
    self._issue_number = 0
    skipped_issues = 0
    for issue in self._issue_json_data:

      issue_title = issue["title"]

      if issue_title in self._previously_created_issues:
        skipped_issues += 1
        continue

      issue["assignee"] = self._GetIssueAssignee(issue)

      # code.google.com always has one comment (item #0) which is the issue
      # description.
      first_item = issue["items"].pop(0)

      content = _FixUpComment(first_item["content"])
      author = first_item["author"]["name"]
      create_date = first_item["published"]
      issue_id = issue["id"]
      url = "https://code.google.com/p/%s/issues/detail?id=%s" % \
          (self._project_name, issue_id)
      body = "Original [issue %s](%s) created by %s on %s:\n\n%s" % \
          (issue_id, url, author, create_date, content)
      issue["body"] = body

      self._issue_number += 1
      self.UpdatedIssueFeed()

      issue_number, is_open = self._CreateGitHubIssue(issue)
      if issue_number < 0:
        continue

      if "items" in issue:
        self._CreateGitHubComments(issue["items"], issue_number, issue_id)

      if not is_open:
        response, content = self._issue_service.CloseIssue(issue_number)
        if not _CheckSuccessful(response):
          print "\nFailed to close GitHub issue #%s" % (issue_number)

    if skipped_issues > 0:
      print ("\nSkipped %d/%d issue previously uploaded.  Most likely due to"
             " the script being aborted or killed." %
             (skipped_issues, self._issue_total))


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
  parser.add_argument("--assignee_file_path", required=False,
                      help="The path to the file containing a mapping from"
                      "email address to github username.")
  parsed_args, unused_unknown_args = parser.parse_known_args(args)

  github_service = GitHubService(parsed_args.github_owner_username,
                                 parsed_args.github_repo_name,
                                 parsed_args.github_oauth_token)

  assignee_data = None
  issue_data = None
  issue_exporter = None

  user_file = open(parsed_args.issue_file_path)
  user_data = json.load(user_file)
  user_projects = user_data["projects"]

  for project in user_projects:
    if parsed_args.project_name in project["name"]:
      issue_data = project["items"]
      break

  if issue_data is None:
    raise ProjectNotFoundError("Project %s not found" %
                               parsed_args.project_name)

  if parsed_args.assignee_file_path:
    assignee_data = open(parsed_args.assignee_file_path)
    issue_exporter = IssueExporter(github_service, issue_data,
                                   parsed_args.project_name,
                                   assignee_data.read())
  else:
    issue_exporter = IssueExporter(github_service, issue_data,
                                   parsed_args.project_name)

  try:
    issue_exporter.Init()
    issue_exporter.Start()
    print "\nDone!\n"
  except IOError, e:
    print "[IOError] ERROR: %s" % e
  except InvalidUserError, e:
    print "[InvalidUserError] ERROR: %s" % e
  except InvalidUserMappingError, e:
    print "[InvalidUserMappingError] ERROR: %s" % e


if __name__ == "__main__":
  main(sys.argv)