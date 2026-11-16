# Assistente do mapa: interpreta a pergunta com um modelo gratuito. Serviço separado no EasyPanel (Caminho de Build: /ia).
FROM node:22-alpine
WORKDIR /app
COPY servidor.mjs visitas.mjs ./
# pasta do contador de visitas: o volume do EasyPanel herda o dono na primeira montagem
RUN mkdir -p /data && chown node:node /data
ENV DADOS_DIR=/data
ENV NODE_ENV=production
EXPOSE 3000
USER node
CMD ["node", "servidor.mjs"]
