FROM python:3.9-slim
WORKDIR /app
RUN pip install Flask
COPY app.py .
CMD ["python3", "app.py"]