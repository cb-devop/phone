"""
DEMO — Latest iPhone + Samsung (6 phones) — 100+ columns schema
Image source: GSMArena clean "bigpic" render (official, NO watermark)
save_phone() is dynamic — add a key in extract_columns + a column in
schema.sql and it just works.
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
from bs4 import BeautifulSoup
from PIL import Image
import psycopg2
from psycopg2 import sql
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)
log = logging.getLogger(__name__)

GSM_BASE = "https://www.gsmarena.com/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

BRAND_URLS = {
    "Apple":   "https://www.gsmarena.com/apple-phones-48.php",
    "Samsung": "https://www.gsmarena.com/samsung-phones-9.php",
}

MAX_PER_BRAND = 3

# Columns owned by save_phone(), not by extract_columns()
EXTRA_SAVE_COLS = ("image_url", "image_public_id", "price_updated_at")
PROTECTED_CONFLICT_COLS = ("unique_id", "brand", "model", "price_updated_at")

# ═══════════════════════════════════════════════════════════
# FETCH
# ═══════════════════════════════════════════════════════════

def fetch(url, retries=3):
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            r = requests.get(url, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.text
            log.warning(f"    HTTP {r.status_code}, retry...")
            time.sleep(5)
        except Exception as e:
            log.warning(f"    Error: {e}")
            time.sleep(5)
    return None

# ═══════════════════════════════════════════════════════════
# HELPERS
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

def norm(text):
    """GSMArena spec text mein invisible unicode spaces hote hain — normalize karo"""
    if not text: return ""
    return re.sub(r"[\u00a0\u2000-\u200a\u202f\u205f\u3000\ufeff]", " ", str(text)).replace("\u2011", "-")

def safe_str(text, max_len=500):
    if not text: return None
    s = str(text).strip()
    return s[:max_len] if len(s) > max_len else s

def make_unique_id(brand, model, year):
    s = f"{brand}-{model}-{year or 'unknown'}".lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:200]

# ═══════════════════════════════════════════════════════════
# GET PHONE LIST
# ═══════════════════════════════════════════════════════════

def get_latest_phones(brand_url, limit):
    log.info(f"  📄 Fetching brand page...")
    html = fetch(brand_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    phones = []

    for item in soup.select(".makers ul li a"):
        href = item.get("href")
        name_tag = item.select_one("strong span")
        if not (href and name_tag):
            continue

        name = name_tag.text.strip()
        name_lower = name.lower()

        if any(kw in name_lower for kw in ["tablet", "watch", "pad", "band"]):
            continue
        if "_tablets-" in href or "_watches-" in href:
            continue

        full_url = GSM_BASE + href if not href.startswith("http") else href
        phones.append({"name": name, "url": full_url})

        if len(phones) >= limit:
            break

    return phones

# ═══════════════════════════════════════════════════════════
# SCRAPE PHONE
# ═══════════════════════════════════════════════════════════

def scrape_gsm(url):
    html = fetch(url)
    if not html: return None
    soup = BeautifulSoup(html, "lxml")
    data = {"reference_url": url}

    title = soup.select_one(".specs-phone-name-title")
    if not title: return None
    data["name"] = title.text.strip()
    log.info(f"    📱 {data['name']}")

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
            if src.startswith("//"):
                src = "https:" + src
            elif not src.startswith("http"):
                src = GSM_BASE + src.lstrip("/")
            data["image_url"] = src
            log.info(f"    🖼️  Image: {src[:90]}")

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
                k, v = ttl.text.strip(), norm(nfo.text)
                if k and v: specs[cat][k] = v

    data["specs"] = specs
    return data

# ═══════════════════════════════════════════════════════════
# EXTRACT — full specs → 100+ flat columns
# ═══════════════════════════════════════════════════════════

def extract_columns(data, brand):
    specs = data.get("specs", {})

    def get(cat, key):
        if cat not in specs: return None
        for k, v in specs[cat].items():
            if key.lower() in k.lower(): return v
        return None

    name = data.get("name", "")
    model = name.replace(brand, "").strip() or "Unknown"

    # ═══════════════ LAUNCH ═══════════════
    announced = get("Launch", "Announced") or ""
    status = get("Launch", "Status") or ""
    m = re.search(r"(20\d{2})", announced)
    year = int(m.group(1)) if m else None
    if not year:
        m = re.search(r"(20\d{2})", status)
        year = int(m.group(1)) if m else None

    # ═══════════════ NETWORK ═══════════════
    tech = get("Network", "Technology") or ""
    has_2g = "GSM" in tech or "CDMA" in tech
    has_3g = "HSPA" in tech or "EVDO" in tech
    has_4g = "LTE" in tech
    has_5g = "5G" in tech if tech else None

    # ═══════════════ SIM ═══════════════
    sim_text = get("Body", "SIM") or ""
    sl_sim = sim_text.lower()
    has_dual_sim = bool(re.search(r"\d+\s*sims?\b|\bdual\b|nano-sim.*,.*nano-sim|nano-sim \+ nano-sim", sl_sim))
    sim_count = 2 if has_dual_sim else (1 if sim_text else None)
    has_esim = "esim" in sl_sim or "e-sim" in sl_sim if sim_text else None

    # ═══════════════ BODY ═══════════════
    dims = get("Body", "Dimensions") or ""
    height_mm = width_mm = thickness_mm = None
    m = re.search(r"([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)\s*mm", dims)
    if m:
        height_mm, width_mm, thickness_mm = float(m.group(1)), float(m.group(2)), float(m.group(3))

    weight = parse_int(get("Body", "Weight"), "g")
    build = get("Body", "Build") or ""

    def build_part(word):
        for part in re.split(r"[;,]", build):
            if word in part.lower():
                return part.strip()
        return None
    build_front = build_part("front")
    build_back = build_part("back")
    build_frame = build_part("frame")

    ip_text = get("Body", "IP") or get("Body", "Water") or get("Body", "Dust") or ""
    ip_rating = None
    m = re.search(r"IP\d{2}", ip_text, re.I)
    if m: ip_rating = m.group(0).upper()
    has_ip = bool(ip_rating)

    # ═══════════════ DISPLAY ═══════════════
    dtype = get("Display", "Type") or ""
    dsize = parse_float(get("Display", "Size"), r'(inch|inches|")')
    dres = get("Display", "Resolution") or ""
    protection = get("Display", "Protection") or ""

    display_w = display_h = None
    m = re.search(r"(\d{3,5})\s*x\s*(\d{3,5})", dres)
    if m:
        display_w, display_h = int(m.group(1)), int(m.group(2))

    ppi = None
    m = re.search(r"~?\s*(\d+)\s*ppi", dres, re.I) or re.search(r"~?\s*(\d+)\s*ppi", dtype, re.I)
    if m: ppi = int(m.group(1))

    res_type = None
    if ppi:
        if ppi >= 1400: res_type = "4K+"
        elif ppi >= 1000: res_type = "QHD+"
        elif ppi >= 350: res_type = "FHD+"
        elif ppi >= 250: res_type = "HD+"
        else: res_type = "HD"

    refresh = None
    m = re.search(r"(\d{2,3})\s*Hz", dtype, re.I)
    if m: refresh = int(m.group(1))

    dt_lower = dtype.lower()
    hdr_type = "Dolby Vision" if "dolby vision" in dt_lower else (
        "HDR10+" if "hdr10+" in dt_lower else (
        "HDR10" if "hdr10" in dt_lower else (
        "HDR" if "hdr" in dt_lower else None)))

    # ═══════════════ PLATFORM ═══════════════
    os_text = get("Platform", "OS") or ""
    ol = os_text.lower()
    os_family = "iOS" if "ios" in ol else ("Android" if "android" in ol else None)
    os_version = None

    cpu_text = get("Platform", "CPU") or ""
    cpu_cores = None
    m = re.search(r"(\d+)\s*[- ]?\s*core", cpu_text, re.I)
    if m:
        cpu_cores = int(m.group(1))
    else:
        core_names = re.findall(r"\b(?:octa|hexa|deca|quad|dual)-?core\b", cpu_text, re.I)
        core_map = {"octa": 8, "hexa": 6, "deca": 10, "quad": 4, "dual": 2}
        if core_names:
            cpu_cores = core_map[re.match(r"(\w+)", core_names[0], re.I).group(1).lower()[:4]]
    cpu_speed = parse_float(cpu_text, "GHz")

    gpu = get("Platform", "GPU") or ""

    chipset_text = get("Platform", "Chipset") or ""
    chipset = chipset_text.split("\n")[0].strip() if chipset_text else None
    chipset_nm = parse_int(chipset_text, r"nm")
    cl = chipset_text.lower()
    chip_brand = chip_model = None
    if "snapdragon" in cl:
        chip_brand = "Snapdragon"
        m = re.search(r"snapdragon\s+([\w\s]+?)(?:\s*\(|$|\n)", chipset_text, re.I)
        if m: chip_model = m.group(1).strip()
    elif "dimensity" in cl:
        chip_brand = "MediaTek"
        m = re.search(r"dimensity\s+([\d]+\w*)", chipset_text, re.I)
        if m: chip_model = f"Dimensity {m.group(1)}"
    elif "helio" in cl:
        chip_brand = "MediaTek"
        m = re.search(r"helio\s+(\w+)", chipset_text, re.I)
        if m: chip_model = f"Helio {m.group(1)}"
    elif "exynos" in cl:
        chip_brand = "Exynos"
        m = re.search(r"exynos\s+([\d]+\w*)", chipset_text, re.I)
        if m: chip_model = f"Exynos {m.group(1)}"
    elif re.search(r"\b(a\d+)\s*(pro|max)?", cl):
        chip_brand = "Apple"
        m = re.search(r"\b(a\d+)\b\s*(pro|max)?", chipset_text, re.I)
        if m: chip_model = (m.group(1) + (" " + m.group(2) if m.group(2) else "")).title()
    elif "kirin" in cl:
        chip_brand = "Kirin"
        m = re.search(r"kirin\s+(\d+\w*)", chipset_text, re.I)
        if m: chip_model = f"Kirin {m.group(1)}"
    elif "tensor" in cl:
        chip_brand = "Google Tensor"
        m = re.search(r"tensor\s+(\w+)", chipset_text, re.I)
        if m: chip_model = f"Tensor {m.group(1)}"
    elif "unisoc" in cl:
        chip_brand = "Unisoc"
        m = re.search(r"unisoc\s+([\w\s]+?)(?:\s*\(|$|\n)", chipset_text, re.I)
        if m: chip_model = m.group(1).strip()
    elif "mediatek" in cl:
        chip_brand = "MediaTek"

    # ═══════════════ MEMORY ═══════════════
    internal = get("Memory", "Internal") or ""
    ram = parse_int(internal, r"GB\s*RAM")
    if not ram:
        m = re.search(r"(\d+)\s*GB\s*RAM", get("Memory", "Built") or "", re.I)
        ram = int(m.group(1)) if m else None
    storages = [int(x) for x in re.findall(r"(\d{1,4})\s*GB", internal, re.I) if int(x) >= 16]
    if ram and ram in storages:
        storages.remove(ram)
    storage = min(storages) if storages else None

    mem_blob = internal + " " + (get("Memory", "Built") or "")
    m = re.search(r"LPDDR\d+\w*", mem_blob, re.I)
    ram_type = m.group(0).upper() if m else None
    m = re.search(r"UFS\s*\d+(?:\.\d+)?(?:\s*[EX]\b)?", mem_blob, re.I)
    storage_type = m.group(0).upper().replace(" ", " ") if m else None

    card = get("Memory", "Card slot") or ""
    has_card = parse_bool(card) if card else None
    card_lower = card.lower()
    memory_card_type = "microSDXC" if "microsd" in card_lower or has_card else None
    max_card_gb = None
    m = re.search(r"(\d+)\s*TB", card, re.I)
    if m:
        max_card_gb = int(m.group(1)) * 1000
    else:
        m = re.search(r"(?:up to|max\.?)\s*(\d{2,4})\s*GB", card, re.I)
        if m: max_card_gb = int(m.group(1))

    # ═══════════════ MAIN CAMERA ═══════════════
    cam_text = ""
    cam_count = 0
    for key, cnt in [("Quad", 4), ("Triple", 3), ("Dual", 2), ("Single", 1)]:
        v = get("Main Camera", key)
        if v:
            cam_text = v
            cam_count = cnt
            break
    if not cam_text:
        cam_text = get("Main Camera", "Camera") or ""
        cam_count = cam_text.count("MP") or (1 if cam_text else 0)

    main_mp = parse_int(cam_text, "MP")
    main_aperture = parse_float(re.search(r"f/(\d+\.?\d*)", cam_text).group(0)[2:], None) if re.search(r"f/(\d+\.?\d*)", cam_text) else None

    cam_upper = cam_text.upper()
    cam_lower = cam_text.lower()
    has_ois = "OIS" in cam_upper
    has_eis = "EIS" in cam_upper or "gyro-eis" in cam_lower or "electronic stabilization" in cam_lower
    has_ultrawide = "ultrawide" in cam_lower or "ultra wide" in cam_lower or "120°" in cam_text
    has_telephoto = "telephoto" in cam_lower or "telephoto" in (get("Main Camera", "Features") or "").lower()
    has_periscope = "periscope" in cam_lower
    has_macro = "macro" in cam_lower
    has_tof = "TOF" in cam_upper or "LiDAR" in cam_text
    has_pdaf = "PDAF" in cam_upper or "phase detection" in cam_lower
    has_laser_af = "laser" in cam_lower
    has_depth = re.search(r"\d+\s*MP[^.\n]*depth", cam_text, re.I) is not None or "depth" in cam_lower

    uw_mp = parse_int(re.search(r"(\d+)\s*MP[^.\n]*ultra\s?wide", cam_text, re.I).group(0), "MP") if re.search(r"(\d+)\s*MP[^.\n]*ultra\s?wide", cam_text, re.I) else None
    tele_mp = parse_int(re.search(r"(\d+)\s*MP[^.\n]*telephoto", cam_text, re.I).group(0), "MP") if re.search(r"(\d+)\s*MP[^.\n]*telephoto", cam_text, re.I) else None
    macro_mp = parse_int(re.search(r"(\d+)\s*MP[^.\n]*macro", cam_text, re.I).group(0), "MP") if re.search(r"(\d+)\s*MP[^.\n]*macro", cam_text, re.I) else None
    if not has_macro and macro_mp: has_macro = True

    optical_zoom = parse_int(re.search(r"(\d+\.?\d*)x\s*optical", cam_text, re.I).group(0), None) if re.search(r"(\d+\.?\d*)x\s*optical", cam_text, re.I) else None
    if optical_zoom is None:
        m = re.search(r"optical\s*zoom\s*(\d+\.?\d*)x?", cam_text, re.I)
        if m: optical_zoom = int(float(m.group(1)))
    digital_zoom = None
    m = re.search(r"(\d+)x\s*digital", cam_text, re.I)
    if m: digital_zoom = int(m.group(1))

    feats_text = get("Main Camera", "Features") or ""
    has_flash = "flash" in feats_text.lower() or "LED" in feats_text.upper()
    flash_type = "Dual-LED" if "dual-led" in feats_text.lower() or "dual led" in feats_text.lower() else ("LED" if "led" in feats_text.lower() else None)

    video_text = get("Main Camera", "Video") or ""
    vu = video_text.upper()
    max_video_res = "8K" if "8K" in vu else ("4K" if "4K" in vu else ("1440p" if "1440P" in vu else ("1080p" if "1080P" in vu else None)))
    fps_values = sorted({int(x) for x in re.findall(r"(\d+)\s*(?:fps|f/s)", video_text)})
    max_fps = fps_values[-1] if fps_values else None

    # ═══════════════ SELFIE ═══════════════
    selfie_text = ""
    selfie_count = 0
    for key, cnt in [("Dual", 2), ("Triple", 3), ("Quad", 4), ("Single", 1)]:
        v = get("Selfie camera", key)
        if v:
            selfie_text = v
            selfie_count = cnt
            break
    if not selfie_text:
        selfie_text = get("Selfie camera", "Camera") or ""
        selfie_count = selfie_text.count("MP") or (1 if selfie_text else 0)

    selfie_mp = parse_int(selfie_text, "MP")
    m = re.search(r"f/(\d+\.?\d*)", selfie_text)
    selfie_aperture = float(m.group(1)) if m else None

    selfie_video = get("Selfie camera", "Video") or ""
    svu = selfie_video.upper()
    selfie_max_res = "4K" if "4K" in svu else ("1080p" if "1080P" in svu else None)
    selfie_fps_values = sorted({int(x) for x in re.findall(r"(\d+)\s*(?:fps|f/s)", selfie_video)})
    selfie_fps = selfie_fps_values[-1] if selfie_fps_values else None

    # ═══════════════ SOUND ═══════════════
    loudspeaker = get("Sound", "Loudspeaker") or ""
    has_loudspeaker = parse_bool(loudspeaker)
    has_stereo = "stereo" in loudspeaker.lower()
    jack_text = get("Sound", "3.5mm") or ""
    has_3_5mm = parse_bool(jack_text)
    audio_text = get("Sound", "Features") or loudspeaker
    has_hires = "hi-res" in audio_text.lower()

    # ═══════════════ CONNECTIVITY ═══════════════
    wlan = get("Comms", "WLAN") or ""
    wl = wlan.lower()
    has_wifi = bool(wlan)
    wifi_version = None
    m = re.search(r"wi-\u0066i\s*(\d{1,2}[a-e]?)\b", wl)
    if m:
        wifi_version = "Wi-Fi " + m.group(1).upper()
    elif "802.11be" in wl: wifi_version = "Wi-Fi 7"
    elif "802.11ax" in wl: wifi_version = "Wi-Fi 6"
    elif "802.11ac" in wl: wifi_version = "Wi-Fi 5"
    elif "802.11n" in wl: wifi_version = "Wi-Fi 4"
    elif "wi-fi" in wl:
        wifi_version = "Wi-Fi"
    wifi_bands = "tri-band" if "tri-band" in wl else ("dual-band" if "dual-band" in wl else None)

    bt = get("Comms", "Bluetooth") or ""
    has_bluetooth = bool(bt)
    bt_version = parse_float(bt)

    gps = get("Comms", "Positioning") or ""
    has_gps = bool(gps)

    nfc_text = get("Comms", "NFC") or ""
    has_nfc = parse_bool(nfc_text)

    usb = get("Comms", "USB") or ""
    usb_type = safe_str(usb, 100)
    has_usb_otg = "otg" in usb.lower()

    has_fm = "fm" in (get("Comms", "Radio") or "").lower() or "radio" in (get("Comms", "Radio") or "").lower()
    has_infrared = parse_bool(get("Comms", "Infrared")) if get("Comms", "Infrared") else None

    # ═══════════════ SENSORS ═══════════════
    sensors = get("Features", "Sensors") or ""
    sl = sensors.lower()

    has_fingerprint = "fingerprint" in sl if sensors else None
    fp_type = "under display" if "under display" in sl else (
        "side-mounted" if "side" in sl else (
        "rear-mounted" if "rear" in sl else (
        "in-display" if "in-display" in sl else None)))
    fp_tech = "ultrasonic" if "ultrasonic" in sl else ("optical" if "optical" in sl else None)

    has_face_id = "face id" in sl
    has_face_unlock = "face" in sl
    has_accel = "accelero" in sl if sensors else None
    has_gyro = "gyro" in sl if sensors else None
    has_prox = "proximity" in sl if sensors else None
    has_compass = "compass" in sl if sensors else None
    has_baro = "baro" in sl if sensors else None
    has_hr = "heart rate" in sl if sensors else None
    has_spo2 = ("spo2" in sl or "blood oxygen" in sl) if sensors else None

    # ═══════════════ BATTERY ═══════════════
    batt_text = " ".join(filter(None, [get("Battery", "Type"), get("Battery", "Capacity")]))
    battery = None
    for blob in (batt_text, get("Battery", "Type") or "", get("Battery", "Capacity") or ""):
        for m in re.finditer(r"([\d,]{3,6})\s*mAh", blob, re.I):
            try:
                battery = int(m.group(1).replace(",", ""))
                break
            except: pass
        if battery: break

    batt_lower = batt_text.lower()
    batt_type = "Li-Po" if "li-po" in batt_lower else ("Li-Ion" if "li-ion" in batt_lower else None)
    batt_removable = ("removable" in batt_lower and "non-removable" not in batt_lower) if batt_text else None

    charging_text = get("Battery", "Charging") or ""
    charging_lower = charging_text.lower()
    charging_w = None
    for m in re.finditer(r"(\d{1,3}(?:\.\d+)?)\s*W", charging_text, re.I):
        ctx = charging_text[max(0, m.start() - 40):m.end()].lower()
        if "wireless" not in ctx:
            v = int(float(m.group(1)))
            charging_w = v if charging_w is None else max(charging_w, v)
    if charging_w is None:
        charging_w = parse_int(charging_text, "W")

    has_wireless = "wireless" in charging_lower if charging_text else None
    wireless_w = None
    m = re.search(r"(\d{1,3})\s*W\s*(?:\w+\s*)*wireless", charging_text, re.I)
    if m: wireless_w = int(m.group(1))
    has_reverse_wireless = "reverse wireless" in charging_lower
    has_reverse_wired = "reverse wired" in charging_text.lower()
    has_fast_charging = ("fast" in charging_lower or (charging_w is not None and charging_w >= 18)) if (charging_text or charging_w is not None) else None

    # ═══════════════ MISC ═══════════════
    colors = safe_str(get("Misc", "Colors"), 1000)
    models_list_text = get("Misc", "Models") or ""
    if not models_list_text:
        models_list_text = get("Misc", "Model") or ""
    ml = re.sub(r"^\s*_models?:?\s*", "", models_list_text, flags=re.I).strip()
    models_list = safe_str(ml, 1000)

    sar_head = safe_str(re.search(r"([\d.]+)\s*W/kg\s*\(head\)", get("Misc", "SAR (head)") or "") and re.search(r"([\d.]+)\s*W/kg\s*\(head\)", get("Misc", "SAR (head)") or "").group(1) or re.search(r"head[^\d]*([\d.]+)", get("Misc", "SAR") or "") and re.search(r"head[^\d]*([\d.]+)", get("Misc", "SAR") or "").group(1), 50)
    sar_body = safe_str(re.search(r"([\d.]+)\s*W/kg\s*\(body\)", get("Misc", "SAR (body)") or "") and re.search(r"([\d.]+)\s*W/kg\s*\(body\)", get("Misc", "SAR (body)") or "").group(1) or re.search(r"body[^\d]*([\d.]+)", get("Misc", "SAR") or "") and re.search(r"body[^\d]*([\d.]+)", get("Misc", "SAR") or "").group(1), 50)

    # ═══════════════ PRICE ═══════════════
    price_text = get("Misc", "Price") or ""
    price_inr = parse_int(re.search(r"₹\s*([\d,]+)", price_text).group(0), None) if re.search(r"₹\s*([\d,]+)", price_text) else None
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", price_text)
    price_usd = int(float(m.group(1).replace(",", ""))) if m else None
    m = re.search(r"€\s*([\d,]+(?:\.\d+)?)", price_text)
    price_eur = int(float(m.group(1).replace(",", ""))) if m else None

    # ═══════════════ CPU max speed (GHz) — from CPU text's leading token ═══════════════
    cpu_speed = max((float(x) for x in re.findall(r"(\d+\.?\d*)\s*GHz", cpu_text)), default=None) if cpu_text else cpu_speed

    # ═══════════════ RETURN ═══════════════
    return {
        "brand": brand, "model": safe_str(model, 200),
        "release_year": year,
        "announced_date": safe_str(announced, 100),
        "status": safe_str(status, 100),
        "price_inr": price_inr,
        "price_usd": price_usd,
        "price_eur": price_eur,
        "network_technology": safe_str(tech, 300),
        "has_2g": has_2g,
        "has_3g": has_3g,
        "has_4g": has_4g,
        "has_5g": has_5g,
        "network_speed": safe_str(get("Network", "Speed"), 300),
        "sim_type": safe_str(sim_text, 300),
        "sim_count": sim_count,
        "has_esim": has_esim,
        "has_dual_sim": has_dual_sim if sim_text else None,
        "dimensions": safe_str(dims, 300),
        "height_mm": height_mm,
        "width_mm": width_mm,
        "thickness_mm": thickness_mm,
        "weight_g": weight,
        "build_front": safe_str(build_front, 300),
        "build_back": safe_str(build_back, 300),
        "build_frame": safe_str(build_frame, 300),
        "has_ip_rating": has_ip,
        "ip_rating": ip_rating,
        "has_waterproof": ("splash" in (get("Body", "IP") or "").lower() or "water" in (get("Body", "IP") or "").lower() or "dust/water" in (get("Body", "IP") or "").lower() or "water/" in (get("Body", "IP") or "").lower()) if has_ip else None,
        "has_dustproof": has_ip,
        "display_type": safe_str(dtype, 400),
        "display_size_inch": dsize,
        "display_resolution": safe_str(dres, 150),
        "display_width_px": display_w,
        "display_height_px": display_h,
        "display_ppi": ppi,
        "refresh_rate_hz": refresh,
        "display_resolution_type": res_type,
        "has_amoled": "amoled" in dt_lower,
        "has_oled": "oled" in dt_lower,
        "has_lcd": "lcd" in dt_lower or "tft" in dt_lower,
        "has_ltpo": "ltpo" in dt_lower,
        "has_hdr": hdr_type is not None,
        "hdr_type": hdr_type,
        "screen_protection": safe_str(protection, 300),
        "has_always_on": "always-on" in dt_lower or "always on" in dt_lower,
        "has_punch_hole": "punch-hol" in dt_lower or "hole" in dt_lower,
        "has_notch": "notch" in dt_lower,
        "os": safe_str(os_text, 200),
        "os_version": parse_float(os_text, None),
        "os_family": os_family,
        "chipset": safe_str(chipset, 300),
        "chipset_brand": chip_brand,
        "chipset_model": safe_str(chip_model, 150),
        "chipset_nm": chipset_nm,
        "cpu": safe_str(cpu_text, 400),
        "cpu_cores": cpu_cores,
        "cpu_max_speed_ghz": cpu_speed,
        "cpu_architecture": None,
        "gpu": safe_str(gpu, 200),
        "ram_gb": ram,
        "ram_type": ram_type,
        "storage_gb": storage,
        "storage_type": storage_type,
        "has_memory_card": has_card,
        "memory_card_type": memory_card_type,
        "max_memory_card_gb": max_card_gb,
        "main_camera_count": cam_count or None,
        "main_camera_mp": main_mp,
        "main_camera_aperture": main_aperture,
        "main_camera_ois": has_ois,
        "main_camera_eis": has_eis,
        "has_ultrawide": has_ultrawide,
        "ultrawide_mp": uw_mp,
        "has_telephoto": has_telephoto,
        "telephoto_mp": tele_mp,
        "has_periscope": has_periscope,
        "has_macro": has_macro,
        "macro_mp": macro_mp,
        "has_depth_sensor": has_depth,
        "has_tof_sensor": has_tof,
        "optical_zoom_x": optical_zoom,
        "digital_zoom_x": digital_zoom,
        "has_laser_autofocus": has_laser_af,
        "has_pdaf": has_pdaf,
        "has_flash": has_flash if feats_text or cam_text else None,
        "flash_type": safe_str(flash_type, 50),
        "max_video_resolution": safe_str(max_video_res, 20),
        "max_video_fps": max_fps,
        "video_8k": "8K" in vu,
        "video_4k": "4K" in vu,
        "video_1080p": "1080" in vu,
        "video_hdr": "HDR" in vu,
        "video_ois": "OIS" in vu or has_ois,
        "has_prores": "ProRes" in video_text,
        "has_log_profile": "log" in vu,
        "selfie_camera_mp": selfie_mp,
        "selfie_camera_aperture": selfie_aperture,
        "selfie_camera_count": selfie_count or None,
        "selfie_has_autofocus": bool(re.search(r"\bAF\b|autofocus", selfie_text, re.I)),
        "selfie_has_hdr": "HDR" in (get("Selfie camera", "Features") or "").upper(),
        "selfie_max_video_resolution": safe_str(selfie_max_res, 20),
        "selfie_max_video_fps": selfie_fps,
        "has_under_display_camera": "under display" in selfie_text.lower(),
        "has_popup_camera": "pop-up" in selfie_text.lower() or "popup" in selfie_text.lower(),
        "has_loudspeaker": has_loudspeaker,
        "has_stereo_speakers": has_stereo,
        "has_3_5mm_jack": has_3_5mm,
        "has_hi_res_audio": has_hires,
        "audio_features": safe_str(audio_text, 300),
        "has_wifi": has_wifi if wlan else None,
        "wifi_version": safe_str(wifi_version, 30),
        "wifi_bands": safe_str(wifi_bands, 30),
        "has_bluetooth": has_bluetooth if bt else None,
        "bluetooth_version": bt_version,
        "has_gps": has_gps if gps else None,
        "gps_systems": safe_str(gps, 300),
        "has_nfc": has_nfc,
        "has_usb_otg": has_usb_otg if usb else None,
        "usb_type": usb_type,
        "has_fm_radio": has_fm,
        "has_infrared": has_infrared,
        "has_fingerprint": has_fingerprint,
        "fingerprint_type": safe_str(fp_type, 50),
        "fingerprint_technology": safe_str(fp_tech, 50),
        "has_face_unlock": has_face_unlock if sensors else None,
        "has_face_id": has_face_id if sensors else None,
        "has_accelerometer": has_accel,
        "has_gyro": has_gyro,
        "has_proximity": has_prox,
        "has_compass": has_compass,
        "has_barometer": has_baro,
        "has_heart_rate": has_hr,
        "has_spo2": has_spo2,
        "battery_mah": battery,
        "battery_type": safe_str(batt_type, 50),
        "battery_removable": batt_removable,
        "charging_watt": charging_w,
        "has_wireless_charging": has_wireless,
        "wireless_charging_watt": wireless_w,
        "has_reverse_wireless": has_reverse_wireless,
        "has_reverse_wired": has_reverse_wired,
        "has_fast_charging": has_fast_charging,
        "has_bypass_charging": "bypass" in charging_lower,
        "charging_features": safe_str(charging_text, 400),
        "colors": colors,
        "models_list": models_list,
        "sar_head": sar_head,
        "sar_body": sar_body,
        "full_specs": json.dumps(specs, ensure_ascii=False),
        "reference_url": data.get("reference_url"),
        "original_image_url": data.get("image_url"),
    }

# ═══════════════════════════════════════════════════════════
# IMAGE DOWNLOAD
# ═══════════════════════════════════════════════════════════

def download_image(url):
    if not url:
        return None
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.gsmarena.com/",
        }
        r = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        if r.status_code != 200:
            return None
        content_type = r.headers.get("Content-Type", "")
        if "image" not in content_type.lower():
            return None
        data = r.content
        if len(data) < 1000:
            return None
        try:
            img = Image.open(BytesIO(data))
            img.verify()
            img = Image.open(BytesIO(data))
            w, h = img.size
            log.info(f"    ✅ Image OK ({len(data)//1024} KB, {w}x{h})")
            return data
        except Exception:
            return None
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════
# UPLOAD (clean bigpic render — no watermark, no hacks)
# ═══════════════════════════════════════════════════════════

def upload_image(image_url, unique_id):
    if not image_url:
        return None, None

    data = download_image(image_url)
    if not data:
        return None, None

    try:
        result = cloudinary.uploader.upload(
            BytesIO(data),
            folder="phones",
            public_id=unique_id,
            overwrite=True,
            resource_type="image",
            transformation=[
                {"width": 1000, "height": 1000, "crop": "pad", "background": "white"},
                {"quality": "auto:best"},
            ]
        )
        return result["secure_url"], result["public_id"]
    except Exception as e:
        log.warning(f"    Cloudinary failed: {e}")
        return None, None

# ═══════════════════════════════════════════════════════════
# DB — dynamic insert (schema-driven, no hardcoded lists)
# ═══════════════════════════════════════════════════════════

def get_schema_columns(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'phones' AND table_schema = 'public'
          AND column_name <> ALL(%s)
        ORDER BY ordinal_position
    """, ([
        "id", "created_at", "updated_at",
        "dxomark_overall", "dxomark_photo", "dxomark_video", "dxomark_zoom",
        "dxomark_selfie", "dxomark_url",
        "antutu_score", "geekbench_single", "geekbench_multi", "gfxbench_score",
        "benchmark_url",
    ],))
    cols = [r[0] for r in cur.fetchall()]
    cur.close()
    return set(cols)

def save_phone(conn, cols, img_url, img_pid):
    """
    Dynamic INSERT:
      - cols = extract_columns() output (keys match schema column names)
      - img_url/img_pid/price_updated_at added here
      - Any key not in the schema is reported and skipped, never crashes
      - ON CONFLICT updates every non-protected column with COALESCE
        (so re-scrapes never NULL out existing data)
    """
    unique_id = make_unique_id(cols["brand"], cols["model"], cols["release_year"])

    schema_cols = get_schema_columns(conn)

    row = {"unique_id": unique_id}
    for k, v in cols.items():
        if k in ("brand", "model", "release_year"):
            row[k] = v
    for k, v in cols.items():
        if k in ("brand", "model", "release_year"):
            continue
        if k in schema_cols:
            row[k] = v
        else:
            log.warning(f"    ⚠️ Skipping unknown column: {k}")

    if img_url:
        row["image_url"] = img_url
        row["image_public_id"] = img_pid
    row["price_updated_at"] = datetime.now()

    keys = list(row.keys())
    values = [row[k] for k in keys]

    columns = sql.SQL(", ").join(map(sql.Identifier, keys))
    placeholders = sql.SQL(", ").join(sql.Placeholder() * len(keys))
    updates = sql.SQL(", ").join(
        sql.SQL("{0} = COALESCE(EXCLUDED.{0}, phones.{0})").format(sql.Identifier(k))
        for k in keys if k not in PROTECTED_CONFLICT_COLS
    )
    query = sql.SQL(
        "INSERT INTO phones ({}) VALUES ({}) "
        "ON CONFLICT (unique_id) DO UPDATE SET {}, updated_at = NOW()"
    ).format(columns, placeholders, updates)

    cur = conn.cursor()
    try:
        cur.execute(query, values)
        conn.commit()
        return unique_id
    except Exception as e:
        conn.rollback()
        log.error(f"    DB error: {e}")
        raise
    finally:
        cur.close()

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    log.info("=" * 60)
    log.info(f"🎯 DEMO — Latest iPhone + Samsung (100+ fields)")
    log.info(f"⏰ {datetime.now()}")
    log.info("=" * 60)

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))

    saved = 0
    errors = 0
    total = 0

    for brand, brand_url in BRAND_URLS.items():
        log.info(f"\n{'='*60}")
        log.info(f"🏷️  {brand}")
        log.info(f"{'='*60}")

        phones = get_latest_phones(brand_url, MAX_PER_BRAND)
        log.info(f"  📊 {len(phones)} phones mile\n")

        for p in phones:
            total += 1
            log.info(f"\n{'─'*60}")
            log.info(f"[{total}] {brand} — {p['name']}")
            log.info(f"    URL: {p['url']}")
            log.info(f"{'─'*60}")

            try:
                log.info(f"  [1/2] Scraping...")
                gsm = scrape_gsm(p["url"])
                if not gsm:
                    log.error(f"  ❌ Scrape failed")
                    errors += 1
                    continue

                cols = extract_columns(gsm, brand)
                unique_id = make_unique_id(brand, cols["model"], cols["release_year"])
                log.info(f"  ✅ Unique ID: {unique_id}")
                non_empty = sum(1 for v in cols.values() if v not in (None, False, 0))
                log.info(f"  📋 {cols['model']} | {cols['release_year']} | {non_empty}/{len(cols)} fields filled | "
                         f"{cols['ram_gb']}/{cols['storage_gb']}GB {cols['ram_type']}/{cols['storage_type']} | "
                         f"{cols['display_size_inch']}in {cols['refresh_rate_hz']}Hz {cols['display_resolution_type']} {cols['display_ppi']}ppi | "
                         f"{cols['main_camera_count']}x cam ({cols['main_camera_mp']}MP f/{cols['main_camera_aperture']} OIS:{cols['main_camera_ois']}) | "
                         f"Video {cols['max_video_resolution']}@{cols['max_video_fps']}fps | {cols['chipset']} {cols['chipset_nm']}nm {cols['cpu_cores']}core | {cols['gpu']} | {cols['os_version']} | "
                         f"{cols['battery_mah']}mAh {cols['charging_watt']}W (wireless:{cols['charging_watt'] and cols['has_wireless_charging']}) | "
                         f"{cols['weight_g']}g {cols['thickness_mm']}mm {cols['ip_rating']} | "
                         f"₹{cols['price_inr']} ${cols['price_usd']} | 2G:{cols['has_2g']} 3G:{cols['has_3g']} 4G:{cols['has_4g']} 5G:{cols['has_5g']} | "
                         f"WiFi {cols['wifi_version']} BT {cols['bluetooth_version']} NFC {cols['has_nfc']} FM {cols['has_fm_radio']} OTG {cols['has_usb_otg']} IR {cols['has_infrared']} | "
                         f"FP {cols['fingerprint_type']}/{cols['fingerprint_technology']} face {cols['has_face_id']} | "
                         f"3.5mm {cols['has_3_5mm_jack']} stereo {cols['has_stereo_speakers']} HiRes {cols['has_hi_res_audio']} | "
                         f"selfie {cols['selfie_camera_count']}x {cols['selfie_camera_mp']}MP")

                time.sleep(random.uniform(3, 5))

                log.info(f"  [2/2] Image...")
                img_url, img_pid = upload_image(gsm.get("image_url"), unique_id)
                log.info(f"  {'✅' if img_url else '❌'} Image")

                save_phone(conn, cols, img_url, img_pid)
                log.info(f"  💾 Saved to DB")
                saved += 1

                time.sleep(random.uniform(3, 5))

            except Exception as e:
                log.error(f"  ❌ Error: {e}")
                errors += 1

    conn.close()

    log.info("\n" + "=" * 60)
    log.info(f"🎉 DEMO DONE")
    log.info(f"   ✅ Saved:  {saved}")
    log.info(f"   ❌ Errors: {errors}")
    log.info(f"   📊 Total:  {total}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
