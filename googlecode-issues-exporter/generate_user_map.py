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

  assignee_data = None
  issue_data = None
  issue_converter = None

  user_file = open(parsed_args.issue_file_path)
  user_data = json.load(user_file)
  user_projects = user_data["projects"]

  for project in user_projects:
    if parsed_args.project_name in project["name"]:
      issue_data = project["items"]
      break

  if issue_data is None:
    raise ProjectNotFoundError("Project %s not found" % parsed_args.project_name)

  users = {}

  for issue in issue_data:
    googlecode_issue = GoogleCodeIssue(issue)
      
    # Add reporting user, if they aren't already
    reporting_user = googlecode_issue.GetReporter()
    if reporting_user not in users:
      users[reporting_user] = reporting_user

    assignee_user = googlecode_issue.GetAssignee()
    # Add assignee user, if they aren't already
    if assignee_user not in users:
      users[assignee_user] = assignee_user

    googlecode_comments = googlecode_issue.GetComments()
    for comment in googlecode_comments:
      googlecode_comment = GoogleCodeComment(comment, googlecode_issue.GetId())
      commenting_user = googlecode_comment.GetUser()
      if commenting_user not in users:
        users[commenting_user] = commenting_user

  user_data = {"users":users}

  with open("users.json", "w") as users_file:
    users_file.write(unicode(json.dumps(user_data, sort_keys=True, indent=4, separators=(',', ': '), ensure_ascii=False)))
    print "\nCreated file users.json\n"

if __name__ == "__main__":
  main(sys.argv)
