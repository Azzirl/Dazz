FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Exponer el puerto nativo de Streamlit
EXPOSE 8501

# Comando de ejecución
CMD ["streamlit", "run", "App.py", "--server.port=8501", "--server.address=0.0.0.0"]
