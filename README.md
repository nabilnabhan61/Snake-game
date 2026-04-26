## HOW TO USE:

## REQUIREMENTS 
BEFORE RUNNING THIS PROJECT MAKE SURE YOU HAVE:
- python 3.13 installed 
- then run in your terminal "py -3.13 -m pip install -r requirements.txt"
- the requirements file contains pygame and python-dotenv

## to Start the server 
py -3.13 run_server.py 5000

## to start the client 
py -3.13 run_client.py

## if you are on the same device you can use the same .env file

## if you want to use different devices but on the same network
update the .env file's SERVER_IP with the networks IP address 
for example if your IPv4 address is 192.168.1.25
update the .env file to: SERVER_IP=192.168.1.25
No need to change the SERVER_PORT unless when you start the server and you are given "Only one usage of each socket address" then just change to any available port number on your device
