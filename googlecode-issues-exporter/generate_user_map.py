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

"""Tool for generating a user mapping from Google Code user to BitBucket user.
"""

import argparse
import json
import sys

from bitbucket_issue_converter import GoogleCodeComment
from bitbucket_issue_converter import GoogleCodeIssue
from bitbucket_issue_converter import ProjectNotFoundError


def _CreateUsersDict(issue_data):
  """Extract users from list of issues into a dict.

  Args:
    issue_data: Issue data

  Returns:
    Dict of users associated with a list of issues
  """
  users = {}
  for issue in issue_data:
    googlecode_issue = GoogleCodeIssue(issue)

    # Add reporting user, if they aren't already
    reporting_user = googlecode_issue.GetAuthor()
    if reporting_user not in users:
      users[reporting_user] = reporting_user

    assignee_user = googlecode_issue.GetOwner()
    # Add assignee user, if they aren't already
    if assignee_user not in users:
      users[assignee_user] = assignee_user

    googlecode_comments = googlecode_issue.GetComments()
    for comment in googlecode_comments:
      googlecode_comment = GoogleCodeComment(comment, googlecode_issue.GetId())
      commenting_user = googlecode_comment.GetAuthor()
      if commenting_user not in users:
        users[commenting_user] = commenting_user

  return {
      "users": users
  }


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
  parsed_args, unused_unknown_args = parser.parse_known_args(args)

  issue_data = None

  user_file = open(parsed_args.issue_file_path)
  user_data = json.load(user_file)
  user_projects = user_data["projects"]

  for project in user_projects:
    if parsed_args.project_name in project["name"]:
      issue_data = project["items"]
      break

  if issue_data is None:
    raise ProjectNotFoundError(
        "Project %s not found" % parsed_args.project_name)

  users = _CreateUsersDict(issue_data)

  with open("users.json", "w") as users_file:
    user_json = json.dumps(users, sort_keys=True, indent=4,
                           separators=(",", ": "), ensure_ascii=False)
    users_file.write(unicode(user_json))
    print "\nCreated file users.json\n"

if __name__ == "__main__":
  main(sys.argv)
