FROM node:20.10-slim

ENV PATH /app/node_modules/.bin:$PATH

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev"]
