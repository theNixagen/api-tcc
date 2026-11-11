FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV npm_config_cache=/tmp/npm-cache
CMD ["npm", "run", "build:server", "--", "--emptyOutDir"]
