# Imagem do site (SCRUM-55): gera o build do Vite e serve com nginx.
# Construa pelo compose, da raiz do repositório:
#   docker compose up -d --build site        (site em http://localhost:8080)
#
# O nginx serve os arquivos estáticos e repassa /api/ para o serviço `api` do compose (nginx.conf).
# O site não guarda segredo: a única variável de build é VITE_EMAIL_REMOCAO, que é pública
# (vai para o navegador, no rodapé).

FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_EMAIL_REMOCAO=""
ENV VITE_EMAIL_REMOCAO=${VITE_EMAIL_REMOCAO}
RUN npm run build

FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
