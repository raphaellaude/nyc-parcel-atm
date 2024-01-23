FROM node:18
WORKDIR /app
COPY pluto-hist/package.json .
RUN npm install
COPY pluto-hist/ .
RUN npm run build
EXPOSE 8080
CMD [ "npm", "run", "preview" ]