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
    getPriceProcess=`ps aux | grep get_cu_price_and_sub_redis | grep -v "grep" `
    if [ -z $getPriceProcess ]
    then
        echo "getPriceProcess is restarted"
        nohup python get_cu_price_and_sub_redis.py &
    else
         echo "getPriceProcess is running"
    fi
    sleep 60 #每 60s检查一次
done