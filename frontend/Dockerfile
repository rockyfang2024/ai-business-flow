FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install --silent

COPY . .

EXPOSE 3000

ENV PORT=3000
ENV NODE_ENV=production

CMD ["npm", "start"]