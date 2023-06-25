FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy your application code to the container
COPY . /app/api

# Install dependencies
RUN pip install --no-cache-dir -r api/requirements.txt

# Set the PYTHONPATH environment variable to include the /app directory
ENV PYTHONPATH "${PYTHONPATH}:/app"

# Expose the port on which your server will listen
EXPOSE 80

# Update the CMD command to import and run the correct application
CMD ["waitress-serve", "--port=80", "--call", "api:create_app"]
