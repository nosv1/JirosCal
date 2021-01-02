#!/bin/sh

restart=1 # if restart is 1, bot is restarted
while [[ 1 -eq ${restart} ]]; do
	restart=0 # default to shutdown unless controller says restart

	echo "git pull" 
	git pull # update bot
	echo

	echo "python3 Controller.py"
	restart=$(python3 Controller.py | tail -n 1) # run it and store the last output line upon 'shut down of bot', last line will be a 0 or 1
	restart=$((restart+0)) # update restart based on last output line of Controller.py
	echo
done;
