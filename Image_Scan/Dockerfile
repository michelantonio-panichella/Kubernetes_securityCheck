FROM python:3.9

RUN mkdir /app
WORKDIR /app/
ADD . /app/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "./main.py"]