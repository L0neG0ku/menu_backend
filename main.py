from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import json
import os
from uuid import uuid4
import requests
import base64

# -----------------------------------
# App Setup
# -----------------------------------

app = FastAPI(title="Menu Display System API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_FOLDER = os.path.join(BASE_DIR, "images")

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Serve images
app.mount("/images", StaticFiles(directory=IMAGE_FOLDER), name="images")

# -----------------------------------
# GitHub Config (ENV VARIABLES)
# -----------------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")          # e.g. username/repo
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "master")

GITHUB_API = "https://api.github.com"
DATA_PATH = "data/menus.json"


def github_headers():
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN not set")

    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }


# -----------------------------------
# GitHub Helpers
# -----------------------------------

def load_data():
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{DATA_PATH}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=github_headers())
    r.raise_for_status()

    content = r.json()
    decoded = base64.b64decode(content["content"]).decode("utf-8")
    return json.loads(decoded)


def save_data(data, message="Update menu data"):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{DATA_PATH}"

    r = requests.get(url, headers=github_headers())
    r.raise_for_status()
    sha = r.json()["sha"]

    encoded = base64.b64encode(
        json.dumps(data, indent=2).encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": message,
        "content": encoded,
        "sha": sha,
        "branch": GITHUB_BRANCH
    }

    r = requests.put(url, headers=github_headers(), json=payload)
    r.raise_for_status()


# -----------------------------------
# Health Check
# -----------------------------------

@app.get("/")
def health():
    return {"status": "API running 🚀"}


# -----------------------------------
# Restaurant APIs
# -----------------------------------

@app.post("/restaurant")
def create_restaurant(name: str = Form(...)):
    data = load_data()

    restaurant_id = str(uuid4())[:6]

    data["restaurants"][restaurant_id] = {
        "name": name,
        "categories": {}
    }

    save_data(data, f"Create restaurant {restaurant_id}")

    return {
        "restaurant_id": restaurant_id,
        "name": name
    }


@app.get("/menu/{restaurant_id}")
def get_menu(restaurant_id: str):
    data = load_data()
    restaurant = data["restaurants"].get(restaurant_id)

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return restaurant


# -----------------------------------
# Category APIs
# -----------------------------------

@app.post("/menu/{restaurant_id}/category")
def create_category(
    restaurant_id: str,
    category_name: str = Form(...)
):
    data = load_data()
    restaurant = data["restaurants"].get(restaurant_id)

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    category_id = category_name.lower().replace(" ", "_")

    if category_id in restaurant["categories"]:
        raise HTTPException(status_code=400, detail="Category already exists")

    restaurant["categories"][category_id] = {
        "name": category_name,
        "items": []
    }

    save_data(
        data,
        f"Create category {category_name} in restaurant {restaurant_id}"
    )

    return {
        "category_id": category_id,
        "name": category_name
    }


# -----------------------------------
# Menu Item APIs
# -----------------------------------

@app.post("/menu/{restaurant_id}/category/{category_id}/item")
def add_menu_item(
    restaurant_id: str,
    category_id: str,
    name: str = Form(...),
    price: float = Form(...),
    image: UploadFile = File(...)
):
    data = load_data()
    restaurant = data["restaurants"].get(restaurant_id)

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    category = restaurant["categories"].get(category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

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

    category["items"].append(item)

    save_data(
        data,
        f"Add item {item['id']} to {category_id} ({restaurant_id})"
    )

    return item
