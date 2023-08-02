FROM --platform=linux/amd64 python:3.11.4

COPY s3blitzer /s3blitzer/
COPY requirements.txt /s3blitzer/


RUN \
    mkdir -p /s3blitzer/testfiles/ && \
    python3 -m pip install -r /s3blitzer/requirements.txt


ENTRYPOINT ["/bin/bash"]
