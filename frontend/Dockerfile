# Stage 1: Build the React application
FROM node:20-alpine AS build
WORKDIR /app

# Copy package files and install dependencies using clean install
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code and config files
COPY . .

# Run production build
RUN npm run build

# Stage 2: Serve built static assets using Nginx
FROM nginx:1.25-alpine
# Copy basic configuration supporting React SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy built files from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
