import sys
import os
import webbrowser
import subprocess
import customtkinter as ctk
import shutil
import tempfile
import requests

APP_VERSION = "1.0.0"
UPDATE_INFO_URL = "https://raw.githubusercontent.com/borin009/hwupdate/main/update.json"



# -------------------------------------------------
# Force correct import path
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import hw_check
import mi_check_1

# -------------------------------------------------
# FASTBOOT PATH
# -------------------------------------------------
FASTBOOT_PATH = os.path.join(BASE_DIR, "adb_hw", "fastboot.exe")

def version_tuple(v):
    return tuple(map(int, v.split(".")))

def check_for_update():
    try:
        r = requests.get(UPDATE_INFO_URL, timeout=5)
        r.raise_for_status()
        info = r.json()

        if version_tuple(info["version"]) > version_tuple(APP_VERSION):
            r = requests.get(info["url"], stream=True, timeout=10)
            r.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
                tmp = f.name

            shutil.copy(tmp, os.path.abspath(__file__))
            os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])

    except Exception as e:
        print("UPDATE ERROR:", e)
        print("RAW RESPONSE:", r.text if 'r' in locals() else "NO RESPONSE")


# -------------------------------------------------
# UI setup
# -------------------------------------------------
BASE_FONT = ("Consolas", 15)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Hw Check Info")
app.geometry("980x600")
app.minsize(980, 600)

# =================================================
# MAIN LAYOUT (LEFT / RIGHT)
# =================================================
main_frame = ctk.CTkFrame(app, fg_color="transparent")
main_frame.pack(fill="both", expand=True, padx=12, pady=12)

main_frame.grid_columnconfigure(0, weight=3)
main_frame.grid_columnconfigure(1, weight=1)
main_frame.grid_rowconfigure(0, weight=1)

# =================================================
# LEFT : OUTPUT BOX
# =================================================
output_box = ctk.CTkTextbox(
    main_frame,
    font=BASE_FONT,
    wrap="word",
    corner_radius=12
)
output_box.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
output_box.bind("<Key>", lambda e: "break")

# =================================================
# RIGHT : CONTROL PANEL
# =================================================
right_panel = ctk.CTkFrame(main_frame, corner_radius=16)
right_panel.grid(row=0, column=1, sticky="nsew")
right_panel.grid_columnconfigure(0, weight=1)

# -------------------------------------------------
# Buttons
# -------------------------------------------------

def styled_button(parent, text, command):
    return ctk.CTkButton(
        parent,
        text=text,
        height=42,
        corner_radius=22,
        command=command
    )

styled_button(right_panel, "📱 Check Huawei / Honor ", lambda: run_hw()).pack(fill="x", padx=18, pady=(20, 10))
styled_button(right_panel, "📱 Check MI", lambda: run_mi()).pack(fill="x", padx=18, pady=10)
styled_button(right_panel, "📋 Copy SN", lambda: copy_sn_only()).pack(fill="x", padx=18, pady=10)
styled_button(right_panel, "📋 Copy Version", lambda: copy_version_only()).pack(fill="x", padx=18, pady=(10, 20))

# -------------------------------------------------
# FRP SECTION
# -------------------------------------------------
ctk.CTkLabel(
    right_panel,
    text="🔐 Honor FRP Key",
    anchor="w"
).pack(fill="x", padx=18, pady=(10, 6))

frp_entry = ctk.CTkEntry(
    right_panel,
    height=40,
    placeholder_text="Enter FRP Key"
)
frp_entry.pack(fill="x", padx=18, pady=(0, 10))

ctk.CTkButton(
    right_panel,
    text="🔓 Erase Frp",
    height=40,
    corner_radius=22,
    command=lambda: run_fastboot_frp_unlock()
).pack(fill="x", padx=18, pady=(0, 20))

# =================================================
# HELPERS & LOGIC (UNCHANGED)
# =================================================
link_map = {}

def clear_output():
    link_map.clear()
    output_box.delete("1.0", "end")

def add_text(text):
    color = "#ffffff"
    if text.startswith("MODE"):
        color = "#00e5ff"
    elif text.startswith("🛠 MODE"):
        color = "#00e5ff"
    elif text.startswith("Please"):
        color = "#00e5ff"
    elif text.startswith("❌"):
        color = "#ff0000"
    elif text.startswith("🔍 Check Device Info"):
        color = "#0BB411"
    elif "Product Model" in text:
        color = "#b4aef6"
    elif "Build Number" in text:
        color = "#c1f20f"
    elif "INFO locked" in text:
        color = "#ff5252"
    elif "INFO unlocked" in text:
        color = "#00e676"
    elif text.startswith("📌"):
        color = "#64ffda"
    elif text.startswith("•"):
        color = "#cccccc"
    elif text.startswith("→"):
        color = "#82cfff"

    start = output_box.index("end-1c")
    output_box.insert("end", text + "\n")
    end = output_box.index("end")
    tag = f"text_{start}"
    output_box.tag_add(tag, start, end)
    output_box.tag_config(tag, foreground=color)

def add_clickable_file(label_text, filename, url):
    output_box.insert("end", f"{label_text} : ")
    start = output_box.index("end-1c")
    output_box.insert("end", filename)
    end = output_box.index("end")
    output_box.insert("end", "\n")

    tag = f"link_{start}"
    link_map[tag] = url
    output_box.tag_add(tag, start, end)
    output_box.tag_config(tag, foreground="#4da6ff", underline=True)
    output_box.tag_bind(tag, "<Button-1>", lambda e, t=tag: webbrowser.open_new_tab(link_map[t]))

def copy_sn_only():
    text = output_box.get("1.0", "end")
    sn = "SN NOT FOUND"
    for line in text.splitlines():
        if "serial" in line.lower():
            sn = line.split(":", 1)[1].strip()
            break
    app.clipboard_clear()
    app.clipboard_append(sn)

def copy_version_only():
    text = output_box.get("1.0", "end")
    app.clipboard_clear()
    app.clipboard_append(text.strip())

def run_hw():
    clear_output()
    result = hw_check.main()
    for line in result.splitlines():
        if "||LINK||" in line:
            left, url = line.split("||LINK||", 1)
            label, filename = left.split(":", 1)
            add_clickable_file(label.strip(), filename.strip(), url.strip())
        else:
            add_text(line)

def run_mi():
    clear_output()
    result = mi_check_1.main()
    for line in result.splitlines():
        if "||LINK||" in line:
            left, url = line.split("||LINK||", 1)
            label, filename = left.split(":", 1)
            add_clickable_file(label.strip(), filename.strip(), url.strip())
        else:
            add_text(line)

def run_fastboot_frp_unlock():
    key = frp_entry.get().strip()
    if not key:
        add_text("INFO locked : FRP key is empty")
        return

    cmd = [FASTBOOT_PATH, "oem", "frp-unlock", key]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in result.stdout.splitlines():
        add_text("• " + line)
    for line in result.stderr.splitlines():
        add_text("INFO locked : " + line)

# -------------------------------------------------
# Startup text
# -------------------------------------------------
clear_output()
add_text("📌 How to connect device")
add_text("────────────────────────")
add_text("• FASTBOOT : Volume Down + Power")
add_text("• SIDELOAD : Volume Up + Power")
add_text("────────────────────────")
add_clickable_file(
    "Whatsapp Group",
    "Click Here",
    "https://chat.whatsapp.com/I5OVKaxGcpo7cDdlPnh6ce"
)

add_clickable_file(
    "Telegram Group",
    "Click Here",
    "https://t.me/+tyiZZCl8Z70xYjk1"
)

check_for_update()

app.mainloop()