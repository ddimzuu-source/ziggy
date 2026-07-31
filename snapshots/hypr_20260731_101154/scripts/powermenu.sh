#!/usr/bin/env bash

options="⏻  Shutdown\n  Reboot\n  Lock\n󰍃  Logout"

selected=$(echo -e "$options" | wofi --dmenu --prompt "Power Menu" --width 250 --height 220)

case "$selected" in
    *Shutdown*)
        systemctl poweroff
        ;;
    *Reboot*)
        systemctl reboot
        ;;
    *Lock*)
        hyprlock
        ;;
    *Logout*)
        hyprctl dispatch exit
        ;;
esac
