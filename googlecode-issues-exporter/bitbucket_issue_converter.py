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

"""Tool for converting Google Code issues to a format accepted by BitBucket.

Most BitBucket concepts map cleanly to their Google Code equivalent, with the
exception of the following:
 - Issue Assignee is called an Owner
 - Issue Reporter is called an Author
 - Comment User is called an Author
"""

import argparse
import json
import sys

import issues


def _getKind(kind):
  mapping = {
    "defect": "bug",
    "enhancement": "enhancement",
    "task": "task",
    "review": "proposal",
    "other": "bug",
  }
  return mapping.get(kind.lower(), "bug")


def _getPriority(priority):
  mapping = {
    "low": "trivial",
    "medium": "minor",
    "high": "major",
    "critical": "critical",
  }
  return mapping.get(priority.lower(), "minor")


def _getStatus(status):
  mapping = {
      "new": "new",
      "fixed": "resolved",
      "invalid": "invalid",
      "duplicate": "duplicate",
      "wontfix": "wontfix",
  }
  return mapping.get(status.lower(), "new")


class UserService(issues.UserService):
  """BitBucket user operations.
  """

  def IsUser(self, username):
    """Returns wheter a username is a valid user.

    BitBucket does not have a user api, so accept all usernames.
    """
    return True


class IssueService(issues.IssueService):
  """Abstract issue operations.

  Handles creating and updating issues and comments on an user API.
  """
  def __init__(self):
    self._bitbucket_issues = []
    self._bitbucket_comments = []

  def GetIssues(self, state="open"):
    """Gets all of the issue for the repository.

    Since BitBucket does not have an issue API, always returns an empty list.

    Args:
      state: The state of the repository can be either 'open' or 'closed'.

    Returns:
      An empty list.
    """
    return []

  def CreateIssue(self, googlecode_issue):
    """Creates an issue.

    Args:
      googlecode_issue: An instance of GoogleCodeIssue

    Returns:
      The issue number of the new issue.

    Raises:
      ServiceError: An error occurred creating the issue.
    """
    bitbucket_issue = {
        "assignee": googlecode_issue.GetOwner(),
        "content": googlecode_issue.GetDescription(),
        "content_updated_on": googlecode_issue.GetContentUpdatedOn(),
        "created_on": googlecode_issue.GetCreatedOn(),
        "id": googlecode_issue.GetId(),
        "kind": _getKind(googlecode_issue.GetKind()),
        "priority": _getPriority(googlecode_issue.GetPriority()),
        "reporter": googlecode_issue.GetAuthor(),
        "status": _getStatus(googlecode_issue.GetStatus()),
        "title": googlecode_issue.GetTitle(),
        "updated_on": googlecode_issue.GetUpdatedOn()
    }
    self._bitbucket_issues.append(bitbucket_issue)
    return googlecode_issue.GetId()

  def CloseIssue(self, issue_number):
    """Closes an issue.

    Args:
      issue_number: The issue number.
    """

  def CreateComment(self, issue_number, source_issue_id,
                    googlecode_comment, project_name):
    """Creates a comment on an issue.

    Args:
      issue_number: The issue number.
      source_issue_id: The Google Code issue id.
      googlecode_comment: An instance of GoogleCodeComment
      project_name: The Google Code project name.
    """
    bitbucket_comment = {
        "content": googlecode_comment.GetDescription(),
        "created_on": googlecode_comment.GetCreatedOn(),
        "id": googlecode_comment.GetId(),
        "issue": googlecode_comment.GetIssue().GetId(),
        "updated_on": googlecode_comment.GetUpdatedOn(),
        "user": googlecode_comment.GetAuthor()
    }
    self._bitbucket_comments.append(bitbucket_comment)

  def WriteIssueData(self, default_issue_kind):
    """Writes out the json issue and comments data to db-1.0.json.
    """
    issues_data = {
        "issues": self._bitbucket_issues,
        "comments": self._bitbucket_comments,
        "meta": {
            "default_kind": default_issue_kind
        }
    }
    with open("db-1.0.json", "w") as issues_file:
      issues_json = json.dumps(issues_data, sort_keys=True, indent=4,
                               separators=(",", ": "), ensure_ascii=False)
      issues_file.write(unicode(issues_json))


def ExportIssues(issue_file_path, project_name,
                 user_file_path, default_issue_kind, default_username):
  """Exports all issues for a given project.
  """
  issue_service = IssueService()
  user_service = UserService()

  issue_data = issues.LoadIssueData(issue_file_path, project_name)
  user_map = issues.LoadUserData(user_file_path, default_username, user_service)

  issue_exporter = issues.IssueExporter(
      issue_service, user_service, issue_data, project_name, user_map)

  try:
    issue_exporter.Init()
    issue_exporter.Start()
    issue_service.WriteIssueData(default_issue_kind)
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
  parser.add_argument("--issue_file_path", required=True,
                      help="The path to the file containing the issues from"
                      "Google Code.")
  parser.add_argument("--project_name", required=True,
                      help="The name of the Google Code project you wish to"
                      "export")
  parser.add_argument("--user_file_path", required=True,
                      help="The path to the file containing a mapping from"
                      "email address to bitbucket username")
  parser.add_argument("--default_issue_kind", required=True,
                      help="A non-null string containing one of the following"
                      "values: bug, enhancement, proposal, task. Defaults to"
                      "bug.")
  parser.add_argument("--default_owner_username", required=True,
                      help="The default issue username")
  parsed_args, _ = parser.parse_known_args(args)

  ExportIssues(
    parsed_args.issue_file_path, parsed_args.project_name,
    parsed_args.user_file_path, parsed_args.default_issue_kind,
    parsed_args.default_owner_username)


if __name__ == "__main__":
  main(sys.argv)
