FROM ubuntu:14.04
RUN apt-get update && apt-get install -y
                    python2.7 \
                    python-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python/2.7 /usr/bin/python  
RUN ln -s /usr/bin/python2.7  /usr/bin/python2

RUN pip install tornado
RUN pip install futures

ENV DIRPATH asyncproxy
RUN mkdir /srv/$DIRPATH

WORKDIR

EXPOSE 8888
CMD ["python" "app.py"]

#cp files to a folder

#setup python path
