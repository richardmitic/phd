#!/bin/bash

set -ex

ABSTRACT_TEX=${1}
TEX_DIR=`dirname $ABSTRACT_TEX`
TEX_FILE=`basename $ABSTRACT_TEX`
HTML_FILE=`basename $ABSTRACT_TEX .tex`.html
TXT_FILE=`basename $ABSTRACT_TEX .tex`.txt

# Abstract: tex -> html -> text -> double newlines
(cd $TEX_DIR && htlatex $TEX_FILE && textutil -convert txt $HTML_FILE && sed -i '' 's/$/\n/g' $TXT_FILE)