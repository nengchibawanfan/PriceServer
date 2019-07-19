#!/bin/sh
while true;
do
    priceserverProcess=`ps aux | grep new_new_price_server | grep -v "grep" `
    if [ -z $priceserverProcess ]
    then
        echo "priceserverProcess is restarted"
        pm2 start /home/ubuntu/newPriceServer/PriceServer/new_new_price_server
    else
        echo "priceserverProcess is running"
    fi
    sleep 60 #每 60s检查一次
done