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
# Copiamos como template para que envsubst reemplace $BOT_URL al arrancar
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80
# envsubst reemplaza $BOT_URL en el template antes de iniciar nginx
CMD ["/bin/sh", "-c", "envsubst '$BOT_URL' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
