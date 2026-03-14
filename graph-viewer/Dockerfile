FROM node:20-alpine AS model-viewer-builder

WORKDIR /app/model-viewer
COPY model-viewer/package.json ./
COPY model-viewer/package-lock.json ./
RUN npm ci
COPY model-viewer ./
RUN npm run build

FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY config.template.js /usr/share/nginx/html/config.template.js
COPY entrypoint.sh /entrypoint.sh
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=model-viewer-builder /app/model-viewer/dist /usr/share/nginx/html/model-viewer

RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
