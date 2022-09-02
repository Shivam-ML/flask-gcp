FROM python:3.9
WORKDIR /flaskapps
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8087
CMD ["python3","search_q.py"]
