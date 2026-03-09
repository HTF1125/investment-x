# --- Frontend Dockerfile ---
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies separately to leverage Docker cache
COPY package*.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Set environment variables for build
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG INTERNAL_API_URL=http://backend:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV INTERNAL_API_URL=$INTERNAL_API_URL

# Build the application
RUN npm run build

# Stage 2: Runtime image
FROM node:20-slim

WORKDIR /app

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copy only what's needed to run
COPY --from=builder --chown=appuser:appuser /app/package*.json ./
COPY --from=builder --chown=appuser:appuser /app/.next ./.next
COPY --from=builder --chown=appuser:appuser /app/public ./public
COPY --from=builder --chown=appuser:appuser /app/node_modules ./node_modules

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
