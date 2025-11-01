# Step 1: Use an official Python runtime as a parent image
FROM python:3.11-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Step 4: Install any needed packages specified in requirements.txt
# Using --no-cache-dir makes the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the application source code into the container
COPY ./src /app/src

# Step 6: Expose the port the app will run on
EXPOSE 8888

# Step 7: Define the command to run your app
# Uvicorn is the server that will run your FastAPI application.
# --host 0.0.0.0 is crucial to make the server accessible from outside the container.
CMD ["uvicorn", "src.hpc_dispatch_management.main:app", "--host", "0.0.0.0", "--port", "8888"]
