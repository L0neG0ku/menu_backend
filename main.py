from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import json
import os
from uuid import uuid4
import requests
import base64

# -----------------------------------
# App
# -----------------------------------

app = FastAPI(title="Menu System API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Serve images
app.mount("/images", StaticFiles(directory=IMAGE_FOLDER), name="images")

# -----------------------------------
# GitHub Config (from Render env vars)
# -----------------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")         
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

GITHUB_API = "https://api.github.com"
DATA_PATH = "menu_backend/data/menus.json"


def github_headers():
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN not configured in environment variables")

    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }


# -----------------------------------
# GitHub File Helpers
# -----------------------------------

def load_data():
    """
    Read menus.json from GitHub repo
    """
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{DATA_PATH}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=github_headers())
    r.raise_for_status()

    content = r.json()
    decoded = base64.b64decode(content["content"]).decode("utf-8")
    return json.loads(decoded)


def save_data(data, commit_message="Update menu data"):
    """
    Write menus.json back to GitHub repo
    """
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{DATA_PATH}"

    # Get current file SHA
    r = requests.get(url, headers=github_headers())
    r.raise_for_status()
    sha = r.json()["sha"]

    encoded_content = base64.b64encode(
        json.dumps(data, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha,
        "branch": GITHUB_BRANCH
    }

    r = requests.put(url, headers=github_headers(), json=payload)
    r.raise_for_status()


# -----------------------------------
# APIs
# -----------------------------------

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

    save_data(data, f"Create restaurant {restaurant_id}")

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


# ➕ Add Menu Item (with image)
@app.post("/menu/{restaurant_id}/item")
def add_menu_item(
    restaurant_id: str,
    name: str = Form(...),
    price: float = Form(...),
    image: UploadFile = File(...)
):
    data = load_data()
    restaurant = data["restaurants"].get(restaurant_id)

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Save image locally (served by Render)
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

    save_data(data, f"Add item {item['id']} to restaurant {restaurant_id}")

    return item
