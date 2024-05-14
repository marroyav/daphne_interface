#!/bin/bash

echo -e "\e[36m[INFO] Welcome to the script for acquiring IV curves! [Make sure you have no bias]"
echo -e "\e[36m To execute the script just run: sh run_ivcurves.sh and all the IPs will be acquired in individual tmux sessions."
echo -e " For running over personalized IP(s) run: sh run_ivcurves.sh \"104 105\""
echo -e " Enjoy! :) \n \e[0m"

# Define the command you want to run in each session
command_to_run="python bias_trim_scan.py -ip 10.73.137."

if [ -n "$1" ];then
    IFS=' ' read -r -a your_ips <<< "$1"
    else
        your_ips=(104 105 107 109 111 112 113)
fi

# The confirmation message need to be run with $ bash setup.sh (this lines are to allow $ sh setup.sh too)
if [ ! "$BASH_VERSION" ] ; then
    exec /bin/bash "$0" "$@"
fi

echo -e "\e[31mWARNING: You are about to acquire iv_curves data for IP(s): ["${your_ips[@]}"] !\e[0m"
read -p "Are you sure you want to continue? (y/n) " -n 1 -r
echo
# If the user did not answer with y, exit the script
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# Create 7 tmux sessions one for each endpoint
for i in ${your_ips[@]}
do
    # Create a new detached session with a unique name
    tmux new-session -d -s "IP_$i"

    # Send the command to the session
    tmux send-keys -t "IP_$i" "$command_to_run$i" C-m
    echo "Command $command_to_run$i sent correctly!"

done