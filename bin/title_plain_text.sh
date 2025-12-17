#!/bin/bash

## Extract the title from a tex file. 
## Argument: path to tex file

set -ex

MAIN_TEX=${1}
TEX_DIR=`dirname $MAIN_TEX`
TXT_FILE=$TEX_DIR/title.txt

rg '^\\title\{(.*)\}' $MAIN_TEX -r '$1' --no-filename --no-line-number > $TXT_FILE