"""
Phone Scraper — FULL PRODUCTION VERSION
Saare brands, saare phones, resume capability ke saath
"""
import os
import re
import json
import time
import random
import logging
from io import BytesIO
from datetime import datetime

import requests
import numpy as np
from scipy import ndimage
from bs4 import BeautifulSoup
from PIL import Image
from rembg import remove
import psycopg2
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

# ═══════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

GSM_BASE = "https://www.gsmarena.com/"
DXO_SEARCH = "https://www.dxomark.com/?s="
NANO_BASE = "https://nanoreview.net/en/phone/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

DELAY_GSM = (2.5, 5.0)
DELAY_DXO = (3.0, 6.0)
DELAY_NANO = (2.0, 4.0)

# All brands
BRANDS = {
    "Samsung":   "https://www.gsmarena.com/samsung-phones-9.php",
    "Xiaomi":    "https://www.gsmarena.com/xiaomi-phones-80.php",
    "Realme":    "https://www.gsmarena.com/realme-phones-118.php",
    "OnePlus":   "https://www.gsmarena.com/oneplus-phones-95.php",
    "Vivo":      "https://www.gsmarena.com/vivo-phones-98.php",
    "Oppo":      "https://www.gsmarena.com/oppo-phones-82.php",
    "Motorola":  "https://www.gsmarena.com/motorola-phones-4.php",
    "Google":    "https://www.gsmarena.com/google-phones-107.php",
    "Honor":     "https://www.gsmarena.com/honor-phones-121.php",
    "Nokia":     "https://www.gsmarena.com/nokia-phones-1.php",
    "Asus":      "https://www.gsmarena.com/asus-phones-46.php",
    "Infinix":   "https://www.gsmarena.com/infinix-phones-119.php",
    "Tecno":     "https://www.gsmarena.com/tecno-phones-120.php",
    "Poco":      "https://www.gsmarena.com/poco-phones-124.php",
    "iQOO":      "https://www.gsmarena.com/iqoo-phones-125.php",
    "Apple":     "https://www.gsmarena.com/apple-phones-48.php",
    "Nothing":   "https://www.gsmarena.com/nothing-phones-128.php",
    "Huawei":    "https://www.gsmarena.com/huawei-phones-58.php",
    "Lava":      "https://www.gsmarena.com/lava-phones-123.php",
    "Micromax":  "https://www.gsmarena.com/micromax-phones-15.php",
}

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ═══════════════════════════════════════════════════════════
# PROXY (ScrapeOps)
# ═══════════════════════════════════════════════════════════

def get_proxy():
    api_key = os.getenv("SCRAPEOPS_API_KEY")
    if not api_key:
        return None
    proxy_url = f"http://scrapeops:{api_key}@residential-proxy.scrapeops.io:8181"
    return {"http": proxy_url, "https": proxy_url}


def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            r = requests.get(
                url,
                headers=headers,
                proxies=get_proxy(),
                verify=False,
                timeout=120
            )
            if r.status_code == 200:
                return r.text
            if r.status_code in (403, 429):
                wait = 60 * (attempt + 1)
                log.warning(f"  HTTP {r.status_code}, waiting {wait}s...")
                time.sleep(wait)
                continue
            return None
        except requests.RequestException as e:
            log.warning(f"  Request error: {e}")
            time.sleep(10)
    return None


def delay(rng):
    time.sleep(random.uniform(*rng))


# ═══════════════════════════════════════════════════════════
# HELPERS (Same as test_scraper.py)
# ═══════════════════════════════════════════════════════════

def parse_int(text, unit=None):
    if not text: return None
    try:
        if unit:
            m = re.search(rf"(\d+(?:\.\d+)?)\s*{unit}", str(text), re.I)
            return int(float(m.group(1))) if m else None
        m = re.search(r"(\d+)", str(text))
        return int(m.group(1)) if m else None
    except: return None


def parse_float(text, unit=None):
    if not text: return None
    try:
        if unit:
            m = re.search(rf"(\d+(?:\.\d+)?)\s*{unit}", str(text), re.I)
            return float(m.group(1)) if m else None
        m = re.search(r"(\d+(?:\.\d+)?)", str(text))
        return float(m.group(1)) if m else None
    except: return None


def parse_bool(text):
    if not text: return None
    t = str(text).lower()
    if "yes" in t: return True
    if "no" in t: return False
    return None


def make_unique_id(brand, model, year):
    s = f"{brand}-{model}-{year or 'unknown'}".lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:200]


def make_slug(brand, model):
    s = f"{brand}-{model}".lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# ═══════════════════════════════════════════════════════════
# GSM SCRAPER (Same as test)
# ═══════════════════════════════════════════════════════════

def get_brand_phones(brand_url):
    """Get all phones from brand (with pagination)"""
    phones = []
    url = brand_url
    page = 1

    while url:
        log.info(f"    Brand page {page}")
        html = fetch(url)
        if not html:
            break

        soup = BeautifulSoup(html, "lxml")
        items = soup.select(".makers ul li a")
        if not items:
            break

        for item in items:
            href = item.get("href")
            name_tag = item.select_one("strong span")
            if not (href and name_tag): continue
            name = name_tag.text.strip()
            nl = name.lower()
            if any(kw in nl for kw in ["tablet", "watch", "pad", "band"]): continue
            if "_tablets-" in href or "_watches-" in href: continue
            full_url = GSM_BASE + href if not href.startswith("http") else href
            phones.append({"name": name, "url": full_url})

        nxt = soup.select_one("a.prevnextbutton[title='Next page']")
        if nxt and nxt.get("href"):
            url = GSM_BASE + nxt["href"]
            page += 1
            delay(DELAY_GSM)
        else:
            url = None

    return phones


def scrape_gsm(url):
    html = fetch(url)
    if not html: return None
    soup = BeautifulSoup(html, "lxml")
    data = {"reference_url": url}

    title = soup.select_one(".specs-phone-name-title")
    if not title: return None
    data["name"] = title.text.strip()

    container = soup.select_one(".specs-photo-main")
    if container:
        img = container.select_one("img")
        a_tag = container.select_one("a")
        src = None
        if img:
            cand = img.get("src") or img.get("data-src") or ""
            if cand and "/assets" not in cand:
                src = cand
        if not src and a_tag:
            cand = a_tag.get("href") or ""
            if cand.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                src = cand
        if src:
            data["image_url"] = src if src.startswith("http") else GSM_BASE + src.lstrip("/")

    specs = {}
    for table in soup.select("#specs-list table"):
        th = table.select_one("th")
        if not th: continue
        cat = th.text.strip()
        specs[cat] = {}
        for row in table.select("tr"):
            ttl = row.select_one(".ttl")
            nfo = row.select_one(".nfo")
            if ttl and nfo:
                k, v = ttl.text.strip(), nfo.text.strip()
                if k and v: specs[cat][k] = v

    data["specs"] = specs
    return data


def extract_columns(data, brand):
    specs = data.get("specs", {})
    def get(cat, key):
        if cat not in specs: return None
        for k, v in specs[cat].items():
            if key.lower() in k.lower(): return v
        return None

    name = data.get("name", "")
    model = name.replace(brand, "").strip() or "Unknown"

    announced = get("Launch", "Announced") or ""
    m = re.search(r"(20\d{2})", announced)
    year = int(m.group(1)) if m else None

    internal = get("Memory", "Internal") or ""
    ram = parse_int(internal, r"GB\s*RAM")
    storage = parse_int(internal, r"GB")

    size = parse_float(get("Display", "Size"), r'(inch|inches|")')
    dtype = get("Display", "Type") or ""
    refresh = parse_int(dtype, "Hz")
    resolution = get("Display", "Resolution") or None

    cam = get("Main Camera", "Triple") or get("Main Camera", "Quad") or get("Main Camera", "Dual") or get("Main Camera", "Single") or ""
    main_mp = parse_int(cam, "MP")

    cam_count = 0
    if get("Main Camera", "Triple"): cam_count = 3
    elif get("Main Camera", "Quad"): cam_count = 4
    elif get("Main Camera", "Dual"): cam_count = 2
    elif get("Main Camera", "Single"): cam_count = 1

    selfie = get("Selfie camera", "Single") or get("Selfie camera", "Dual") or ""
    selfie_mp = parse_int(selfie, "MP")

    video_res = get("Main Camera", "Video") or ""
    video_res = video_res.split(",")[0].strip()[:50] if video_res else None

    chipset_text = get("Platform", "Chipset") or ""
    chipset = chipset_text.split("\n")[0].strip()[:150] if chipset_text else None
    cl = chipset_text.lower()
    chip_brand = None
    for k, v in [("snapdragon", "Snapdragon"), ("mediatek", "MediaTek"),
                 ("dimensity", "MediaTek"), ("helio", "MediaTek"),
                 ("exynos", "Exynos"), ("apple", "Apple"),
                 ("kirin", "Kirin"), ("unisoc", "Unisoc"), ("tensor", "Google Tensor")]:
        if k in cl: chip_brand = v; break

    cpu_text = get("Platform", "CPU") or ""
    cpu_cores = None
    m = re.search(r"(\d+)[- ]core", cpu_text, re.I)
    if m: cpu_cores = int(m.group(1))

    gpu = get("Platform", "GPU") or None
    gpu = gpu[:150] if gpu else None

    battery = parse_int(get("Battery", "Type"), "mAh")
    charging = parse_int(get("Battery", "Charging"), "W")
    charging_text = (get("Battery", "Charging") or "").lower()
    has_wireless = "wireless" in charging_text if charging_text else None

    weight = parse_int(get("Body", "Weight"), "g")
    thickness = None
    dims = get("Body", "Dimensions") or ""
    m = re.search(r"(\d+\.?\d*)\s*mm\s*$", dims)
    if m: thickness = float(m.group(1))

    sim_type = get("Body", "SIM") or None
    sim_type = sim_type[:50] if sim_type else None
    has_esim = "esim" in (sim_type or "").lower()

    tech = get("Network", "Technology") or ""
    has_5g = "5G" in tech if tech else None
    has_nfc = parse_bool(get("Comms", "NFC"))
    has_3_5 = parse_bool(get("Sound", "3.5mm jack"))

    speaker = get("Sound", "Loudspeaker") or ""
    has_stereo = "stereo" in speaker.lower() if speaker else None

    card = get("Memory", "Card slot") or ""
    has_card = "no" not in card.lower()[:5] if card else None

    os_text = get("Platform", "OS") or ""
    os_short = os_text.split(",")[0].strip()[:80] if os_text else None

    price_text = get("Misc", "Price") or ""
    price = None
    m = re.search(r"₹\s*([\d,]+)", price_text)
    if m: price = int(m.group(1).replace(",", ""))
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*EUR", price_text, re.I)
        if m: price = int(float(m.group(1)) * 90)

    return {
        "brand": brand, "model": model,
        "release_year": year, "announced_date": announced[:50] if announced else None,
        "price_inr": price,
        "ram_gb": ram, "storage_gb": storage, "has_memory_card": has_card,
        "display_size_inch": size, "display_type": dtype[:100] if dtype else None,
        "screen_resolution": resolution, "refresh_rate_hz": refresh,
        "main_camera_mp": main_mp, "selfie_camera_mp": selfie_mp,
        "camera_count": cam_count, "video_resolution": video_res,
        "chipset": chipset, "chipset_brand": chip_brand,
        "cpu_cores": cpu_cores, "gpu": gpu, "os": os_short,
        "battery_mah": battery, "charging_watt": charging,
        "has_wireless_charging": has_wireless,
        "weight_g": weight, "thickness_mm": thickness,
        "sim_type": sim_type, "has_esim": has_esim,
        "has_5g": has_5g, "has_nfc": has_nfc, "has_3_5mm": has_3_5,
        "has_stereo_speakers": has_stereo,
        "full_specs": json.dumps(specs, ensure_ascii=False),
        "reference_url": data.get("reference_url"),
        "original_image_url": data.get("image_url"),
    }


# ═══════════════════════════════════════════════════════════
# DXOMARK & NANOREVIEW (Same as test)
# ═══════════════════════════════════════════════════════════

def scrape_dxo(phone_name):
    query = phone_name.replace(" ", "+")
    html = fetch(f"{DXO_SEARCH}{query}")
    if not html: return None
    soup = BeautifulSoup(html, "lxml")
    result = soup.select_one("article a[href*='dxomark.com']") or soup.select_one(".search-result a") or soup.select_one("h2 a")
    if not result: return None
    article_url = result.get("href", "")
    if not article_url.startswith("http"):
        article_url = "https://www.dxomark.com" + article_url
    delay(DELAY_DXO)
    a_html = fetch(article_url)
    if not a_html: return None
    a_soup = BeautifulSoup(a_html, "lxml")
    scores = {"camera_score_url": article_url}
    overall = a_soup.select_one(".score-overall, .dxo-score, .score-value")
    if overall:
        m = re.search(r"(\d+)", overall.text)
        if m: scores["camera_score_overall"] = int(m.group(1))
    for el in a_soup.select(".score-sub, .sub-score"):
        label = el.select_one(".label, .score-label")
        value = el.select_one(".value, .score-value")
        if label and value:
            key = label.text.strip().lower()
            m = re.search(r"(\d+)", value.text)
            if not m: continue
            score = int(m.group(1))
            if "photo" in key: scores["camera_score_photo"] = score
            elif "video" in key: scores["camera_score_video"] = score
            elif "zoom" in key: scores["camera_score_zoom"] = score
            elif "selfie" in key: scores["camera_score_selfie"] = score
    return scores if scores.get("camera_score_overall") else None


def scrape_nano(brand, model):
    slug = make_slug(brand, model)
    url = f"{NANO_BASE}{slug}"
    html = fetch(url)
    if not html: return None
    soup = BeautifulSoup(html, "lxml")
    scores = {"benchmark_url": url, "benchmark_slug": slug}
    antutu = soup.select_one("[class*='antutu'] .value, .antutu-score")
    if antutu:
        m = re.search(r"([\d,]+)", antutu.text)
        if m: scores["benchmark_antutu"] = int(m.group(1).replace(",", ""))
    if not scores.get("benchmark_antutu"):
        m = re.search(r"AnTuTu[\s:]*([\d,]+)", soup.get_text())
        if m: scores["benchmark_antutu"] = int(m.group(1).replace(",", ""))
    gb_single = soup.select_one("[class*='geekbench-single'] .value")
    gb_multi = soup.select_one("[class*='geekbench-multi'] .value")
    if gb_single:
        m = re.search(r"(\d+)", gb_single.text)
        if m: scores["benchmark_geekbench_single"] = int(m.group(1))
    if gb_multi:
        m = re.search(r"(\d+)", gb_multi.text)
        if m: scores["benchmark_geekbench_multi"] = int(m.group(1))
    return scores if any(k in scores for k in ["benchmark_antutu", "benchmark_geekbench_single"]) else None


# ═══════════════════════════════════════════════════════════
# CLOUDINARY (Same as test)
# ═══════════════════════════════════════════════════════════

def strip_text_marks(img):
    """Drop small detached alpha components (watermark text/logo) while keeping the subject."""
    try:
        arr = np.array(img)
        alpha = arr[..., 3]
        labels, n = ndimage.label(alpha > 10)
        if n <= 1:
            return img
        sizes = ndimage.sum(np.ones_like(labels), labels, index=range(1, n + 1))
        biggest = sizes.max()
        h_img = alpha.shape[0]
        keep = np.zeros_like(alpha)
        for i, sl in enumerate(ndimage.find_objects(labels), start=1):
            comp_h = sl[0].stop - sl[0].start
            if sizes[i - 1] < 0.02 * biggest and comp_h < 0.06 * h_img:
                continue
            keep[labels == i] = 255
        if keep.any():
            arr[..., 3] = np.minimum(alpha, keep * 255)
            return Image.fromarray(arr)
    except Exception as e:
        log.warning(f"  Text-mark strip failed: {e}")
    return img


def remove_bg(image_bytes):
    try:
        output = remove(image_bytes)
        img = Image.open(BytesIO(output))
        if img.mode != "RGBA": img = img.convert("RGBA")
        img = strip_text_marks(img)
        bbox = img.getbbox()
        if bbox: img = img.crop(bbox)
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        log.warning(f"  BG remove failed: {e}")
        return None


def upload_image(image_url, unique_id):
    if not image_url: return None, None
    try:
        r = requests.get(
            image_url,
            headers={"User-Agent": random.choice(USER_AGENTS)},
            proxies=get_proxy(),
            verify=False,
            timeout=120
        )
        r.raise_for_status()
        original = r.content
        transparent = remove_bg(original) or original
        result = cloudinary.uploader.upload(
            BytesIO(transparent),
            folder="phones",
            public_id=unique_id,
            overwrite=True,
            resource_type="image",
            format="png",
            transformation=[
                {"width": 800, "height": 800, "crop": "pad", "background": "transparent"},
                {"quality": "auto:good"},
            ]
        )
        return result["secure_url"], result["public_id"]
    except Exception as e:
        log.warning(f"  Image upload failed: {e}")
        return None, None


# ═══════════════════════════════════════════════════════════
# DB
# ═══════════════════════════════════════════════════════════

def is_phone_done(conn, unique_id):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM phones WHERE unique_id = %s", (unique_id,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists


def get_brand_progress(conn, brand):
    cur = conn.cursor()
    cur.execute("SELECT MAX(phone_index) FROM scraper_progress WHERE brand = %s AND status = 'done'", (brand,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row and row[0] else 0


def save_progress(conn, brand, index, phone_name, phone_url, unique_id, status="done", error=None):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO scraper_progress
            (brand, phone_index, phone_name, phone_url, unique_id, status, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (brand, phone_index) DO UPDATE SET
            status = EXCLUDED.status,
            error_message = EXCLUDED.error_message,
            unique_id = EXCLUDED.unique_id,
            scraped_at = NOW()
    """, (brand, index, phone_name, phone_url, unique_id, status, error))
    conn.commit()
    cur.close()


def save_phone(conn, cols, dxo, nano, img_url, img_pid):
    unique_id = make_unique_id(cols["brand"], cols["model"], cols["release_year"])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO phones (
            unique_id, brand, model, release_year, announced_date,
            price_inr, ram_gb, storage_gb, has_memory_card,
            display_size_inch, display_type, screen_resolution, refresh_rate_hz,
            main_camera_mp, selfie_camera_mp, camera_count, video_resolution,
            chipset, chipset_brand, cpu_cores, gpu, os,
            battery_mah, charging_watt, has_wireless_charging,
            weight_g, thickness_mm, sim_type, has_esim,
            has_5g, has_nfc, has_3_5mm, has_stereo_speakers,
            image_url, image_public_id, original_image_url,
            camera_score_overall, camera_score_photo, camera_score_video,
            camera_score_zoom, camera_score_selfie, camera_score_url,
            benchmark_antutu, benchmark_geekbench_single, benchmark_geekbench_multi,
            benchmark_url, benchmark_slug,
            full_specs, reference_url, price_updated_at
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT (unique_id) DO UPDATE SET
            price_inr = EXCLUDED.price_inr,
            image_url = COALESCE(EXCLUDED.image_url, phones.image_url),
            image_public_id = COALESCE(EXCLUDED.image_public_id, phones.image_public_id),
            camera_score_overall = COALESCE(EXCLUDED.camera_score_overall, phones.camera_score_overall),
            camera_score_photo = COALESCE(EXCLUDED.camera_score_photo, phones.camera_score_photo),
            camera_score_video = COALESCE(EXCLUDED.camera_score_video, phones.camera_score_video),
            camera_score_zoom = COALESCE(EXCLUDED.camera_score_zoom, phones.camera_score_zoom),
            camera_score_selfie = COALESCE(EXCLUDED.camera_score_selfie, phones.camera_score_selfie),
            benchmark_antutu = COALESCE(EXCLUDED.benchmark_antutu, phones.benchmark_antutu),
            benchmark_geekbench_single = COALESCE(EXCLUDED.benchmark_geekbench_single, phones.benchmark_geekbench_single),
            benchmark_geekbench_multi = COALESCE(EXCLUDED.benchmark_geekbench_multi, phones.benchmark_geekbench_multi),
            full_specs = EXCLUDED.full_specs,
            updated_at = NOW()
    """, (
        unique_id,
        cols["brand"], cols["model"], cols["release_year"], cols["announced_date"],
        cols["price_inr"], cols["ram_gb"], cols["storage_gb"], cols["has_memory_card"],
        cols["display_size_inch"], cols["display_type"], cols["screen_resolution"], cols["refresh_rate_hz"],
        cols["main_camera_mp"], cols["selfie_camera_mp"], cols["camera_count"], cols["video_resolution"],
        cols["chipset"], cols["chipset_brand"], cols["cpu_cores"], cols["gpu"], cols["os"],
        cols["battery_mah"], cols["charging_watt"], cols["has_wireless_charging"],
        cols["weight_g"], cols["thickness_mm"], cols["sim_type"], cols["has_esim"],
        cols["has_5g"], cols["has_nfc"], cols["has_3_5mm"], cols["has_stereo_speakers"],
        img_url, img_pid, cols["original_image_url"],
        dxo.get("camera_score_overall") if dxo else None,
        dxo.get("camera_score_photo") if dxo else None,
        dxo.get("camera_score_video") if dxo else None,
        dxo.get("camera_score_zoom") if dxo else None,
        dxo.get("camera_score_selfie") if dxo else None,
        dxo.get("camera_score_url") if dxo else None,
        nano.get("benchmark_antutu") if nano else None,
        nano.get("benchmark_geekbench_single") if nano else None,
        nano.get("benchmark_geekbench_multi") if nano else None,
        nano.get("benchmark_url") if nano else None,
        nano.get("benchmark_slug") if nano else None,
        cols["full_specs"], cols["reference_url"],
        datetime.now()
    ))
    conn.commit()
    cur.close()
    return unique_id


# ═══════════════════════════════════════════════════════════
# PROCESS PHONE
# ═══════════════════════════════════════════════════════════

def process_phone(conn, brand, phone_name, gsm_url):
    log.info(f"  📱 {phone_name}")

    gsm = scrape_gsm(gsm_url)
    if not gsm:
        log.warning(f"    ❌ Scrape failed")
        return None, "failed"
    delay(DELAY_GSM)

    cols = extract_columns(gsm, brand)
    unique_id = make_unique_id(brand, cols["model"], cols["release_year"])

    # Skip if already in DB
    if is_phone_done(conn, unique_id):
        log.info(f"    ⏭️  Already in DB")
        return unique_id, "skipped"

    # DXOMARK
    dxo = None
    try:
        dxo = scrape_dxo(gsm.get("name", phone_name))
        log.info(f"    📸 Camera: {dxo.get('camera_score_overall') if dxo else 'N/A'}")
    except Exception as e:
        log.warning(f"    DXOMARK error: {e}")
    delay(DELAY_DXO)

    # NanoReview
    nano = None
    try:
        nano = scrape_nano(brand, cols["model"])
        log.info(f"    ⚡ AnTuTu: {nano.get('benchmark_antutu', 'N/A') if nano else 'N/A'}")
    except Exception as e:
        log.warning(f"    NanoReview error: {e}")
    delay(DELAY_NANO)

    # Image
    img_url, img_pid = upload_image(gsm.get("image_url"), unique_id)
    log.info(f"    🖼️  Image: {'✅' if img_url else '❌'}")

    # Save
    save_phone(conn, cols, dxo, nano, img_url, img_pid)
    log.info(f"    ✅ Saved: {unique_id}")
    return unique_id, "done"


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    log.info("=" * 70)
    log.info(f"🚀 FULL SCRAPER STARTED: {datetime.now()}")
    log.info("=" * 70)

    api_key = os.getenv("SCRAPEOPS_API_KEY")
    log.info(f"Proxy: {'✅ ScrapeOps' if api_key else '❌ Direct'}")
    log.info("=" * 70)

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    total_saved = 0
    total_skipped = 0
    total_errors = 0

    try:
        for brand, brand_url in BRANDS.items():
            log.info(f"\n{'='*70}")
            log.info(f"🏷️  {brand}")
            log.info(f"{'='*70}")

            last_index = get_brand_progress(conn, brand)
            if last_index > 0:
                log.info(f"  🔄 Resuming from #{last_index + 1}")

            try:
                phones = get_brand_phones(brand_url)
                log.info(f"  📊 Found {len(phones)} phones")
            except Exception as e:
                log.error(f"  ❌ Brand fetch failed: {e}")
                continue

            for i, p in enumerate(phones, 1):
                if i <= last_index:
                    total_skipped += 1
                    continue

                try:
                    log.info(f"\n  [{i}/{len(phones)}]")
                    uid, status = process_phone(conn, brand, p["name"], p["url"])

                    if status == "done":
                        total_saved += 1
                        save_progress(conn, brand, i, p["name"], p["url"], uid, "done")
                    elif status == "skipped":
                        total_skipped += 1
                        save_progress(conn, brand, i, p["name"], p["url"], uid, "done")
                    else:
                        save_progress(conn, brand, i, p["name"], p["url"], None, "failed")

                    if i % 10 == 0:
                        log.info(f"  ☕ Break 30s (saved: {total_saved}, skipped: {total_skipped})")
                        time.sleep(30)
                    if i % 100 == 0:
                        log.info(f"  🛌 Break 5 min")
                        time.sleep(300)

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    total_errors += 1
                    log.error(f"    ❌ {e}")
                    save_progress(conn, brand, i, p["name"], p["url"], None, "failed", str(e)[:500])
                    with open("errors.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.now()} | {brand} | {p['name']} | {e}\n")
                    continue

    except KeyboardInterrupt:
        log.warning("\n⚠️  Stopped by user. Progress saved.")
    finally:
        conn.close()

    log.info("\n" + "=" * 70)
    log.info(f"🎉 DONE")
    log.info(f"   Saved:    {total_saved}")
    log.info(f"   Skipped:  {total_skipped}")
    log.info(f"   Errors:   {total_errors}")
    log.info(f"   Time:     {datetime.now()}")
    log.info("=" * 70)
    log.info("\n💾 Backup lo:")
    log.info("   pg_dump DATABASE_URL -Fc -f backup.dump")


if __name__ == "__main__":
    main()