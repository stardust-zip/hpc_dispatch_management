# Step 1: Use an official Python runtime as a parent image
FROM python:3.11-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Step 4: Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of the application files into the container
# This is the key change. `COPY . .` copies everything from the build context
# (your project root) into the container's working directory (`/app`).
COPY . .

# Step 6: Expose the port the app will run on
EXPOSE 8888

# Step 7: Define the command to run your app
# The path is correct because the WORKDIR is /app
CMD ["uvicorn", "src.hpc_dispatch_management.main:app", "--host", "0.0.0.0", "--port", "8888"]
