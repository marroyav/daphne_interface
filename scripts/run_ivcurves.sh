#!/bin/bash

# Define the command you want to run in each session
command_to_run="python bias_trim_scan.py -bs 10 -ts 40 -ip 10.73.137."

# Create 7 tmux sessions one for each endpoint
for i in 104 105 107 109 111 112 113
do
    # Create a new detached session with a unique name
    tmux new-session -d -s "IP_$i"

    # Send the command to the session
    tmux send-keys -t "IP_$i" "$command_to_run$i" C-m
    echo "Command $command_to_run$i sent correctly!"

done