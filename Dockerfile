FROM python:3.11-slim

WORKDIR /app

# Copy root requirements
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy dashboard requirements
COPY dashboard/requirements.txt dashboard/
RUN pip install --no-cache-dir -r dashboard/requirements.txt

RUN pip install awslambdaric

# Copy all project files
COPY . .

ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/local/bin/aws-lambda-rie
RUN chmod +x /usr/local/bin/aws-lambda-rie
# ✅ Set AWS region (and optionally creds if needed)
ENV AWS_DEFAULT_REGION=us-east-2
# You can also add these if you want hardcoded creds (not recommended for prod):


# Expose ports
EXPOSE 8080 8501

# Install supervisor
RUN pip install supervisor

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Start supervisor
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
