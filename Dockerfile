FROM python:3.9
WORKDIR /flaskapps
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python3","main2.py"]
