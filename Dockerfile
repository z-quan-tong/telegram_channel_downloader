FROM python:3.8.13

WORKDIR /srv/

COPY ./requirements.txt ./
RUN pip install -r requirements.txt
# COPY ./tg_channel_downloader.py ./

CMD ["python", "-m", "http.server", "9000"]
#CMD ["python", "tg_channel_downloader.py"]