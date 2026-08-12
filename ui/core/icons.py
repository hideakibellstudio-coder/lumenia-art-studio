from PySide6 import QtGui, QtCore, QtSvg
import xml.etree.ElementTree as ET

SVG_ICONS = {
    "brush": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" fill="currentColor"><path d="M240-120q-45 0-89-22t-71-58q26 0 53-20.5t27-59.5q0-50 35-85t85-35q50 0 85 35t35 85q0 66-47 113t-113 47Zm0-80q33 0 56.5-23.5T320-280q0-17-11.5-28.5T280-320q-17 0-28.5 11.5T240-280q0 23-5.5 42T220-202q5 2 10 2h10Zm230-160L360-470l358-358q11-11 27.5-11.5T774-828l54 54q12 12 12 28t-12 28L470-360Zm-190 80Z"/></svg>""",
    
    "eraser": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="M396-160q-98 0-167-69t-69-167q0-46 17-89.5t52-78.5l167-167q35-35 78.5-52t89.5-17q98 0 167 69t69 167q0 46-17 89.5T731-396L564-229q-35 35-78.5 52T396-160Z"/></svg>""",

    "smudge": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="M491-200q12-1 20.5-9.5T520-230q0-14-9-22.5t-23-7.5q-41 3-87-22.5T343-375q-2-11-10.5-18t-19.5-7q-14 0-23 10.5t-6 24.5q17 91 80 130t127 35Zm-239.5 26Q160-268 160-408q0-100 79.5-217.5T480-880q161 137 240.5 254.5T800-408q0 140-91.5 234T480-80q-137 0-228.5-94ZM652-230.5Q720-301 720-408q0-73-60.5-165T480-774Q361-665 300.5-573T240-408q0 107 68 177.5T480-160q104 0 172-70.5ZM480-480Z"/></svg>""",
    
    "theme": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
    </svg>""",
    
    "zoom_in": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="11" y1="8" x2="11" y2="14"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
    </svg>""",
    
    "zoom_out": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
    </svg>""",
    
    "reset": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
        <path d="M3 3v5h5"/>
    </svg>""",
    
    "copy": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M7 7m0 2.667a2.667 2.667 0 0 1 2.667 -2.667h8.666a2.667 2.667 0 0 1 2.667 2.667v8.666a2.667 2.667 0 0 1 -2.667 2.667h-8.666a2.667 2.667 0 0 1 -2.667 -2.667z" /><path d="M4.012 16.737a2.005 2.005 0 0 1 -1.012 -1.737v-10c0 -1.1 .9 -2 2 -2h10c.75 0 1.158 .385 1.5 1" /></svg>""",
    
    "arrow-swap": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/></svg>""",
    
    "maximize": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>""",
    
    "refresh_ccw": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v6h6"/><path d="M21 12A9 9 0 0 0 6 5.3L3 8"/><path d="M21 22v-6h-6"/><path d="M3 12a9 9 0 0 0 15 6.7l3-2.7"/></svg>""",
    
    "flip_horizontal": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v2" /><path d="M12 8v2" /><path d="M12 13v2" /><path d="M12 18v2" /><path d="M9 12L3 6v12z" /><path d="M15 12l6-6v12z" /></svg>""",
    
    "flip_vertical": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h2" /><path d="M8 12h2" /><path d="M13 12h2" /><path d="M18 12h2" /><path d="M12 9l-6-6h12z" /><path d="M12 15l-6 6h12z" /></svg>""",

    "trash": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>""",

    "settings": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>""",

    "cat_lapis": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="m240-320 100-360h60v-60l60-140h40l60 140v60h60l100 360H240Zm105-80h270l-56-200H401l-56 200ZM160-120l22-65q8-25 29-40t47-15h444q26 0 47 15t29 40l22 65H160Zm185-280h270-270Z"/></svg>""",
    "cat_canetas": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="m160-120 22-65q8-25 29-40t47-15h444q26 0 47 15t29 40l22 65H160Zm80-200 200-520h80l200 520H240Zm116-80h248L480-721 356-400Zm0 0h248-248Z"/></svg>""",
    "cat_pinceis": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="M480-320q-100 0-170-69.5T240-562q0-74 44-139t96.5-114q52.5-49 96-77l43.5-28q0 57 20.5 96t77.5 83q59 46 80.5 85.5T720-562q0 103-70 172.5T480-320Zm113-126.5Q640-493 640-562q0-35-17-61.5T567-680q-31-23-55.5-49.5T470-788q-79 65-114.5 120T320-562q0 69 47 115.5T480-400q66 0 113-46.5ZM480-594ZM160-120l22-65q8-25 29-40t47-15h444q26 0 47 15t29 40l22 65H160Z"/></svg>""",
    "cat_smudges": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="M491-200q12-1 20.5-9.5T520-230q0-14-9-22.5t-23-7.5q-41 3-87-22.5T343-375q-2-11-10.5-18t-19.5-7q-14 0-23 10.5t-6 24.5q17 91 80 130t127 35Zm-239.5 26Q160-268 160-408q0-100 79.5-217.5T480-880q161 137 240.5 254.5T800-408q0 140-91.5 234T480-80q-137 0-228.5-94ZM652-230.5Q720-301 720-408q0-73-60.5-165T480-774Q361-665 300.5-573T240-408q0 107 68 177.5T480-160q104 0 172-70.5ZM480-480Z"/></svg>""",
    "cat_borrachas": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="M396-160q-98 0-167-69t-69-167q0-46 17-89.5t52-78.5l167-167q35-35 78.5-52t89.5-17q98 0 167 69t69 167q0 46-17 89.5T731-396L564-229q-35 35-78.5 52T396-160Z"/></svg>""",
    "cat_pulverizadores": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="M560-640q-17 0-28.5-11.5T520-680q0-17 11.5-28.5T560-720q17 0 28.5 11.5T600-680q0 17-11.5 28.5T560-640Zm240 0q-17 0-28.5-11.5T760-680q0-17 11.5-28.5T800-720q17 0 28.5 11.5T840-680q0 17-11.5 28.5T800-640Zm-120-80q-17 0-28.5-11.5T640-760q0-17 11.5-28.5T680-800q17 0 28.5 11.5T720-760q0 17-11.5 28.5T680-720Zm120-80q-17 0-28.5-11.5T760-840q0-17 11.5-28.5T800-880q17 0 28.5 11.5T840-840q0 17-11.5 28.5T800-800ZM680-560q-17 0-28.5-11.5T640-600q0-17 11.5-28.5T680-640q17 0 28.5 11.5T720-600q0 17-11.5 28.5T680-560Zm120 80q-17 0-28.5-11.5T760-520q0-17 11.5-28.5T800-560q17 0 28.5 11.5T840-520q0 17-11.5 28.5T800-480ZM200-200h240v-320H200v320Zm-80 80v-400q0-33 23.5-56.5T200-600h240q33 0 56.5 23.5T520-520v400H120Zm80-480v-160q0-33 23.5-56.5T280-840h160v240h-80v-160h-80v160h-80Zm0 400h240-240Z"/></svg>""",
    "cat_efeitos": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="m176-120-56-56 301-302-181-45 198-123-17-234 179 151 216-88-87 217 151 178-234-16-124 198-45-181-301 301Zm24-520-80-80 80-80 80 80-80 80Zm355 197 48-79 93 7-60-71 35-86-86 35-71-59 7 92-79 49 90 22 23 90Zm165 323-80-80 80-80 80 80-80 80ZM569-570Z"/></svg>""",

    "import": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>""",

    "power": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>""",

    
    "close": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>""",
    
    "eye": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
        <circle cx="12" cy="12" r="3"/>
    </svg>""",
    
    "eye_off": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
        <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.3 2.68"/>
        <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7c.44 0 .87-.03 1.28-.09"/>
        <line x1="2" x2="22" y1="2" y2="22"/>
    </svg>""",
    
    "folder": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 2H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>
    </svg>""",
    
    "sliders": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>
        <line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>
        <line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>
        <line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>
    </svg>""",
    
    "clip_mask": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M15 7l-6.5 6.5a1.5 1.5 0 0 0 3 3l6.5 -6.5a3 3 0 0 0 -6 -6l-6.5 6.5a4.5 4.5 0 0 0 9 9l6.5 -6.5"/>
    </svg>""",
    
    "lock": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>""",
    
    "alpha_lock": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M14 10m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/>
        <path d="M21 12a9 9 0 1 1 -18 0a9 9 0 0 1 18 0z"/>
        <path d="M12.5 11.5l-4 4l1.5 1.5"/>
        <path d="M12 15l-1.5 -1.5"/>
    </svg>""",
    
    "plus": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M5 12h14"/>
        <path d="M12 5v14"/>
    </svg>""",
    
    "chevron_up": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 15 12 9 6 15"/>
    </svg>""",
    
    "chevron_down": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9"/>
    </svg>""",
    
    "merge": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M21 18a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3"/>
        <path d="M3 3m0 3a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v0a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3z"/>
        <path d="M12 9v8"/>
        <path d="M9 14l3 3l3 -3"/>
    </svg>""",
    
    "duplicate": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
        <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
    </svg>""",
    
    "clean_layer": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2v4"/><path d="m16.2 7.8 2.9-2.9"/><path d="M18 12h4"/><path d="m16.2 16.2 2.9 2.9"/><path d="M12 18v4"/><path d="m4.9 19.1 2.9-2.9"/><path d="M2 12h4"/><path d="m4.9 4.9 2.9 2.9"/>
    </svg>""",
    
    "fx": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 4l2 16"/>
        <path d="M4 10h8"/>
        <path d="M16 7l4 4-4 4"/>
        <path d="M20 7l-4 4 4 4"/>
    </svg>""",
    
    "filter": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
    </svg>""",

    "smudge": """<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="currentColor"><path d="M491-200q12-1 20.5-9.5T520-230q0-14-9-22.5t-23-7.5q-41 3-87-22.5T343-375q-2-11-10.5-18t-19.5-7q-14 0-23 10.5t-6 24.5q17 91 80 130t127 35Zm-239.5 26Q160-268 160-408q0-100 79.5-217.5T480-880q161 137 240.5 254.5T800-408q0 140-91.5 234T480-80q-137 0-228.5-94ZM652-230.5Q720-301 720-408q0-73-60.5-165T480-774Q361-665 300.5-573T240-408q0 107 68 177.5T480-160q104 0 172-70.5ZM480-480Z"/></svg>""",

    "bucket": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m19 11-8-8-8.6 8.6a2 2 0 0 0 0 2.8l5.2 5.2c.8.8 2 .8 2.8 0L19 11Z"/><path d="m5 2 5 5"/><path d="M2 13h15"/><path d="M22 20a2 2 0 1 1-4 0c0-1.6 1.7-2.4 2-4 .3 1.6 2 2.4 2 4Z"/></svg>""",

    "eyedrop": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 9-8.414 8.414A2 2 0 0 0 3 18.828v1.344a2 2 0 0 1-.586 1.414A2 2 0 0 1 3.828 21h1.344a2 2 0 0 0 1.414-.586L15 12"/><path d="m18 9 .4.4a1 1 0 1 1-3 3l-3.8-3.8a1 1 0 1 1 3-3l.4.4 3.4-3.4a1 1 0 1 1 3 3z"/><path d="m2 22 .414-.414"/></svg>""",

    "wand": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 4V2"/><path d="M15 16v-2"/><path d="M8 9h2"/><path d="M20 9h2"/><path d="M17.8 11.8 19 13"/><path d="M15 9h.01"/><path d="M17.8 6.2 19 5"/><path d="m3 21 9-9"/><path d="M12.2 6.2 11 5"/></svg>""",

    "transform": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 9l-3 3 3 3"/><path d="M9 5l3-3 3 3"/><path d="M15 19l-3 3-3-3"/><path d="M19 9l3 3-3 3"/><path d="M2 12h20"/><path d="M12 2v20"/></svg>""",

    "rect_select": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 3a2 2 0 0 0-2 2"/><path d="M19 3a2 2 0 0 1 2 2"/><path d="M21 19a2 2 0 0 1-2 2"/><path d="M5 21a2 2 0 0 0-2-2"/><path d="M9 3h1"/><path d="M9 21h1"/><path d="M14 3h1"/><path d="M14 21h1"/><path d="M3 9v1"/><path d="M21 9v1"/><path d="M3 14v1"/><path d="M21 14v1"/></svg>""",

    "ellipse_select": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.1 2.182a10 10 0 0 1 3.8 0"/><path d="M13.9 21.818a10 10 0 0 1-3.8 0"/><path d="M17.609 3.721a10 10 0 0 1 2.69 2.7"/><path d="M2.182 13.9a10 10 0 0 1 0-3.8"/><path d="M20.279 17.609a10 10 0 0 1-2.7 2.69"/><path d="M21.818 10.1a10 10 0 0 1 0 3.8"/><path d="M3.721 6.391a10 10 0 0 1 2.7-2.69"/><path d="M6.391 20.279a10 10 0 0 1-2.69-2.7"/></svg>""",

    "lasso": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3.704 14.467A10 8 0 0 1 2 10a10 8 0 0 1 20 0 10 8 0 0 1-10 8 10 8 0 0 1-5.181-1.158"/><path d="M7 22a5 5 0 0 1-2-3.994"/><circle cx="5" cy="16" r="2"/></svg>"""
}

def svg_to_icon(svg_xml: str, size: QtCore.QSize = QtCore.QSize(24, 24)) -> QtGui.QIcon:
    byte_array = QtCore.QByteArray(svg_xml.encode('utf-8'))
    renderer = QtSvg.QSvgRenderer(byte_array)
    
    pixmap = QtGui.QPixmap(size)
    pixmap.fill(QtCore.Qt.transparent)
    
    painter = QtGui.QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QtGui.QIcon(pixmap)

class DynamicThemeIconEngine(QtGui.QIconEngine):
    def __init__(self, icon_manager, icon_name: str, color_key: str):
        super().__init__()
        self.icon_manager = icon_manager
        self.icon_name = icon_name
        self.color_key = color_key

    def paint(self, painter: QtGui.QPainter, rect: QtCore.QRect, mode: QtGui.QIcon.Mode, state: QtGui.QIcon.State):
        pixmap = self.pixmap(rect.size(), mode, state)
        if not pixmap.isNull():
            align_rect = rect
            x_offset = (rect.width() - pixmap.width()) // 2
            y_offset = (rect.height() - pixmap.height()) // 2
            if x_offset > 0 or y_offset > 0:
                align_rect = QtCore.QRect(rect.x() + x_offset, rect.y() + y_offset, pixmap.width(), pixmap.height())
            painter.drawPixmap(align_rect, pixmap)

    def clone(self):
        return DynamicThemeIconEngine(self.icon_manager, self.icon_name, self.color_key)

    def pixmap(self, size: QtCore.QSize, mode: QtGui.QIcon.Mode, state: QtGui.QIcon.State) -> QtGui.QPixmap:
        if size.isEmpty():
            size = QtCore.QSize(24, 24)
        return self.icon_manager.get_rendered_pixmap(self.icon_name, self.color_key, size)

class IconManager(QtCore.QObject):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._pixmap_cache = {}
        
        # Conecta às mudanças de tema
        from ui.core.theme.manager import ThemeManager
        ThemeManager.instance().themeChanged.connect(self._clear_cache)

    def _clear_cache(self, _theme_name=None):
        self._pixmap_cache.clear()

    def get_rendered_pixmap(self, icon_name: str, color_key: str, size: QtCore.QSize) -> QtGui.QPixmap:
        cache_key = (icon_name, color_key, size.width(), size.height())
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]

        svg_template = SVG_ICONS.get(icon_name)
        if not svg_template:
            return QtGui.QPixmap()

        from ui.core.theme.manager import ThemeManager
        color = ThemeManager.instance().get_color(color_key)

        svg_xml = svg_template.replace("currentColor", color)
        byte_array = QtCore.QByteArray(svg_xml.encode('utf-8'))
        
        renderer = QtSvg.QSvgRenderer(byte_array)
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.transparent)
        
        painter = QtGui.QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        self._pixmap_cache[cache_key] = pixmap
        return pixmap

def get_icon(name: str, color: str = None) -> QtGui.QIcon:
    name = name.replace("-", "_").replace(" ", "_")
    if not SVG_ICONS.get(name):
        return QtGui.QIcon()
        
    # Se uma cor específica (como hex) for fornecida, renderiza estaticamente
    if color and color.startswith("#"):
        svg_xml = SVG_ICONS[name].replace("currentColor", color)
        return svg_to_icon(svg_xml)
        
    # Caso contrário, usa a cor do tema dinâmica
    color_key = color if color else "text_main"
    return QtGui.QIcon(DynamicThemeIconEngine(IconManager.instance(), name, color_key))
