#!/bin/bash

# Converts Google Code wiki pages to GitHub flavored Markdown. This is done
# inside of an existing git repo, and the process will build up a series
# of git commits for each file modified.
USAGE="Bulk converter for wiki pages.

convert-repo.sh <path-to-wiki2gfm.py> <path-to-git-repo-root>
"

if [ $# -eq 0 ] ; then
    echo "$USAGE"
    exit 1
fi

PATH_TO_WIKI2GMF=$1
GIT_REPO_ROOT=$2

for wikifile in `find "$GIT_REPO_ROOT" -name "*.wiki"`
do
  mdfile="`dirname $wikifile`/`basename $wikifile .wiki`.md"

  printf "**************************\n"
  printf "Converting wiki: $file\n"
  printf "To Markdown    : $mdfile\n"
  printf "**************************\n"

  python $PATH_TO_WIKI2GMF \
      --input_file=$wikifile \
      --output_file=$mdfile

  git rm $wikifile
  git add $mdfile
  git commit -m "Converted `basename $mdfile`"

  printf "done\n\n"
done

