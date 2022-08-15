FROM python:3.8.13

WORKDIR /srv/

RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple/ pip -U
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/

COPY ./requirements.txt ./
RUN pip3 install -r requirements.txt
# COPY ./tg_channel_downloader.py ./

CMD ["python", "-m", "http.server", "9000"]
#CMD ["python", "tg_channel_downloader.py"]