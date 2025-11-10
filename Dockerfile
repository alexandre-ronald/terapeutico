# Dockerfile
FROM python:3.11

# Define diretório de trabalho
WORKDIR /app

RUN pip install --upgrade pip

# Copia os arquivos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expõe a porta que o Django usará
EXPOSE 9500

# Comando para rodar o servidor (ajustável)
CMD ["python", "manage.py", "runserver", "0.0.0.0:9500"]
