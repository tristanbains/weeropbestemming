# Stage 1:
FROM node:18-bookworm-slim AS builder

WORKDIR /app

COPY package.json ./

# RUN npm install -g npm
RUN npm install

COPY . .

# Stage 2:
FROM jupyter/scipy-notebook:latest

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt requirements.txt

# Install additional packages
RUN pip install -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose web and jupyter notebook ports
EXPOSE 5777
EXPOSE 8777

# Define different commands for web and jupyter notebook
CMD ["sh", "-c", "true"]