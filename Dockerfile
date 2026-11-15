FROM python:3.12-slim
WORKDIR /service
COPY app/ ./app/
RUN useradd --uid 10001 --create-home serviceuser
USER serviceuser
ENV PORT=8080 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
CMD ["python", "-m", "app.main"]
