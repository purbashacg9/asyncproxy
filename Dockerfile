#FROM ubuntu:14.04
FROM python:2.7
ADD . /srv

WORKDIR /srv
#RUN apt-get update && apt-get install -y \
#                    python2.7 \
#                    python-pip \
#    && apt-get clean \
#    && rm -rf /var/lib/apt/lists/*

#RUN ln -s /usr/bin/python2.7 /usr/bin/python
#RUN ln -s /usr/bin/python2.7  /usr/bin/python2

#RUN pip install tornado
#RUN pip install futures

RUN pip install -r requirements.txt

ENV DIRPATH /srv
ENV DIRNAME asyncproxy
ENV PYTHONPATH $DIRPATH/$DIRNAME


#RUN cd $DIRPATH && mkdir $DIRNAME
#COPY handlers $DIRNAME/handlers/
#COPY processrange $DIRNAME/processrange/
#COPY utils $DIRNAME/utils/
#COPY app.py $DIRNAME/
#COPY settings.conf $DIRNAME/

EXPOSE 8888
CMD python app.py

