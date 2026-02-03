FROM node:20.10-slim

ENV PATH /app/node_modules/.bin:$PATH

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY src src
COPY static static
COPY vite.config.ts vite.config.ts

CMD ["npm", "run", "dev"]
