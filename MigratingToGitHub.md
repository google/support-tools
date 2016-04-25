[GitHub](https://github.com) has been providing both public and private source hosting since 2008. This document will cover how to migrate a Google Code project to GitHub.

Note that while Google Code will host source code using the SVN, Mercurial, or Git protocol, GitHub chiefly supports Git. Mercurial or SVN-based Google Code projects will be converted to the Git protocol as part of the migration.

# Project Source #
There are several options for importing your source code into GitHub, depending on the type of source control system you use. The rest of this post will cover how to migrate git-based projects to GitHub. But if you are using another VCS, such as SVN or Mercurial, see this [GitHub article](https://help.github.com/articles/importing-your-project-to-github/).

## Using Git ##
To migrate your project's source to GitHub using command-line tools, first use your GitHub account to create a new, empty repository. Next, add the new GitHub repo as a "remote" to your Google Code project. You can see the git remote originally pointing to Google Code by typing `git remote -v`.

To move the source code to your new GitHub project, simply change the "origin" remote to point to GitHub.

```
$ git remote set-url origin \
    https://github.com/chrsmith/<new-github-repo>.git
$ git remote -v
origin	https://github.com/chrsmith/<new-github-repo>.git (fetch)
origin	https://github.com/chrsmith/<new-github-repo>.git (push)
```

Next, push your changes to the new remote:

```
git push -u origin --all   # push the repo and its refs
git push -u origin --tags  # push any tags
```

Once the data has been pushed, your project's source code and history should all be available on GitHub.

If your git push fails for some reason, for example "error: git-remote-https died of signal 13" run `git fsck` to diagnose the problem. GitHub also provides documentation for [Importing a Git repository using the command line](https://help.github.com/articles/importing-a-git-repository-using-the-command-line/).

With the project source migrated, the next step is to bring over Google Code project's issues and wikis.

# Project Issues #
To export project issues to GitHub, see the documentation for the [Issue Exporter](IssueExporterTool.md).

# Project Wikis #
To export project wikis to GitHub, see the documentation for the [Wiki-to-Markdown Tool](WikiToMarkdownTool.md).

# URL Redirection #
Once a project has been successfully exported to GitHub, you will want to update your project's homepage on Google Code to avoid confusion.

It is possible to set a "project moved" URL for a project. When set, attempts to access the project will take users to an interstitial page indicating the new project location. In some situations, users will be automatically redirected to the project's new homepage.

To set the "project moved" URL simply send an email to [google-code-shutdown@google.com](mailto:google-code-shutdown@google.com), with the name of the project and the URL you would like to redirect to.