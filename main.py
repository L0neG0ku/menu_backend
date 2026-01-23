from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
import json
import os

app = FastAPI(title="Menu API", version="1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MENU_FOLDER = os.path.join(BASE_DIR, "menus")
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")

# Serve images publicly
app.mount("/images", StaticFiles(directory=IMAGE_FOLDER), name="images")


@app.get("/")
def home():
    return {"status": "Menu API running 🚀"}


@app.get("/menu/{user_id}")
def get_user_menu(user_id: str):
    file_path = os.path.join(MENU_FOLDER, f"user_{user_id}.json")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Menu not found for this user")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
