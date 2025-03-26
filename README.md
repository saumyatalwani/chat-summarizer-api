### Installation

First, we need to create a .env file and specify the API Key for Gemini API and the MongoDB URI in the env file in the following format : 

```env
GEMINI_KEY=
MONGO_URI=
```
be careful not to put any quotes or spaces

then we need to run 

```sh
docker build -t fastapi-chat-app .  
```

to build the docker file and then 

```sh
docker run -d -p 8000:8000 --env-file .env fastapi-chat-app
```

to run the app

you'll find the docs at https://localhost:8000/docs