# Use official Node image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Expose the Next.js port
EXPOSE 3000

# Command to run the frontend in dev mode
CMD ["npm", "run", "dev"]