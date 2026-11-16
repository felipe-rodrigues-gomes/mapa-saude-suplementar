# Assistente do mapa: interpreta a pergunta com um modelo gratuito. Serviço separado no EasyPanel (Caminho de Build: /ia).
FROM node:22-alpine
WORKDIR /app
COPY servidor.mjs .
ENV NODE_ENV=production
EXPOSE 3000
USER node
CMD ["node", "servidor.mjs"]
