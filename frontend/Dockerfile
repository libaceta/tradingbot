### Stage 1: Build Angular app
FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npm run build:prod

### Stage 2: Serve with nginx
FROM nginx:1.27-alpine

COPY --from=builder /app/dist/trading-dashboard/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
