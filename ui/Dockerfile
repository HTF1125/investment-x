# --- Frontend Dockerfile ---
FROM node:20-slim

WORKDIR /app

# Install dependencies separately to leverage Docker cache
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Set environment variables for build
# This is needed during 'next build' for static generation or setting client-side env vars
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build the application
RUN npm run build

# Expose the application port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
