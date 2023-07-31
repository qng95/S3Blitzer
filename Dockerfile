FROM python:3.11.4

COPY s3blitzer /s3blitzer/
COPY requirements.txt /s3blitzer/


RUN \
   python3 -m pip install -r /s3blitzer/requirements.txt


ENTRYPOINT ["/bin/bash"]
