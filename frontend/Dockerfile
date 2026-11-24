FROM node:20-alpine
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
ARG API_INTERNAL_URL
ENV API_INTERNAL_URL=$API_INTERNAL_URL
RUN npm run build
CMD ["npm", "start"]
