FROM node:22-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY tsconfig.json ./
COPY src ./src
RUN npx tsc -p tsconfig.json
ENV PORT=4000
EXPOSE 4000
CMD ["node", "dist/index.js"]
