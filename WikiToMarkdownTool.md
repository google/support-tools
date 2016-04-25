This document describes how you can convert Google Code wiki pages to [GitHub-flavored Markdown](https://help.github.com/articles/github-flavored-markdown/). This variant of Markdown is also compatible with Bitbucket’s wiki format.

Once the Google Code project's .wiki files have been converted to Markdown, you will need to import them into your GitHub or Bitbucket repo using their web UI, or check the files directly into the repo.

# Install Python #
First you need to [install Python](https://www.python.org/downloads/), though it should be already installed on most Mac and Linux machines.

Next, [clone the support-tools Google Code project](https://code.google.com/p/support-tools/source/checkout) (i.e. _this_ project's source code).

```
git clone https://code.google.com/p/support-tools/
```

# Run the Converter #
With the conversion tool, all you need to do is simply run it on your project’s wiki pages.

Google Code stores wikis along with project source code, but the exact location depends on the type of project (Subversion, Mercurial, or Git).

Git and Mercurial projects store wikis in a separate repo, so to get access to your wiki files you need to clone the "wiki" subrepo. For example, if you want to get access to all of the wiki files in the "codesearch" project, simply clone the "codesearch.wiki" repository.

```
hg clone https://code.google.com/p/codesearch.wiki/ 
```

Subversion projects store the wikis directly in the svn repository, in the `/wiki` folder. For example:

```
svn checkout http://chromium.googlecode.com/svn/wiki chromium-wiki
```

## Running the converter ##

To run the `wiki2gfm` tool, simply run:

```
python ./wiki2gfm.py \
    --input_file <your_wiki_to_convert.wiki> \
    --output_file <output_file_path.md>
```

The conversion process may output warnings to the console. This is expected as Google Code’s wiki syntax cannot always be converted to Markdown. Take a look over these warnings, along with the output to ensure no undesirable formatting has occurred.

There are several additional flags that may be of use:

`--project`: The name of your Google Code project. It is possible to refer to your project name indirectly in wiki syntax; providing this option makes it possible for the converter to resolve your project name when this occurs.

`--wikipages_list`: The list of wiki pages that are assumed to exist for the purpose of auto-linking to other pages. Wiki syntax allows auto-linking to other wiki pages, if they exist. Providing a list of wiki pages that do actually exist to the converter allows it to optimistically link to the converted page of another wiki.

`--wikipages_path`: An alternate way of providing the same information as --wikipages\_list, this is a list of directories to search for .wiki files, the names of which are used as if they were provided via --wikipages\_list.

`--[no_]symmetric_headers`: Controls whether or not headers in Markdown are given symmetric header guards. In Markdown, a header is indicated by a number of # symbols, and only the leading group of symbols is required; however, for aesthetic purposes it is sometimes desirable for the header to be surrounded by equal numbers of #. This flag controls this.

# Bulk conversion #
For projects with many wiki pages, manually typing in the name of each wiki file can get tedious. To bulk-convert all of a project’s wiki pages, you can use the following Bash script:

```
#!/bin/bash

# Bulk converts wiki pages. Usage:
# bulk-convert.sh <path-to-wiki2gmf.py> <path-to-wiki-files> <output-folder>
USAGE="Bulk converter for wiki pages.

Example usage:
$ mkdir converted-wikis
$ ./bulk-convert.sh \ 
     ./support-tools/wiki_to_md/wiki2gfm.py \ 
     ./google-code-project.wiki/ \ 
     ./converted-wikis/
"

if [ $# -eq 0 ] ; then
    echo "$USAGE"
    echo 
    exit 1
fi

PATH_TO_WIKI2GMF=$1
PATH_TO_WIKIS=$2
OUTPUT_DIR=$3

for file in `ls $PATH_TO_WIKIS`
do
  printf "**************************\n"
  printf "Converting $file\n"
  printf "**************************\n"

  python $PATH_TO_WIKI2GMF \
      --input_file=$PATH_TO_WIKIS/$file \
      --output_file=$OUTPUT_DIR/$file.md

  printf "done\n\n"

done
```