FROM node:20-slim

WORKDIR /app

COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci

COPY app/frontend ./

ENV VITE_API_BASE_URL=http://localhost:8000

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]
