node:18-slim

WORKDIR /app

COPY package*.json ./
RUN npm install --silent

COPY . .

EXPOSE 3000

ENV PORT=3000
ENV API_URL=http://backend:8000

CMD ["npm", "start"]