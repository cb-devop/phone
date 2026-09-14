import logging
logging.basicConfig(level=logging.WARNING)
import json, time, random
import test_scraper as t

for brand, url in list(t.BRAND_URLS.items()):
    for p in t.get_latest_phones(url, 2):
        gsm = t.scrape_gsm(p["url"])
        if not gsm:
            print("SCRRAPE FAIL", p["name"]); continue
        cols = t.extract_columns(gsm, brand)
        filled = {k: v for k, v in cols.items() if v not in (None, False, 0, "")}
        print(f"\n===== {brand} | {cols['model']} ({cols['release_year']}) — {len(filled)}/{len(cols)} filled")
        for k in ["os_version","chipset_nm","cpu_cores","cpu_max_speed_ghz","ram_gb","storage_gb",
                  "ram_type","storage_type","display_size_inch","refresh_rate_hz","display_ppi",
                  "display_resolution_type","main_camera_count","main_camera_mp","main_camera_aperture",
                  "has_ois","has_ultrawide","ultrawide_mp","has_telephoto","telephoto_mp","has_periscope",
                  "optical_zoom_x","max_video_resolution","max_video_fps","video_8k","video_4k",
                  "selfie_camera_count","selfie_camera_mp","battery_mah","battery_type","battery_removable",
                  "charging_watt","has_wireless_charging","wireless_charging_watt","has_reverse_wireless",
                  "weight_g","thickness_mm","ip_rating","has_amoled","hdr_type","screen_protection",
                  "has_ip_rating","has_face_unlock","has_face_id","has_fingerprint","fingerprint_type",
                  "has_dual_sim","has_esim","sim_type","colors","wifi_version","has_dual_sim","bluetooth_version",
                  "has_gps","has_nfc","has_stereo_speakers","has_3_5mm_jack","has_hi_res_audio","has_usbc_otg" if False else "has_usb_otg",
                  "price_inr","price_usd","price_eur","network_speed","max_memory_card_gb","status",
                  "models_list","image_url"]:
            if k in cols:
                print(f"  {k:24s} = {cols[k]}")
        print("  ORIGINAL IMG:", gsm.get("image_url"))
        
        over = [k for k, v in cols.items() if isinstance(v, str) and len(v) > 450]
        print("  LONG FIELDS:", over)
        time.sleep(2)
