#!/bin/sh
while true;
do
processExist=`ps aux | grep gunicorn | grep -v "grep" `
if [ -z $processExist ];then
echo "proecss is restarted"
gunicorn -c gunicorn_conf.py new_price_server:app
else
 echo "process is running"
fi
sleep 60 #每 60s检查一次
done