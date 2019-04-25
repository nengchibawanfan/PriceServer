#!/bin/sh
while true;
do
    priceserverProcess=`ps aux | grep new_price_server | grep -v "grep" `
    if [ -z $priceserverProcess ]
    then
        echo "priceserverProcess is restarted"
        nohup gunicorn -c gunicorn_conf.py new_price_server:app &
    else
        echo "priceserverProcess is running"
    fi
    sleep 60 #每 60s检查一次
done