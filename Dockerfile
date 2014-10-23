FROM python:3.4

ADD requirements.txt /src/requirements.txt
RUN cd /src; pip install -r requirements.txt

ADD . /src

EXPOSE 5000
CMD ["python", "/src/shinobi.py"]
