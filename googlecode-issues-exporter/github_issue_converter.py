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
  This tools allows you to easily migrate your downloaded Google Code issues to
  GitHub.

  To use this tool see the documentation available at:
  https://code.google.com/p/support-tools/wiki/IssueExporterTool
"""

import argparse
import sys

import github_services
import issues


def ExportIssues(github_owner_username, github_repo_name, github_oauth_token,
                 issue_file_path, project_name, user_file_path, rate_limit):
  """Exports all issues for a given project."""
  github_service = github_services.GitHubService(
      github_owner_username, github_repo_name, github_oauth_token,
      rate_limit)
  issue_service = github_services.IssueService(github_service)
  user_service = github_services.UserService(github_service)

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
