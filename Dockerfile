FROM python:3.6.15

WORKDIR /srv/

COPY ./requirements.txt ./
RUN pip install -r requirements.txt
# COPY ./tg_channel_downloader.py ./

CMD ["python", "-m", "http.server", "9000"]
#CMD ["python", "tg_channel_downloader.py"]