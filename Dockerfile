FROM python:3.9-slim

EXPOSE 8501

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY .streamlit/secrets.toml .streamlit/secrets.toml
COPY /trades/latest.csv /trades/latest.csv

COPY src /src/

CMD streamlit run src/app.py