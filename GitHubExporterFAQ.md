If you have a question that isn't answered here, please log an issue in the [issue tracker](https://code.google.com/p/support-tools/issues/list) or [contact Google](mailto:google-code-shutdown@google.com) for assistance.



# Questions #

## Where did my Google Code wikis go? ##
The wikis of projects exported to GitHub are converted into Markdown and placed in new `wiki` branch in the GitHub project's repo.

If you would rather use the GitHub wikis feature instead, GitHub user [morgant](https://github.com/morgant/) wrote [a tool](https://github.com/morgant/finishGoogleCodeGitHubWikiMigration) to move the wiki files from the `wiki` branch into the repo's wiki section.
## How can I export private issues? ##
Issues on Google Code can be labeled in such a way that they are private (e.g. those with `Restrict-View-*`). Private issues will be migrated to GitHub as if they were deleted. None of their contents will be migrated.

If you need to export private issues, you should not use the Google Code Exporter, and instead [manually export](https://code.google.com/p/support-tools/wiki/MigratingToGitHub) your project to GitHub.

As part of that process, you will use Google Takeout to get a full archive of your projects issues, which includes those marked as restricted. And the [Issue Exporter](https://code.google.com/p/support-tools/wiki/IssueExporterTool) tool will allow you to import them to GitHub.

## Are all projects available to be exported to GitHub? ##
No. Some projects are blocked from automatic export to GitHub, specifically those that have too many issues (1,000+) or those which have already moved.

In these situations, you will need to [manually export](https://code.google.com/p/support-tools/wiki/MigratingToGitHub) your project to GitHub.

## Can I migrate a Google Code repository to a GitHub Organization? ##
No, however you can quickly transfer the repository after the export is complete.

For more information about transferring a repository on GitHub, see [this document](https://help.github.com/articles/transferring-a-repository/).

# Post-Export Actions #

After the project gets migrated to GitHub, sometimes additional clean-up work is necessary.

## Fixing author information (SVN only) ##

While Git and Mercurial based projects store the author information as an email address, SVN does not. This can lead to strange situations when the project is on GitHub.  Commits by `larry.page@gmail.com` would show up in GitHub as being by `larry.page` after the export. (Since that is how SVN stored the information.) This means that the commits won't get linked to the GitHub user with email address `larry.page@gmail.com`.

You can fix this however by updating the git repo's author information.

The process for rewriting git history to change an author's email address is documented on GitHub under [changing author information](https://help.github.com/articles/changing-author-info/).

## Setting the "Project Moved" Flag ##

Once a project has been successfully exported to GitHub, you will want to update your project's homepage on Google Code to avoid confusion.

Now that Google Code has become read-only, the only way to set the project moved flag is to contact a Google Code administrator, by emailing google-code-shutdown@google.com. Please include the name of the Google Code repository and the new URL you want it to redirect to in your email.

# Known Issues #

This section covers a few common errors you might run into. If you encounter any other bugs or unexpected conversion issues, please log issues in the [issue tracker](https://code.google.com/p/support-tools/issues/list).

## Error "GitHub code import failure: ..." ##

There are several kinds of GitHub import failures which can arise, such as

  * Error! There was an error pushing commits to GitHub.
  * Error! There was an error importing commits.

This can happen for several reasons, the most common one is that the Google Code repository is too large.

GitHub will block pushes where a single file is larger than 100MiB. Similarly, the default limit for a GitHub is 1GiB. See [working with large files](https://help.github.com/articles/working-with-large-files/).

Simply `git rm`-ing a 100+MiB file from your repo is not enough, since the large file will still exist in your repos history. Instead, you need to erase the file from your repo's entirely history. (Literally rewrite history.) GitHub provides documentation for how to do this at [removing sensitive data](https://help.github.com/articles/remove-sensitive-data/).


If you do have a consistent error importing your code into GitHub please contact GitHub's support at https://github.com/contact. Please include the name of the target repository (e.g. https://github.com/user/repo), and they will be able to assist you from there.

## Error "GitHub code import took too long." ##

If the GitHub import process takes too long the project export is terminated. Please retry your project export, and if the problem persists contact [Google](mailto:google-code-shutdown@google.com) or [GitHub](https://github.com/contact?form%5Bsubject%5D=Google+Code+Export:+Error+code+import+took+too+long).

## Error "Project cannot be migrated because it has too many issues." ##
There is a hard limit on the number of issues that can be exported by the tool, per repo. If your project has more than 1,000 issues the export will fail.

To migrate your issues repos, you will need to use the stand-alone [Issue Exporter](https://code.google.com/p/support-tools/wiki/IssueExporterTool).

## Error "Error migrating issues." ##

There was an error migrating your projects issues. You can try re-exporting your project in GitHub (deleting the repo, and then using the Exporter tool again).

If the problem persists, please report it in the [issue tracker](https://code.google.com/p/support-tools/issues/list). Be sure to include the name of the Google Code project you are trying to export.

## Error "Internal Server Error." ##

Aw snap! Sometimes gremlins work their way into the system. We do our best to stamp them out, but with Google's free food it is hard to avoid snacking after midnight...

If you see this error someone will be looking into it. Wait a while and retry your project export again.

## Error "GitHub code import failure." ##

This error occurs when the GitHub code import API fails. Usually this issue is transient. But if it persists, contact Google or GitHub.

## Error "Project already exists." ##

Projects will be migrated to GitHub creating a repo with the same name as the Google Code project. It is not possible to specify a different name for the GitHub repo.

If your GitHub account already has a repo with the name of the project you wish to export, you will be prohibited from migrating that project from Google Code.

To work around this, you can rename your GitHub repo by going to the repo's settings. However, GitHub will still keep a placeholder stub and redirect URLs for you. So you will need to [contact GitHub](https://github.com/contact) and have them remove this for you. (So that the name is no longer reserved, and the Google Code exporter can migrate the project.)