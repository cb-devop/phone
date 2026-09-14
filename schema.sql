-- ═══════════════════════════════════════════════════════════
-- PHONES TABLE — All fields as separate columns
-- ═══════════════════════════════════════════════════════════

-- WARNING: yeh DROP existing test data delete karega
DROP TABLE IF EXISTS phones CASCADE;

CREATE TABLE phones (
    id                          SERIAL PRIMARY KEY,
    unique_id                   VARCHAR(200) UNIQUE NOT NULL,

    -- ═══════════════ IDENTITY ═══════════════
    brand                       VARCHAR(50) NOT NULL,
    model                       VARCHAR(200) NOT NULL,
    release_year                INT,
    announced_date              TEXT,
    status                      VARCHAR(100),  -- 'Available', 'Coming soon', 'Discontinued'

    -- ═══════════════ PRICE ═══════════════
    price_inr                   INT,
    price_usd                   INT,
    price_eur                   INT,
    price_updated_at            TIMESTAMP,

    -- ═══════════════ NETWORK ═══════════════
    network_technology          VARCHAR(300),  -- 'GSM / HSPA / LTE / 5G'
    has_2g                      BOOLEAN,
    has_3g                      BOOLEAN,
    has_4g                      BOOLEAN,
    has_5g                      BOOLEAN,
    network_speed               VARCHAR(300),
    sim_type                    VARCHAR(300),
    sim_count                   INT,
    has_esim                    BOOLEAN,
    has_dual_sim                BOOLEAN,

    -- ═══════════════ BODY ═══════════════
    dimensions                  VARCHAR(300),
    height_mm                   DECIMAL(5,1),
    width_mm                    DECIMAL(5,1),
    thickness_mm                DECIMAL(4,1),
    weight_g                    INT,
    build_front                 VARCHAR(300),  -- 'Glass front (Gorilla Glass)'
    build_back                  VARCHAR(300),
    build_frame                 VARCHAR(300),
    has_ip_rating               BOOLEAN,
    ip_rating                   VARCHAR(30),   -- 'IP68', 'IP67'
    has_waterproof              BOOLEAN,
    has_dustproof               BOOLEAN,

    -- ═══════════════ DISPLAY ═══════════════
    display_type                VARCHAR(400),  -- 'LTPO AMOLED, 120Hz, HDR10+'
    display_size_inch           DECIMAL(3,1),
    display_resolution          VARCHAR(150),  -- '1080 x 2340 pixels'
    display_width_px            INT,
    display_height_px           INT,
    display_ppi                 INT,
    refresh_rate_hz             INT,
    display_resolution_type     VARCHAR(20),   -- 'HD', 'HD+', 'FHD', 'FHD+', 'QHD+'
    has_amoled                  BOOLEAN,
    has_oled                    BOOLEAN,
    has_lcd                     BOOLEAN,
    has_ltpo                    BOOLEAN,
    has_hdr                     BOOLEAN,
    hdr_type                    VARCHAR(50),   -- 'HDR10+', 'Dolby Vision'
    screen_protection           VARCHAR(300),  -- 'Gorilla Glass Victus 2'
    has_always_on               BOOLEAN,
    has_punch_hole              BOOLEAN,
    has_notch                   BOOLEAN,

    -- ═══════════════ PLATFORM ═══════════════
    os                          VARCHAR(200),  -- 'Android 14'
    os_version                  DECIMAL(4,1),
    os_family                   VARCHAR(50),   -- 'Android', 'iOS'
    chipset                     VARCHAR(300),  -- 'Snapdragon 8 Gen 3'
    chipset_brand               VARCHAR(50),   -- 'Snapdragon', 'MediaTek', 'Exynos'
    chipset_model               VARCHAR(150),  -- '8 Gen 3', 'Dimensity 9300'
    chipset_nm                  INT,           -- 4, 3 (nanometers)
    cpu                         VARCHAR(400),
    cpu_cores                   INT,
    cpu_max_speed_ghz           DECIMAL(4,2),
    cpu_architecture            VARCHAR(200),
    gpu                         VARCHAR(200),  -- 'Adreno 750'

    -- ═══════════════ MEMORY ═══════════════
    ram_gb                      INT,
    ram_type                    VARCHAR(30),   -- 'LPDDR5X'
    storage_gb                  INT,
    storage_type                VARCHAR(30),   -- 'UFS 4.0'
    has_memory_card             BOOLEAN,
    memory_card_type            VARCHAR(50),   -- 'microSDXC'
    max_memory_card_gb          INT,

    -- ═══════════════ MAIN CAMERA ═══════════════
    main_camera_count           INT,
    main_camera_mp              INT,           -- Primary MP
    main_camera_aperture        DECIMAL(3,1),  -- f/1.8 = 1.8
    main_camera_ois             BOOLEAN,
    main_camera_eis             BOOLEAN,
    has_ultrawide               BOOLEAN,
    ultrawide_mp                INT,
    has_telephoto               BOOLEAN,
    telephoto_mp                INT,
    has_periscope               BOOLEAN,
    has_macro                   BOOLEAN,
    macro_mp                    INT,
    has_depth_sensor            BOOLEAN,
    has_tof_sensor              BOOLEAN,
    optical_zoom_x              INT,           -- 3x, 5x, 10x
    digital_zoom_x              INT,
    has_laser_autofocus         BOOLEAN,
    has_pdaf                    BOOLEAN,
    has_flash                   BOOLEAN,
    flash_type                  VARCHAR(50),   -- 'Dual-LED', 'LED'

    -- Main Camera Video
    max_video_resolution        VARCHAR(20),   -- '8K', '4K'
    max_video_fps               INT,           -- 30, 60, 120, 240
    video_8k                    BOOLEAN,
    video_4k                    BOOLEAN,
    video_1080p                 BOOLEAN,
    video_hdr                   BOOLEAN,
    video_ois                   BOOLEAN,
    has_prores                  BOOLEAN,
    has_log_profile             BOOLEAN,

    -- ═══════════════ SELFIE CAMERA ═══════════════
    selfie_camera_mp            INT,
    selfie_camera_aperture      DECIMAL(3,1),
    selfie_camera_count         INT,
    selfie_has_autofocus        BOOLEAN,
    selfie_has_hdr              BOOLEAN,
    selfie_max_video_resolution VARCHAR(20),
    selfie_max_video_fps        INT,
    has_under_display_camera    BOOLEAN,
    has_popup_camera            BOOLEAN,

    -- ═══════════════ DXOMARK ═══════════════
    dxomark_overall             INT,
    dxomark_photo               INT,
    dxomark_video               INT,
    dxomark_zoom                INT,
    dxomark_selfie              INT,
    dxomark_url                 TEXT,

    -- ═══════════════ BENCHMARKS ═══════════════
    antutu_score                INT,
    geekbench_single            INT,
    geekbench_multi             INT,
    gfxbench_score              INT,
    benchmark_url               TEXT,

    -- ═══════════════ SOUND ═══════════════
    has_loudspeaker             BOOLEAN,
    has_stereo_speakers         BOOLEAN,
    has_3_5mm_jack              BOOLEAN,
    has_hi_res_audio            BOOLEAN,
    audio_features              VARCHAR(300),  -- 'Tuned by AKG'

    -- ═══════════════ CONNECTIVITY ═══════════════
    has_wifi                    BOOLEAN,
    wifi_version                VARCHAR(30),   -- 'Wi-Fi 6E', 'Wi-Fi 7'
    wifi_bands                  VARCHAR(30),   -- 'tri-band'
    has_bluetooth               BOOLEAN,
    bluetooth_version           DECIMAL(3,1),  -- 5.3
    has_gps                     BOOLEAN,
    gps_systems                 VARCHAR(300),  -- 'GPS, GLONASS, BDS, GALILEO'
    has_nfc                     BOOLEAN,
    has_usb_otg                 BOOLEAN,
    usb_type                    VARCHAR(100),  -- 'USB Type-C 3.2'
    has_fm_radio                BOOLEAN,
    has_infrared                BOOLEAN,

    -- ═══════════════ SENSORS ═══════════════
    has_fingerprint             BOOLEAN,
    fingerprint_type            VARCHAR(50),   -- 'under display', 'side-mounted'
    fingerprint_technology      VARCHAR(50),   -- 'optical', 'ultrasonic'
    has_face_unlock             BOOLEAN,
    has_face_id                 BOOLEAN,
    has_accelerometer           BOOLEAN,
    has_gyro                    BOOLEAN,
    has_proximity               BOOLEAN,
    has_compass                 BOOLEAN,
    has_barometer               BOOLEAN,
    has_heart_rate              BOOLEAN,
    has_spo2                    BOOLEAN,

    -- ═══════════════ BATTERY ═══════════════
    battery_mah                 INT,
    battery_type                VARCHAR(50),   -- 'Li-Po', 'Li-Ion'
    battery_removable           BOOLEAN,
    charging_watt               INT,
    has_wireless_charging       BOOLEAN,
    wireless_charging_watt      INT,
    has_reverse_wireless        BOOLEAN,
    has_reverse_wired           BOOLEAN,
    has_fast_charging           BOOLEAN,
    has_bypass_charging         BOOLEAN,
    charging_features           VARCHAR(400),  -- 'PD3.0, QC4'

    -- ═══════════════ MISC ═══════════════
    colors                      TEXT,
    models_list                 TEXT,          -- 'SM-S921B, SM-S921U'
    sar_head                    VARCHAR(50),
    sar_body                    VARCHAR(50),

    -- ═══════════════ IMAGE ═══════════════
    image_url                   TEXT,
    image_public_id             VARCHAR(200),
    original_image_url          TEXT,

    -- ═══════════════ FULL DATA (backup) ═══════════════
    full_specs                  JSONB,

    -- ═══════════════ META ═══════════════
    reference_url               TEXT,
    created_at                  TIMESTAMP DEFAULT NOW(),
    updated_at                  TIMESTAMP DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════
-- INDEXES — Fast filtering
-- ═══════════════════════════════════════════════════════════

-- Basic filters
CREATE INDEX idx_brand            ON phones(brand);
CREATE INDEX idx_price            ON phones(price_inr);
CREATE INDEX idx_year             ON phones(release_year);
CREATE INDEX idx_status           ON phones(status);

-- Performance
CREATE INDEX idx_ram              ON phones(ram_gb);
CREATE INDEX idx_storage          ON phones(storage_gb);
CREATE INDEX idx_chipset_brand    ON phones(chipset_brand);
CREATE INDEX idx_antutu           ON phones(antutu_score);
CREATE INDEX idx_geekbench        ON phones(geekbench_single);

-- Display
CREATE INDEX idx_display_size     ON phones(display_size_inch);
CREATE INDEX idx_refresh_rate     ON phones(refresh_rate_hz);
CREATE INDEX idx_display_ppi      ON phones(display_ppi);

-- Camera
CREATE INDEX idx_main_camera_mp   ON phones(main_camera_mp);
CREATE INDEX idx_selfie_camera_mp ON phones(selfie_camera_mp);
CREATE INDEX idx_optical_zoom     ON phones(optical_zoom_x);
CREATE INDEX idx_has_ois          ON phones(main_camera_ois);
CREATE INDEX idx_video_res        ON phones(max_video_resolution);
CREATE INDEX idx_dxomark          ON phones(dxomark_overall);

-- Battery
CREATE INDEX idx_battery          ON phones(battery_mah);
CREATE INDEX idx_charging         ON phones(charging_watt);

-- Connectivity
CREATE INDEX idx_5g               ON phones(has_5g);
CREATE INDEX idx_nfc              ON phones(has_nfc);
CREATE INDEX idx_35mm             ON phones(has_3_5mm_jack);

-- Body
CREATE INDEX idx_weight           ON phones(weight_g);
CREATE INDEX idx_thickness        ON phones(thickness_mm);

-- Full specs (for rare queries)
CREATE INDEX idx_full_specs       ON phones USING GIN(full_specs);

-- ═══════════════════════════════════════════════════════════
-- SCRAPER PROGRESS (Resume ke liye)
-- ═══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scraper_progress (
    id              SERIAL PRIMARY KEY,
    brand           VARCHAR(50) NOT NULL,
    phone_index     INT NOT NULL,
    phone_url       TEXT,
    phone_name      VARCHAR(200),
    unique_id       VARCHAR(200),
    status          VARCHAR(20) DEFAULT 'done',
    error_message   TEXT,
    scraped_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(brand, phone_index)
);

CREATE INDEX IF NOT EXISTS idx_progress_brand  ON scraper_progress(brand);
CREATE INDEX IF NOT EXISTS idx_progress_status ON scraper_progress(status);
