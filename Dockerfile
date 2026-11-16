# Site estático (pasta site/) servido por nginx. Usado pelo EasyPanel em mapa.feliperodrigues.cloud.
FROM nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY site/ /usr/share/nginx/html/
# versão da publicação nos endereços de css, js e dados: proxy ou navegador nunca servem arquivo de uma versão anterior
RUN V=$(date +%Y%m%d%H%M%S) && sed -i "s/__V__/$V/g" /usr/share/nginx/html/index.html /usr/share/nginx/html/css/site.css
EXPOSE 80
