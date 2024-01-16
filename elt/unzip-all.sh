#!/bin/bash

DIR=$1
DEST=$2

if [ ! -d "$DIR" ]; then
    echo "Directory $DIR does not exist"
    exit 1
fi

if [ ! -d "$DEST" ]; then
    mkdir $DEST
fi

for file in $DIR/*.zip; do
    filename=$(basename -- "$file")
    # extension="${filename##*.}"
    filename="${filename%.*}"
    echo "Unzipping $filename"
    mkdir $DEST/${filename%}
    unzip $file -d $DEST/${filename%}
done
