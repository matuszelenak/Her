FROM node:20.10-slim

WORKDIR /app

COPY package.json package.json

RUN npm install

COPY . .

RUN npm run build

COPY serve.json dist/serve.json

ENTRYPOINT ["npx", "serve", "--listen", "80", "--single", "dist"]