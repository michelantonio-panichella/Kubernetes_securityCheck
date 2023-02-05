FROM python:3.9

WORKDIR /Users/michelantoniopanichella/PycharmProjects/Progetto_Tesi

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ADD main.py .

CMD ["python", "./main.py"]