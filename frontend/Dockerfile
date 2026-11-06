FROM node:22.23.4-bookworm-slim
WORKDIR /srv/frontend
RUN npm install --global npm@11.21.1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN chown -R node:node /srv/frontend
USER node
EXPOSE 5173
CMD ["npm", "run", "dev"]
