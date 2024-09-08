FROM node:20.10-slim

COPY package.json package.json

RUN npm install --omit=dev

COPY . .

RUN npm run build

ENTRYPOINT ["npx", "serve", "--listen", "80", "--single", "dist"]
