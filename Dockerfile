# Site estático (pasta site/) servido por nginx. Usado pelo EasyPanel em mapa.feliperodrigues.cloud.
FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY site/ /usr/share/nginx/html/
EXPOSE 80
