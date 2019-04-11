FROM python:3.6

RUN mkdir /usr/src/priceserver

WORKDIR /usr/src/priceserver

ADD . /usr/src/priceserver

COPY auto_restart.sh /usr/bin/auto_restart.sh

RUN chmod +x /usr/bin/auto_restart.sh

EXPOSE 5000

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["auto_restart.sh"]