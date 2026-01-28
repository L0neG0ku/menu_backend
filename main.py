from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
import json
import os
from uuid import uuid4

app = FastAPI(title="Menu System API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "menus.json")
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")

# Ensure folders exist
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Serve images
app.mount("/images", StaticFiles(directory=IMAGE_FOLDER), name="images")


# -----------------------------
# Utility functions
# -----------------------------

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# -----------------------------
# APIs
# -----------------------------

@app.get("/")
def health():
    return {"status": "API Running"}


# ➕ Create Restaurant (Master App)
@app.post("/restaurant")
def create_restaurant(name: str):
    data = load_data()
    restaurant_id = str(uuid4())[:6]

    data["restaurants"][restaurant_id] = {
        "name": name,
        "menu": []
    }

    save_data(data)

    return {
        "restaurant_id": restaurant_id,
        "name": name
    }


# 📄 Get Menu (TV App)
@app.get("/menu/{restaurant_id}")
def get_menu(restaurant_id: str):
    data = load_data()
    restaurant = data["restaurants"].get(restaurant_id)

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return restaurant


# ➕ Add Menu Item (Master App)
@app.post("/menu/{restaurant_id}/item")
def add_menu_item(
    restaurant_id: str,
    name: str,
    price: float,
    image: UploadFile = File(...)
):
    data = load_data()
    restaurant = data["restaurants"].get(restaurant_id)

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Save image
    ext = image.filename.split(".")[-1]
    image_name = f"{uuid4()}.{ext}"
    image_path = os.path.join(IMAGE_FOLDER, image_name)

    with open(image_path, "wb") as f:
        f.write(image.file.read())

    item = {
        "id": str(uuid4())[:6],
        "name": name,
        "price": price,
        "image": f"/images/{image_name}"
    }

    restaurant["menu"].append(item)
    save_data(data)

    return item
