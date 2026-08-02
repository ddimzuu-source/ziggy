#!/usr/bin/env bash

# Buat folder jika belum ada
mkdir -p ~/Pictures/ss

FILENAME="$HOME/Pictures/ss/$(date +'%Y-%m-%d_%H-%M-%S').png"

if [ "$1" == "full" ]; then
    grim "$FILENAME"
    wl-copy < "$FILENAME"
elif [ "$1" == "area" ]; then
    grim -g "$(slurp)" "$FILENAME"
    wl-copy < "$FILENAME"
fi
