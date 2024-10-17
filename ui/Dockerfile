FROM node:20.10-slim AS build

WORKDIR /app

COPY package*.json ./

RUN npm install
COPY . .
RUN npm run build


FROM nginx:latest

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
