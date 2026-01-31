FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY config.template.js /usr/share/nginx/html/config.template.js
COPY entrypoint.sh /entrypoint.sh
COPY nginx.conf /etc/nginx/conf.d/default.conf

RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
