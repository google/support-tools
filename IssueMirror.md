# Issue Mirror #

As part of the export process, either to GitHub or using the [Issue Exporter](IssueExporterTool.md) tool, issue attachments are presented as a link. This wiki describes how those links are generated.

All _public_ Google Code issue attachments are mirrored to [Google Cloud Storage](https://cloud.google.com/storage/), in the bucket `google-code-attachments`.

You can access a project's issue attachments by generating a URL based on the issue's information. The format is as follows:

```
    "http://storage.googleapis.com/google-code-attachments" +
    "/" + project_name + 
    "/issue-" + issue_number +
    "/comment-" + comment_number +
    "/" + file_name
```

The end result will be a URL to the project's issue, for example:

http://storage.googleapis.com/google-code-attachments/issue-export-test/issue-4/comment-1/misc_file2.txt

If an attachment is added to the initial issue report, then it is considered to be at `comment_number` 0.