#!/bin/bash
# gnudiridx.sh

# Mangled: 2020-Jun by tomc
# Updated: Wed Apr 10 21:04:12 2013 by webmaster@askapache
# @ http://u.askapache.com/2013/04/gnu-mirror-index-creator.txt
# Copyright (C) 2013 Free Software Foundation, Inc.
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.


#function Directory-Index-Creator ()

function gnudiridx () {
    # call it right or die
    [[ $# != 2 ]] && echo "bad args. do: $FUNCNAME '/DOCUMENT_ROOT/' '/' " && exit 2
  
    # D is the doc_root containing the site
    local L= D="$1" SUBDIR="$2" F=

    # The index.html file to create
    F="${D}index.html"

    # if dir doesnt exist, create it
    [[ -d $D ]] || mkdir -p $D;

    # cd into dir or die
    cd $D || exit 2;

    # touch index.html and check if writable or die
    touch $F && test -w $F || exit 2;

    # remove empty directories, they dont need to be there and slow things down if they are
    # find . -maxdepth 1 -type d -empty -exec rm -rf {} \;

    # start of total output for saving as index.html
    (

        # print the html header
        echo '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">';
        echo "<html><head><title>${SUBDIR}</title><!--Generated--></head>";
        echo "<body><h1>${SUBDIR}</h1><pre>";
        echo "      Name                                        Last modified      Size";

        # start of content output
        (
            # change IFS locally within subshell so the for loop saves line correctly to L var
            IFS=$'\n';

            # pretty sweet, will mimick the normal apache output
            for L in $(find -L . -mount -depth -maxdepth 1 -type f ! -name 'index.html' -printf "      <a href=\"%f\">%-44f@_@%Td-%Tb-%TY %Tk:%TM  @%f@\n"|sort|sed 's,\([\ ]\+\)@_@,</a>\1,g');
            do
                # file
                F=$(sed -e 's,^.*@\([^@]\+\)@.*$,\1,g'<<<"$L");

                # file with file size
                F=$(du -bh $F | cut -f1);

                # output with correct format
                sed -e 's,\ @.*$, '"$F"',g'<<<"$L";
            done;
        )

        # now output a list of all directories in this dir (maxdepth 1) other than '.' outputting in a sorted manner exactly like apache
        find -L . -mount -depth -maxdepth 1 -type d ! -name '.' -printf "      <a href=\"%f\">%-43f@_@%Td-%Tb-%TY %Tk:%TM  -\n"|sort -d|sed 's,\([\ ]\+\)@_@,/</a>\1,g'

        # print the footer html
        echo "</pre></body></html>";

    # finally save the output of the subshell to index.html
    )  > $F;

}

# start the run ( use function so everything is local and contained )
#    $1 is absolute document_root with trailing '/'
#    $2 is subdir like '/subdir/' if thats the web root, '/' if no subdir

gnudiridx "${PWD}/" "${PWD##*/}"

exit
