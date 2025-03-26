from fastapi import FastAPI, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from bson import ObjectId
import os
from google import genai
from google.genai import types

app = FastAPI()
load_dotenv()
# Database Configuration
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "chat_db"

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
chats_collection = db["chats"]

# Models
class ChatMessage(BaseModel):
    user_id: str
    conversation_id: str
    message: str
    timestamp: str

class ChatSummaryRequest(BaseModel):
    conversation_id: str

class ChatBulkRequest(BaseModel):
    messages: List[ChatMessage]

# API Endpoints
@app.post("/chats", response_model=dict)
async def store_chat(chat: ChatMessage):
    result = await chats_collection.insert_one(chat.dict())
    return {"message": "Chat stored successfully", "chat_id": str(result.inserted_id)}

@app.post("/chats/bulk", response_model=dict)
async def store_bulk_chats(chat_bulk: ChatBulkRequest):
    if not chat_bulk.messages:
        raise HTTPException(status_code=400, detail="No chat messages provided.")
    
    chat_dicts = [chat.dict() for chat in chat_bulk.messages]
    result = await chats_collection.insert_many(chat_dicts)
    return {"message": "Chats stored successfully", "inserted_ids": [str(id) for id in result.inserted_ids]}


@app.get("/chats/{conversation_id}", response_model=List[ChatMessage])
async def retrieve_chats(conversation_id: str):
    chats = await chats_collection.find({"conversation_id": conversation_id}).to_list(None)
    if not chats:
        raise HTTPException(status_code=404, detail="No chats found for this conversation.")
    return chats

@app.post("/chats/summarize")
async def summarize_chat(summary_request: ChatSummaryRequest):
    client = genai.Client(
        api_key=os.environ.get("GEMINI_KEY"),
    )

    model = "gemini-2.0-flash"
    
    chats=await retrieve_chats(summary_request.conversation_id)
    contents = [
        types.Content(role="user",parts=[
                types.Part.from_text(text=f"""
                        summarize the chats with same conversation_id and give only the summary
                        {chats}
                        """)]
                        )
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )

    out=''

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")
        out+=chunk.text

    return {"message": out}        

@app.get("/users/{user_id}/chats")
async def get_user_chats(user_id: str, page: int = 1, limit: int = 10):
    skip = (page - 1) * limit
    chats = await chats_collection.find({"user_id": user_id}).skip(skip).limit(limit).to_list(None)
    
    # Convert ObjectId to string
    for chat in chats:
        chat["_id"] = str(chat["_id"])
    
    return chats

@app.delete("/chats/{conversation_id}")
async def delete_chat(conversation_id: str):
    result = await chats_collection.delete_many({"conversation_id": conversation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No chats found to delete.")
    return {"message": "Chats deleted successfully"}
