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


class InvalidUserError(Exception):
  """Error for an invalid user."""


class ProjectNotFoundError(Exception):
  """Error for a non-existent project."""


class GoogleCodeIssue(object):
  """Google Code issue.

  Handles parsing and viewing a Google Code issue.
  """

  def __init__(self, issue):
    """Initialize the GoogleCodeIssue.

    Args:
      issue: The Google Code Issue.
    """
    self._issue = issue

  def GetOwner(self):
    """Get the owner username of a Google Code issue.

    Returns:
      The Google Code username that owns the issue or the
      repository owner if no mapping or email address exists.
    """
    if "owner" not in self._issue:
      return self.GetAuthor()

    return self._issue["owner"]["name"]

  def GetContent(self):
    """Get the content from a Google Code issue.

    Returns:
      The issue content
    """
    return self._issue["summary"]

  def GetContentUpdatedOn(self):
    """Get the date the content was last updated from a Google Code issue.

    Returns:
      The time stamp when the issue content was last updated
    """
    return self._issue["updated"]

  def GetCreatedOn(self):
    """Get the creation date from a Google Code issue.

    Returns:
      The time stamp when the issue content was created
    """
    return self._issue["published"]

  def GetId(self):
    """Get the id from a Google Code issue.

    Returns:
      The issue id
    """
    return self._issue["id"]

  def GetKind(self):
    """Get the kind from a Google Code issue.

    Returns:
      The issue kind, if none is found defaults to 'Defect'
    """
    types = [t for t in self._issue["labels"] if "Type-" in t]
    if types:
      return types[0][len("Type-"):]
    return "Defect"

  def GetPriority(self):
    """Get the priority from a Google Code issue.

    Returns:
      The issue priority, if none is found defaults to 'Medium'
    """
    priorities = [p for p in self._issue["labels"] if "Priority-" in p]
    if priorities:
      return priorities[0][len("Priority-"):]
    return "Medium"

  def GetAuthor(self):
    """Get the author's username of a Google Code issue.

    Returns:
      The Google Code username that the issue is authored by or the
      repository owner if no mapping or email address exists.
    """
    if "author" not in self._issue:
      return None

    return self._issue["author"]["name"]

  def GetStatus(self):
    """Get the status from a Google Code issue.

    Returns:
      The issue status
    """
    status = self._issue["status"].lower()
    if status == "accepted":
      status = "open"
    return status

  def GetTitle(self):
    """Get the title from a Google Code issue.

    Returns:
      The issue title
    """
    return self._issue["title"]

  def GetUpdatedOn(self):
    """Get the date the issue was last updated.

    Returns:
      The time stamp when the issue was last updated
    """
    return self.GetCreatedOn()

  def GetComments(self):
    """Get the list of comments for the issue (if any).

    Returns:
      The list of comments attached to the issue
    """
    return self._issue["items"]


class GoogleCodeComment(object):
  """Google Code Comment.

  Handles parsing and viewing a Google Code Comment.
  """

  def __init__(self, googlecode_comment, issue_id):
    """Initialize the GoogleCodeComment.

    Args:
      googlecode_comment: The Google Code Comment.
      issue_id: The issue id
    """
    self._comment = googlecode_comment
    self._issue_id = issue_id

  def GetContent(self):
    """Get the content from a Google Code comment.

    Returns:
      The issue comment
    """
    return self._comment["content"]

  def GetCreatedOn(self):
    """Get the creation date from a Google Code comment.

    Returns:
      The time stamp when the issue comment content was created
    """
    return self._comment["published"]

  def GetId(self):
    """Get the id from a Google Code comment.

    Returns:
      The issue comment id
    """
    return self._comment["id"]

  def GetIssueId(self):
    """Get the issue id from a Google Code comment.

    Returns:
      The issue id
    """
    return self._issue_id

  def GetUpdatedOn(self):
    """Get the date the issue comment content was last updated.

    Returns:
      The time stamp when the issue comment content was last updated
    """
    return self.GetCreatedOn()

  def GetAuthor(self):
    """Get the author's username of a Google Code issue comment.

    Returns:
      The Google Code username that the issue comment is authored by or the
      repository owner if no mapping or email address exists.
    """
    if "author" not in self._comment:
      return None

    return self._comment["author"]["name"]


class BitBucketIssue(object):
  """BitBucket issue.

  Handles creating and viewing a BitBucket issue.
  """

  def __init__(self, googlecode_issue):
    """Initialize the BitBucketIssue from a GoogleCodeIssue.

    Args:
      googlecode_issue: The Google Code Issue.
    """
    self._issue = googlecode_issue
    self._dict = {
        "assignee": self._issue.GetOwner(),
        "content": self._issue.GetContent(),
        "content_updated_on": self._issue.GetContentUpdatedOn(),
        "created_on": self._issue.GetCreatedOn(),
        "id": self._issue.GetId(),
        "kind": self._issue.GetKind(),
        "priority": self._issue.GetPriority(),
        "reporter": self._issue.GetAuthor(),
        "status": self._issue.GetStatus(),
        "title": self._issue.GetTitle(),
        "updated_on": self._issue.GetUpdatedOn()
    }

  def SetAssignee(self, assignee):
    self._dict["assignee"] = assignee

  def SetReporter(self, reporter):
    self._dict["reporter"] = reporter

  def ToDict(self):
    return self._dict


class BitBucketComment(object):
  """BitBucket comment.

  Handles creating and updating BitBucket comments.
  """

  def __init__(self, googlecode_comment):
    """Initialize the BitBucketComment from a GoogleCodeComment.

    Args:
      googlecode_comment: The Google Code Comment.
    """
    self._comment = googlecode_comment
    self._dict = {
        "content": self._comment.GetContent(),
        "created_on": self._comment.GetCreatedOn(),
        "id": self._comment.GetId(),
        "issue": self._comment.GetIssueId(),
        "updated_on": self._comment.GetUpdatedOn(),
        "user": self._comment.GetAuthor()
    }

  def ToDict(self):
    return self._dict

  def SetUser(self, user):
    self._dict["user"] = user


class IssueConverter(object):
  """Issue Converter.

  Handles the issues format conversion from Google Code to BitBucket.
  """

  def __init__(self, issue_json_data, assignee_data, default_issue_kind="bug"):
    """Initialize the IssuesConverter.

    Args:
      issue_json_data: The JSON file from Google Takeout
      assignee_data: The generated JSON file from generate_user_map.py
      default_issue_kind: Default issue kind (initially set to bug)
    """
    self._issue_data = issue_json_data
    self._default_issue_kind = default_issue_kind
    self._assignee_data = assignee_data

  def Convert(self):
    """The primary function that runs this script.
    """
    issues_data = self.CreateBitBucketIssues()

    with open("db-1.0.json", "w") as issues_file:
      issues_json = json.dumps(issues_data, sort_keys=True, indent=4,
                               separators=(",", ": "), ensure_ascii=False)
      issues_file.write(unicode(issues_json))

  def CreateBitBucketIssues(self):
    """Create BitBucket issues dict.

    Returns:
      BitBucket issues dict
    """
    bitbucket_issues = []
    bitbucket_comments = []

    for issue in self._issue_data:
      # Extract Google Code issue from JSON data
      googlecode_issue = GoogleCodeIssue(issue)

      # Convert to BitBucket issue
      bitbucket_issue = BitBucketIssue(googlecode_issue)

      # Set assignee to appropriate BitBucket user
      bitbucket_issue_assignee = self._assignee_data[
          googlecode_issue.GetOwner()]
      bitbucket_issue.SetAssignee(bitbucket_issue_assignee)

      # Set reporter to appropriate BitBucket user
      bitbucket_issue_reporter = self._assignee_data[
          googlecode_issue.GetAuthor()]
      bitbucket_issue.SetReporter(bitbucket_issue_reporter)

      # Append issue to JSON
      bitbucket_issues.append(bitbucket_issue.ToDict())

      # Extract Google Code comments, create equivalent BitBucket comments,
      # and append to BitBucket comments dict
      googlecode_comments = googlecode_issue.GetComments()
      bitbucket_comments_data = self.CreateBitBucketComments(
          googlecode_issue.GetId(), googlecode_comments)
      bitbucket_comments.append(bitbucket_comments_data)

    return {
        "issues": bitbucket_issues,
        "comments": bitbucket_comments,
        "meta": {
            "default_kind": self._default_issue_kind
        }
    }

  def CreateBitBucketComments(self, issue_id, issue_comments):
    """Create BitBucket comments dict for a particular issue.

    Args:
      issue_id: Issue ID
      issue_comments: Comments associated with specified issue

    Returns:
      BitBucket comments dict for an issue
    """
    bitbucket_comments = []
    for comment in issue_comments:
      # Extract Google Code comment from JSON data
      googlecode_comment = GoogleCodeComment(
          comment, issue_id)

      # Convert to BitBucket comment
      bitbucket_comment = BitBucketComment(googlecode_comment)

      # Set user to appropriate BitBucket user
      bitbucket_comment_user = self._assignee_data[
          googlecode_comment.GetAuthor()]
      bitbucket_comment.SetUser(bitbucket_comment_user)

      # Append comment to JSON
      bitbucket_comments.append(bitbucket_comment.ToDict())
    return bitbucket_comments


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
  parser.add_argument("--assignee_file_path", required=True,
                      help="The path to the file containing a mapping from"
                      "email address to github username")
  parser.add_argument("--default_issue_kind", required=False,
                      help="A non-null string containing one of the following"
                      "values: bug, enhancement, proposal, task. Defaults to"
                      "bug.")
  parsed_args, unused_unknown_args = parser.parse_known_args(args)

  assignee_data = None
  issue_data = None
  issue_converter = None

  # Load user data from Takeout JSON
  user_file = open(parsed_args.issue_file_path)
  user_data = json.load(user_file)

  # Load issue data from target project (if exists)
  user_projects = user_data["projects"]
  for project in user_projects:
    if parsed_args.project_name in project["name"]:
      issue_data = project["items"]
      break

  if issue_data is None:
    raise ProjectNotFoundError(
        "Project %s not found" % parsed_args.project_name)

  # Load assignee data from generated user mapping JSON
  assignee_file = open(parsed_args.assignee_file_path)
  assignee_data = json.load(assignee_file)["users"]

  # Set default issue kind (defaults to 'bug')
  default_issue_kind = parsed_args.default_issue_kind

  issue_converter = IssueConverter(
      issue_data, assignee_data, default_issue_kind)
  issue_converter.Convert()
  print "\nDone!\n"

if __name__ == "__main__":
  main(sys.argv)
