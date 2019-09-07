#!/bin/bash

if [ $# -eq 1 ];then
    use_old=true
else
    use_old=false
fi

if [ $use_old == "true" ];then
    makefile="Makefile.new"
    setbash="set_bash.new"
else
    makefile="Makefile"
    setbash="set_bash"
fi

source $setbash;
make -f $makefile clean ; make -f $makefile; ./chip_cp
