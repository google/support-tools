[GitLab](http://gitlab.com/) is a service that hosts git source code repositories, along with wikis and issue tracking. But unlike other services such as GitHub, you can also run GitLab on your own infrastructure. This document will cover how to migrate a project from Google Code to GitLab.

# Sign in to GitLab #
You can sign-into GitLab using an !OpenID identity, such as your Google account. From you will see the import from Google Code option available on the "New Project" page.

But first, you need to get the issue tracker data for your Google Code project.

# Obtain your Google Code Issue data #

Project migration to GitLab is keyed off of the Google Code Project Hosting archives returned from Google Takeout. To create an archive of all of your Google Code projects' issues, head to Google Takeout: https://www.google.com/settings/takeout

Google Takeout allows you to export project data from many Google Services, but for now you are only interested in "Google Code Project Hosting".

Google Takeout will create an archive of all of your project’s issues. Note that this is only available for projects which you are an owner of. You will not be able to use Google Takeout to export archives of issues for other open-source projects. (And consequently you cannot migrate those to GitLab.)

Depending on the number of Google Code projects you own, and the number of issues they have, exporting an archive may take a very long time. Google Takeout will notify you when your archive is ready.

Once you have your issue archive, extract the file named `GoogleCodeProjectHosting.json`. This is a JSON dump of all of your projects' issues. (The issues for multiple Google Code projects will be stored in that single file.)

Upload the .json file to GitLab as part of the project migration.

# Migrate your Project(s) #

GitLab's New Project flow guides you through each step of the migration process. With the list of projects obtained from your JSON dump, simply click "Import" for any projects you want to have migrated to GitLab.

As an optional step, GitLab provides is the ability to map Google Code email addresss to another name. For example, convert the obfuscated "johnsmi...@gmail.com" from the `GoogleCodeProjectHosting.json` dump to a GitLab user, or a full name such as "John Smith".

# URL Redirection #
Once a project has been successfully exported to GitLab, you will want to update your project's homepage on Google Code to avoid confusion.

It is possible to set a "project moved" URL for a project. When set, attempts to access the project will take users to an interstitial page indicating the new project location. In some situations, users will be automatically redirected to the project's new homepage.

To set the "project moved" URL simply send an email to [google-code-shutdown@google.com](mailto:google-code-shutdown@google.com), with the name of the project and the URL you would like to redirect to.