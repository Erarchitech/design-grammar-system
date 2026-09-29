FROM node:20-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
COPY gen-config.sh /gen-config.sh
RUN chmod +x /entrypoint.sh /gen-config.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
