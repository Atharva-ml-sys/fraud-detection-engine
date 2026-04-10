# Dockerfile — Docker ko instructions deta hai
# "Mere container ko kaise banao"

# Step 1: Base image — Python 3.11 already installed hoga
FROM python:3.11-slim

# Step 2: Container ke andar working directory set karo
WORKDIR /app

# Step 3: requirements.txt copy karo
COPY requirements.txt .

# Step 4: Libraries install karo
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Apna code copy karo
COPY . .

# Step 6: Jab container start ho — yeh command run karo
CMD ["python3", "transaction_generator.py"]