import os
import datetime
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import requests
import io
import calendar
import json
import webbrowser
import time
import subprocess
import sys
import shutil

from meta_api import MetaAPI
from gdrive_api import GoogleDriveAPI
import config

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# === MODERN COLOR PALETTE ===
BG_PRIMARY = "#0a0e27"
BG_SECONDARY = "#151932"
BG_CARD = "#1a1f3a"
ACCENT_BLUE = "#4f46e5"
ACCENT_PURPLE = "#7c3aed"
ACCENT_GREEN = "#10b981"
ACCENT_ORANGE = "#f59e0b"
ACCENT_RED = "#ef4444"
TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#94a3b8"
TEXT_DIM = "#64748b"
BORDER_COLOR = "#2d3250"
HOVER_COLOR = "#252b48"

# === UTILITY FUNCTIONS ===

# Cores para subpastas/contas
FOLDER_COLORS = {
    0: "#3b82f6",  # Azul
    1: "#8b5cf6",  # Roxo
    2: "#ec4899",  # Rosa
    3: "#f59e0b",  # Laranja
    4: "#10b981",  # Verde
    5: "#06b6d4",  # Ciano
    6: "#f43f5e",  # Vermelho
    7: "#6366f1",  # Índigo
}

def get_folder_color(folder_name):
    """Retorna uma cor única para cada pasta/conta"""
    if not folder_name:
        return TEXT_DIM
    # Gera um índice baseado no hash do nome
    idx = hash(folder_name) % len(FOLDER_COLORS)
    return FOLDER_COLORS[idx]

def create_gradient_frame(parent, color1, color2):
    """Cria um frame com efeito de gradiente simulado"""
    frame = ctk.CTkFrame(parent, fg_color=color1, corner_radius=20)
    return frame

def format_time_ago(timestamp):
    """Formata timestamp para 'X horas atrás', 'X dias atrás', etc"""
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return "agora mesmo"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins} min atrás"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h atrás"
    else:
        days = int(diff / 86400)
        return f"{days}d atrás"

# === MODERN COMPONENTS ===

class ModernButton(ctk.CTkButton):
    """Botão moderno com efeitos"""
    def __init__(self, parent, text, icon="", command=None, style="primary", **kwargs):
        colors = {
            "primary": (ACCENT_BLUE, "#6366f1"),
            "success": (ACCENT_GREEN, "#34d399"),
            "danger": (ACCENT_RED, "#f87171"),
            "secondary": (BG_CARD, HOVER_COLOR)
        }
        
        fg_color, hover = colors.get(style, colors["primary"])
        
        display_text = f"{icon} {text}" if icon else text
        
        # Configurações padrão
        default_config = {
            "text": display_text,
            "command": command,
            "fg_color": fg_color,
            "hover_color": hover,
            "corner_radius": 12,
            "height": 45,
            "font": ctk.CTkFont(size=14, weight="bold")
        }
        
        # Mesclar com kwargs (kwargs tem prioridade)
        default_config.update(kwargs)
        
        super().__init__(parent, **default_config)

class ModernCard(ctk.CTkFrame):
    """Card moderno com sombra simulada"""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color=BORDER_COLOR,
            **kwargs
        )

class VideoCard(ModernCard):
    """Card de vídeo com preview e informações"""
    def __init__(self, parent, video_data, on_select=None, on_remove=None, app=None):
        super().__init__(parent)
        self.video = video_data
        self.selected = tk.BooleanVar(value=False)
        self.on_select = on_select
        self.app = app
        
        # Container principal
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Checkbox de seleção
        self.checkbox = ctk.CTkCheckBox(
            container,
            text="",
            variable=self.selected,
            width=24,
            height=24,
            checkbox_width=24,
            checkbox_height=24,
            corner_radius=6,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_PURPLE,
            command=lambda: on_select() if on_select else None
        )
        self.checkbox.pack(side="left", padx=(0, 15))
        
        # Ícone de mídia baseado na extensão
        filename = video_data.get("filename", "").lower()
        media_icon = "🎬" # Default Reels
        if filename.endswith(".zip") or "[CARROSSEL]" in video_data.get("filename", ""):
            media_icon = "🎠"
        elif filename.endswith((".jpg", ".jpeg", ".png")):
            media_icon = "🖼️"
            
        folder_name = video_data.get("account") or video_data.get("folder")
        folder_color = get_folder_color(folder_name) if folder_name else BG_SECONDARY
        
        icon_frame = ctk.CTkFrame(container, width=42, height=42, corner_radius=10, fg_color=folder_color)
        icon_frame.pack(side="left", padx=(0, 15))
        icon_frame.pack_propagate(False)
        
        icon_label = ctk.CTkLabel(icon_frame, text=media_icon, font=ctk.CTkFont(size=20))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Informações do vídeo
        info_frame = ctk.CTkFrame(container, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        # Nome do arquivo
        name = video_data.get("filename", "video.mp4")
        if len(name) > 40:
            name = name[:37] + "..."
        
        name_label = ctk.CTkLabel(
            info_frame,
            text=name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        )
        name_label.pack(anchor="w", pady=(0, 5))
        
        # Origem e pasta
        origin_parts = []
        if video_data.get("gdrive_id"):
            origin_parts.append("☁️ Google Drive")
        else:
            origin_parts.append("💻 Local")
        
        if folder_name:
            origin_parts.append(f"📁 {folder_name}")
        
        status_label = ctk.CTkLabel(
            info_frame,
            text=" • ".join(origin_parts),
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        status_label.pack(anchor="w")
        
        # Status de postagem (direita)
        status_frame = ctk.CTkFrame(container, fg_color="transparent")
        status_frame.pack(side="right", padx=(15, 0))
        
        # Verificar se foi postado
        if app:
            video_id = video_data.get("gdrive_id")
            video_name = video_data.get("filename")
            
            # Verificar no histórico
            posted = None
            for h in app.history:
                if (video_id and h.get("id") == video_id) or (h.get("filename") == video_name):
                    posted = h
                    break
            
            # Verificar se está agendado
            scheduled = None
            for s in app.schedule:
                if (video_id and s.get("gdrive_id") == video_id) or (s.get("filename") == video_name):
                    scheduled = s
                    break
            
            if posted:
                # Postado
                post_time = posted.get("post_time", 0)
                time_ago = format_time_ago(post_time)
                dt = datetime.datetime.fromtimestamp(post_time)
                
                status_badge = ctk.CTkFrame(status_frame, fg_color=ACCENT_GREEN, corner_radius=8)
                status_badge.pack()
                
                ctk.CTkLabel(
                    status_badge,
                    text=f"✅ Postado",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="white"
                ).pack(padx=10, pady=5)
                
                ctk.CTkLabel(
                    status_frame,
                    text=f"{dt.strftime('%d/%m %H:%M')} ({time_ago})",
                    font=ctk.CTkFont(size=10),
                    text_color=TEXT_DIM
                ).pack(pady=(2, 0))
                
            elif scheduled:
                # Agendado
                sched_time = scheduled["schedule_time"]
                if isinstance(sched_time, int):
                    sched_time = datetime.datetime.fromtimestamp(sched_time)
                
                status_badge = ctk.CTkFrame(status_frame, fg_color=ACCENT_PURPLE, corner_radius=8)
                status_badge.pack()
                
                ctk.CTkLabel(
                    status_badge,
                    text=f"⏰ Agendado",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="white"
                ).pack(padx=10, pady=5)
                
                ctk.CTkLabel(
                    status_frame,
                    text=sched_time.strftime('%d/%m %H:%M'),
                    font=ctk.CTkFont(size=10),
                    text_color=TEXT_DIM
                ).pack(pady=(2, 0))
            else:
                # Não postado
                status_badge = ctk.CTkFrame(status_frame, fg_color=BG_SECONDARY, corner_radius=8)
                status_badge.pack()
                
                ctk.CTkLabel(
                    status_badge,
                    text=f"📭 Pendente",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=TEXT_DIM
                ).pack(padx=10, pady=5)
        
        # Botão de remover
        if on_remove:
            remove_btn = ctk.CTkButton(
                container,
                text="🗑️",
                width=35,
                height=35,
                corner_radius=10,
                fg_color="transparent",
                hover_color=ACCENT_RED,
                command=on_remove
            )
            remove_btn.pack(side="right")

class ScheduleCard(ModernCard):
    """Card de agendamento"""
    def __init__(self, parent, schedule_data, on_edit=None, on_remove=None):
        super().__init__(parent)
        self.schedule = schedule_data
        
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=8)
        
        # Data e hora
        dt = schedule_data["schedule_time"]
        if isinstance(dt, int):
            dt = datetime.datetime.fromtimestamp(dt)
        
        # Lado esquerdo: Data/Hora
        left_frame = ctk.CTkFrame(container, fg_color=BG_SECONDARY, corner_radius=12, width=85)
        left_frame.pack(side="left", padx=(0, 15))
        left_frame.pack_propagate(False)
        
        date_label = ctk.CTkLabel(
            left_frame,
            text=dt.strftime("%d\n%b").upper(),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=ACCENT_BLUE
        )
        date_label.pack(pady=10)
        
        time_label = ctk.CTkLabel(
            left_frame,
            text=dt.strftime("%H:%M"),
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY
        )
        time_label.pack(pady=(0, 10))
        
        # Centro: Informações
        center_frame = ctk.CTkFrame(container, fg_color="transparent")
        center_frame.pack(side="left", fill="both", expand=True)
        
        filename = schedule_data.get("filename", "video.mp4")
        if len(filename) > 35:
            filename = filename[:32] + "..."
        
        ctk.CTkLabel(
            center_frame,
            text=filename,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(anchor="w", pady=(0, 5))
        
        # Contas
        accounts = schedule_data.get("accounts", [])
        if accounts:
            acc_text = f"📱 {len(accounts)} conta(s): " + ", ".join([a.get("name", "?")[:15] for a in accounts[:2]])
            if len(accounts) > 2:
                acc_text += f" +{len(accounts)-2}"
            
            ctk.CTkLabel(
                center_frame,
                text=acc_text,
                font=ctk.CTkFont(size=11),
                text_color=TEXT_SECONDARY,
                anchor="w"
            ).pack(anchor="w")
        
        # Direita: Ações
        actions_frame = ctk.CTkFrame(container, fg_color="transparent")
        actions_frame.pack(side="right")
        
        if on_edit:
            ctk.CTkButton(
                actions_frame,
                text="✏️",
                width=35,
                height=35,
                corner_radius=10,
                fg_color="transparent",
                hover_color=HOVER_COLOR,
                command=on_edit
            ).pack(side="left", padx=2)
        
        if on_remove:
            ctk.CTkButton(
                actions_frame,
                text="🗑️",
                width=35,
                height=35,
                corner_radius=10,
                fg_color=ACCENT_RED,
                hover_color="#dc2626",
                command=on_remove
            ).pack(side="left", padx=2)

class StatCard(ModernCard):
    """Card de estatística"""
    def __init__(self, parent, title, value, icon, color=ACCENT_BLUE):
        super().__init__(parent)
        
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Ícone
        icon_label = ctk.CTkLabel(
            container,
            text=icon,
            font=ctk.CTkFont(size=32),
            text_color=color
        )
        icon_label.pack(pady=(0, 10))
        
        # Valor
        self.value_label = ctk.CTkLabel(
            container,
            text=str(value),
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.value_label.pack()
        
        # Título
        ctk.CTkLabel(
            container,
            text=title,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY
        ).pack(pady=(5, 0))
    
    def update_value(self, value):
        self.value_label.configure(text=str(value))

class ModernCalendar(ModernCard):
    """Calendário moderno e interativo"""
    def __init__(self, parent, on_date_select=None, get_highlights=None):
        super().__init__(parent)
        
        self.on_date_select = on_date_select
        self.get_highlights = get_highlights
        self.selected_dates = []
        
        now = datetime.datetime.now()
        self.current_month = now.month
        self.current_year = now.year
        
        self._build_ui()
        self.update_calendar()
    
    def _build_ui(self):
        # Header com navegação
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        self.prev_btn = ctk.CTkButton(
            header,
            text="◀",
            width=40,
            height=40,
            corner_radius=10,
            fg_color=BG_SECONDARY,
            hover_color=HOVER_COLOR,
            command=self.prev_month
        )
        self.prev_btn.pack(side="left")
        
        self.month_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.month_label.pack(side="left", expand=True)
        
        self.next_btn = ctk.CTkButton(
            header,
            text="▶",
            width=40,
            height=40,
            corner_radius=10,
            fg_color=BG_SECONDARY,
            hover_color=HOVER_COLOR,
            command=self.next_month
        )
        self.next_btn.pack(side="right")
        
        # Grid do calendário
        cal_grid = ctk.CTkFrame(self, fg_color="transparent")
        cal_grid.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Dias da semana
        days = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        for i, day in enumerate(days):
            ctk.CTkLabel(
                cal_grid,
                text=day,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=TEXT_DIM
            ).grid(row=0, column=i, pady=10, sticky="nsew")
        
        # Botões dos dias
        self.day_buttons = []
        self.day_badges = []
        for row in range(1, 7):
            for col in range(7):
                # Frame para conter o botão e o badge
                day_frame = ctk.CTkFrame(cal_grid, fg_color="transparent")
                day_frame.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
                
                btn = ctk.CTkButton(
                    day_frame,
                    text="",
                    width=45,
                    height=45,
                    corner_radius=10,
                    fg_color="transparent",
                    hover_color=HOVER_COLOR,
                    font=ctk.CTkFont(size=13),
                    command=lambda r=row, c=col: self._on_day_click(r, c)
                )
                btn.pack(fill="both", expand=True)
                
                # Badge (inicialmente escondido)
                badge = ctk.CTkLabel(
                    day_frame,
                    text="",
                    width=18,
                    height=18,
                    corner_radius=9,
                    fg_color="#1e3a8a", # Azul escuro
                    text_color="white",
                    font=ctk.CTkFont(size=9, weight="bold")
                )
                
                self.day_buttons.append(btn)
                self.day_badges.append(badge)
        
        # Configurar grid
        for i in range(7):
            cal_grid.grid_columnconfigure(i, weight=1)
        for i in range(1, 7):
            cal_grid.grid_rowconfigure(i, weight=1)
    
    def _on_day_click(self, row, col):
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        day = cal[row-1][col]
        
        if day == 0:
            return
        
        date = datetime.date(self.current_year, self.current_month, day)
        
        if date in self.selected_dates:
            self.selected_dates.remove(date)
        else:
            self.selected_dates.append(date)
        
        self.update_calendar()
        
        if self.on_date_select:
            self.on_date_select(self.selected_dates)
    
    def update_calendar(self):
        months_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        self.month_label.configure(
            text=f"{months_pt[self.current_month-1]} {self.current_year}"
        )
        
        cal = calendar.monthcalendar(self.current_year, self.current_month)
        highlights = self.get_highlights() if self.get_highlights else {}
        today = datetime.date.today()
        
        for idx, btn in enumerate(self.day_buttons):
            badge = self.day_badges[idx]
            row, col = idx // 7, idx % 7
            
            # Reset badge
            badge.place_forget()
            
            if row < len(cal):
                day = cal[row][col]
                
                if day == 0:
                    btn.configure(
                        text="",
                        state="disabled",
                        fg_color="transparent",
                        border_width=0
                    )
                else:
                    date = datetime.date(self.current_year, self.current_month, day)
                    date_str = date.strftime("%d/%m/%Y")
                    
                    # Configuração padrão
                    btn.configure(
                        text=str(day),
                        state="normal",
                        fg_color=BG_SECONDARY,
                        border_width=0,
                        text_color=TEXT_PRIMARY,
                        font=ctk.CTkFont(size=13)
                    )
                    
                    # Hoje
                    if date == today:
                        btn.configure(border_width=2, border_color=ACCENT_BLUE)
                    
                    # Selecionado
                    if date in self.selected_dates:
                        btn.configure(fg_color=ACCENT_BLUE, text_color="white")
                    
                    # Com agendamentos - mostrar badge
                    if date_str in highlights:
                        count = highlights[date_str].get("total", 0)
                        if count > 0:
                            # Mudar cor de fundo se tiver agendamentos
                            if date not in self.selected_dates:
                                btn.configure(fg_color=ACCENT_PURPLE)
                            
                            # Mostrar badge no canto superior direito
                            badge_text = str(count) if count < 10 else "+"
                            badge.configure(text=badge_text)
                            badge.place(relx=1.0, rely=0.0, anchor="ne", x=-2, y=2)
    
    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.update_calendar()
    
    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.update_calendar()


# === QUICK SCHEDULE WIZARD ===

class QuickScheduleWizard(ctk.CTkToplevel):
    """Assistente rápido e intuitivo de agendamento"""
    def __init__(self, parent, videos, selected_dates):
        super().__init__(parent)
        
        self.app = parent
        self.videos = videos
        self.selected_dates = sorted(selected_dates)
        self.result = None
        
        # Configuração da janela
        self.title("✨ Agendar Postagens")
        self.geometry("700x800")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.configure(fg_color=BG_PRIMARY)
        
        self._build_ui()
    
    def _build_ui(self):
        # Container principal com scroll
        main_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        main_scroll.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Título
        ctk.CTkLabel(
            main_scroll,
            text="✨ Configurar Agendamento",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(pady=(0, 10))
        
        ctk.CTkLabel(
            main_scroll,
            text=f"{len(self.videos)} vídeos • {len(self.selected_dates)} dias selecionados",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECONDARY
        ).pack(pady=(0, 30))
        
        # === SEÇÃO 1: CONTAS ===
        self._create_section(main_scroll, "1️⃣ Onde Publicar?", "Selecione as contas")
        
        accounts_card = ModernCard(main_scroll)
        accounts_card.pack(fill="x", pady=(0, 30))
        
        accounts_container = ctk.CTkFrame(accounts_card, fg_color="transparent")
        accounts_container.pack(fill="x", padx=20, pady=20)
        
        if not self.app.accounts:
            ctk.CTkLabel(
                accounts_container,
                text="⚠️ Nenhuma conta configurada",
                text_color=ACCENT_ORANGE
            ).pack(pady=20)
        else:
            for acc in self.app.accounts:
                acc_frame = ctk.CTkFrame(accounts_container, fg_color=BG_SECONDARY, corner_radius=10)
                acc_frame.pack(fill="x", pady=5)
                
                var = self.app.acc_vars.get(acc['name'], tk.BooleanVar(value=False))
                
                cb = ctk.CTkCheckBox(
                    acc_frame,
                    text=f"  {acc['name']}",
                    variable=var,
                    font=ctk.CTkFont(size=14),
                    fg_color=ACCENT_BLUE,
                    hover_color=ACCENT_PURPLE
                )
                cb.pack(side="left", padx=15, pady=12)
        
        # === SEÇÃO 2: HORÁRIOS ===
        self._create_section(main_scroll, "2️⃣ Quando Publicar?", "Configure os horários")
        
        timing_card = ModernCard(main_scroll)
        timing_card.pack(fill="x", pady=(0, 30))
        
        timing_container = ctk.CTkFrame(timing_card, fg_color="transparent")
        timing_container.pack(fill="x", padx=20, pady=20)
        
        # Horário de início
        ctk.CTkLabel(
            timing_container,
            text="⏰ Horário de Início",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(anchor="w", pady=(0, 10))
        
        time_frame = ctk.CTkFrame(timing_container, fg_color="transparent", corner_radius=10)
        time_frame.pack(pady=(0, 20))
        
        self.hour_var = tk.IntVar(value=9)
        self.min_var = tk.IntVar(value=0)
        
        # Container dos seletores
        time_selector = ctk.CTkFrame(time_frame, fg_color="transparent")
        time_selector.pack()
        
        # Seletor de Hora
        hour_container = ctk.CTkFrame(time_selector, fg_color=BG_SECONDARY, corner_radius=15, width=120, height=140)
        hour_container.pack(side="left", padx=10)
        hour_container.pack_propagate(False)
        
        # Botão incrementar hora
        ctk.CTkButton(
            hour_container,
            text="▲",
            width=100,
            height=35,
            corner_radius=10,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_PURPLE,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: self._increment_time(self.hour_var, 23)
        ).pack(pady=(10, 5))
        
        # Display da hora
        self.hour_display = ctk.CTkLabel(
            hour_container,
            text="09",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=BG_CARD,
            corner_radius=10,
            width=100,
            height=50
        )
        self.hour_display.pack(pady=5)
        
        # Botão decrementar hora
        ctk.CTkButton(
            hour_container,
            text="▼",
            width=100,
            height=35,
            corner_radius=10,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_PURPLE,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: self._decrement_time(self.hour_var, 23)
        ).pack(pady=(5, 10))
        
        # Separador ":"
        ctk.CTkLabel(
            time_selector,
            text=":",
            font=ctk.CTkFont(size=40, weight="bold"),
            text_color=TEXT_SECONDARY
        ).pack(side="left", padx=5)
        
        # Seletor de Minuto
        min_container = ctk.CTkFrame(time_selector, fg_color=BG_SECONDARY, corner_radius=15, width=120, height=140)
        min_container.pack(side="left", padx=10)
        min_container.pack_propagate(False)
        
        # Botão incrementar minuto
        ctk.CTkButton(
            min_container,
            text="▲",
            width=100,
            height=35,
            corner_radius=10,
            fg_color=ACCENT_PURPLE,
            hover_color=ACCENT_BLUE,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: self._increment_time(self.min_var, 59)
        ).pack(pady=(10, 5))
        
        # Display do minuto
        self.min_display = ctk.CTkLabel(
            min_container,
            text="00",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=BG_CARD,
            corner_radius=10,
            width=100,
            height=50
        )
        self.min_display.pack(pady=5)
        
        # Botão decrementar minuto
        ctk.CTkButton(
            min_container,
            text="▼",
            width=100,
            height=35,
            corner_radius=10,
            fg_color=ACCENT_PURPLE,
            hover_color=ACCENT_BLUE,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=lambda: self._decrement_time(self.min_var, 59)
        ).pack(pady=(5, 10))
        
        # Atualizar displays quando as variáveis mudarem
        self.hour_var.trace_add("write", lambda *_: self.hour_display.configure(text=f"{self.hour_var.get():02d}"))
        self.min_var.trace_add("write", lambda *_: self.min_display.configure(text=f"{self.min_var.get():02d}"))
        
        # Distribuição
        ctk.CTkLabel(
            timing_container,
            text="📊 Distribuição dos Vídeos",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(anchor="w", pady=(20, 10))
        
        dist_frame = ctk.CTkFrame(timing_container, fg_color=BG_SECONDARY, corner_radius=10)
        dist_frame.pack(fill="x")
        
        dist_inner = ctk.CTkFrame(dist_frame, fg_color="transparent")
        dist_inner.pack(fill="x", padx=20, pady=15)
        
        self.posts_per_day = tk.IntVar(value=1)
        self.interval_hours = tk.IntVar(value=1)
        
        # Posts por dia
        ctk.CTkLabel(
            dist_inner,
            text="Vídeos por dia:",
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 5))
        
        ppd_frame = ctk.CTkFrame(dist_inner, fg_color="transparent")
        ppd_frame.pack(fill="x", pady=(0, 15))
        
        self.ppd_slider = ctk.CTkSlider(
            ppd_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            variable=self.posts_per_day,
            progress_color=ACCENT_GREEN,
            button_color=ACCENT_BLUE,
            button_hover_color=ACCENT_PURPLE
        )
        self.ppd_slider.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.ppd_label = ctk.CTkLabel(
            ppd_frame,
            text="1",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=ACCENT_GREEN,
            width=40
        )
        self.ppd_label.pack(side="right")
        
        self.posts_per_day.trace_add("write", lambda *_: self.ppd_label.configure(text=str(self.posts_per_day.get())))
        
        # Intervalo
        ctk.CTkLabel(
            dist_inner,
            text="Intervalo entre posts:",
            text_color=TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 5))
        
        int_frame = ctk.CTkFrame(dist_inner, fg_color="transparent")
        int_frame.pack(fill="x")
        
        self.int_slider = ctk.CTkSlider(
            int_frame,
            from_=1,
            to=12,
            number_of_steps=11,
            variable=self.interval_hours,
            progress_color=ACCENT_GREEN,
            button_color=ACCENT_BLUE,
            button_hover_color=ACCENT_PURPLE
        )
        self.int_slider.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.int_label = ctk.CTkLabel(
            int_frame,
            text="1h",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=ACCENT_GREEN,
            width=40
        )
        self.int_label.pack(side="right")
        
        self.interval_hours.trace_add("write", lambda *_: self.int_label.configure(text=f"{self.interval_hours.get()}h"))
        
        # === SEÇÃO 3: LEGENDA ===
        self._create_section(main_scroll, "3️⃣ Legenda", "Configure o texto das postagens")
        
        caption_card = ModernCard(main_scroll)
        caption_card.pack(fill="x", pady=(0, 30))
        
        caption_container = ctk.CTkFrame(caption_card, fg_color="transparent")
        caption_container.pack(fill="x", padx=20, pady=20)
        
        self.caption_mode = tk.StringVar(value="default")
        
        mode_frame = ctk.CTkFrame(caption_container, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkRadioButton(
            mode_frame,
            text="Usar nome do arquivo como título",
            variable=self.caption_mode,
            value="title",
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_PURPLE
        ).pack(anchor="w", pady=5)
        
        ctk.CTkRadioButton(
            mode_frame,
            text="Usar legenda personalizada",
            variable=self.caption_mode,
            value="default",
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_PURPLE
        ).pack(anchor="w", pady=5)
        
        self.caption_text = ctk.CTkTextbox(
            caption_container,
            height=120,
            corner_radius=10,
            fg_color=BG_SECONDARY,
            border_width=1,
            border_color=BORDER_COLOR,
            font=ctk.CTkFont(size=13)
        )
        self.caption_text.pack(fill="x")
        self.caption_text.insert("1.0", self.app.settings.get("default_caption", ""))
        
        # === PREVIEW ===
        self._create_section(main_scroll, "📋 Resumo", "Confira antes de agendar")
        
        preview_card = ModernCard(main_scroll)
        preview_card.pack(fill="x", pady=(0, 20))
        
        preview_container = ctk.CTkFrame(preview_card, fg_color="transparent")
        preview_container.pack(fill="x", padx=20, pady=20)
        
        self.preview_label = ctk.CTkLabel(
            preview_container,
            text=self._generate_preview(),
            font=ctk.CTkFont(size=13),
            text_color=TEXT_SECONDARY,
            justify="left",
            anchor="w"
        )
        self.preview_label.pack(fill="x")
        
        # Atualizar preview quando mudar valores
        self.posts_per_day.trace_add("write", lambda *_: self.preview_label.configure(text=self._generate_preview()))
        self.interval_hours.trace_add("write", lambda *_: self.preview_label.configure(text=self._generate_preview()))
        
        # === BOTÕES ===
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(0, 30))
        
        ModernButton(
            btn_frame,
            text="Cancelar",
            style="secondary",
            command=self.destroy,
            width=150
        ).pack(side="left")
        
        ModernButton(
            btn_frame,
            text="Agendar Tudo",
            icon="🚀",
            style="primary",
            command=self._confirm,
            width=200
        ).pack(side="right")
    
    def _create_section(self, parent, title, subtitle):
        """Cria um cabeçalho de seção"""
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            section_frame,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            section_frame,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
            anchor="w"
        ).pack(anchor="w")
    
    def _increment_time(self, var, max_val):
        """Incrementa o valor do tempo (hora ou minuto)"""
        current = var.get()
        var.set((current + 1) % (max_val + 1))
    
    def _decrement_time(self, var, max_val):
        """Decrementa o valor do tempo (hora ou minuto)"""
        current = var.get()
        var.set((current - 1) % (max_val + 1))
    
    def _generate_preview(self):
        """Gera texto de preview do agendamento"""
        total_posts = len(self.videos)
        days = len(self.selected_dates)
        ppd = self.posts_per_day.get()
        
        preview = f"📦 {total_posts} vídeos serão distribuídos em {days} dia(s)\n"
        preview += f"📊 Até {ppd} vídeos por dia, com intervalo de {self.interval_hours.get()}h\n"
        preview += f"⏰ Primeiro post: {self.selected_dates[0].strftime('%d/%m/%Y')} às {self.hour_var.get():02d}:{self.min_var.get():02d}"
        
        return preview
    
    def _confirm(self):
        """Confirma e retorna os dados"""
        selected_accounts = [acc for acc in self.app.accounts if self.app.acc_vars[acc['name']].get()]
        
        if not selected_accounts:
            messagebox.showwarning("Atenção", "Selecione pelo menos uma conta!")
            return
        
        self.result = {
            "accounts": selected_accounts,
            "start_hour": self.hour_var.get(),
            "start_min": self.min_var.get(),
            "posts_per_day": self.posts_per_day.get(),
            "interval_hours": self.interval_hours.get(),
            "caption_mode": self.caption_mode.get(),
            "default_caption": self.caption_text.get("1.0", "end").strip()
        }
        
        # Salvar legenda padrão
        self.app.settings["default_caption"] = self.result["default_caption"]
        self.app.save_settings()
        
        self.destroy()


# === MAIN VIEWS ===

class DashboardView(ctk.CTkFrame):
    """Dashboard principal com estatísticas"""
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 30))
        
        ctk.CTkLabel(
            header,
            text="📊 Dashboard",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")
        
        # Stats cards
        stats_container = ctk.CTkFrame(self, fg_color="transparent")
        stats_container.pack(fill="x", pady=(0, 30))
        
        self.stat_videos = StatCard(stats_container, "Vídeos", len(app.videos), "🎬", ACCENT_BLUE)
        self.stat_videos.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        self.stat_scheduled = StatCard(stats_container, "Agendados", len(app.schedule), "⏰", ACCENT_PURPLE)
        self.stat_scheduled.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        self.stat_posted = StatCard(stats_container, "Postados", len(app.history), "✅", ACCENT_GREEN)
        self.stat_posted.pack(side="left", fill="both", expand=True)
        
        # Próximos agendamentos
        ctk.CTkLabel(
            self,
            text="📅 Próximas Postagens",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 15))
        
        self.upcoming_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            height=400
        )
        self.upcoming_scroll.pack(fill="both", expand=True)
        
        self.refresh()
    
    def refresh(self):
        # Atualizar stats
        self.stat_videos.update_value(len(self.app.videos))
        self.stat_scheduled.update_value(len(self.app.schedule))
        self.stat_posted.update_value(len(self.app.history))
        
        # Limpar e recriar lista
        for widget in self.upcoming_scroll.winfo_children():
            widget.destroy()
        
        if not self.app.schedule:
            empty_card = ModernCard(self.upcoming_scroll)
            empty_card.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                empty_card,
                text="📭 Nenhum agendamento pendente",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_DIM
            ).pack(pady=40)
            return
        
        # Mostrar próximos 10
        sorted_schedule = sorted(self.app.schedule, key=lambda x: x["schedule_time"])[:10]
        
        for item in sorted_schedule:
            card = ScheduleCard(
                self.upcoming_scroll,
                item,
                on_edit=lambda s=item: self.app.edit_schedule(s),
                on_remove=lambda s=item: self.app.remove_schedule(s)
            )
            card.pack(fill="x", pady=5)

class LibraryView(ctk.CTkFrame):
    """Biblioteca de vídeos"""
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.page = 0
        self.per_page = 20
        
        # Header com ações
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        left_header = ctk.CTkFrame(header, fg_color="transparent")
        left_header.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(
            left_header,
            text="📚 Biblioteca",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")
        
        self.count_label = ctk.CTkLabel(
            left_header,
            text=f"{len(app.videos)} vídeos",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECONDARY
        )
        self.count_label.pack(side="left", padx=20)
        
        # Botões de ação
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="right")
        
        ModernButton(
            actions,
            text="Adicionar",
            icon="➕",
            style="secondary",
            command=app.add_videos,
            width=140
        ).pack(side="left", padx=5)
        
        ModernButton(
            actions,
            text="Do Drive",
            icon="☁️",
            style="secondary",
            command=lambda: app.pull_from_drive("Geral"),
            width=140
        ).pack(side="left", padx=5)
        
        ModernButton(
            actions,
            text="Postar Agora",
            icon="🚀",
            style="success",
            command=app.post_now,
            width=150
        ).pack(side="left", padx=5)
        
        # Barra de busca e filtros
        search_frame = ModernCard(self)
        search_frame.pack(fill="x", pady=(0, 20))
        
        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(fill="x", padx=20, pady=15)
        
        self.search_entry = ctk.CTkEntry(
            search_inner,
            placeholder_text="🔍 Buscar vídeos...",
            height=40,
            corner_radius=10,
            border_width=0,
            fg_color=BG_SECONDARY
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.search_entry.bind("<KeyRelease>", lambda e: self.reset_search())
        
        ModernButton(
            search_inner,
            text="Selecionar Todos",
            style="secondary",
            command=app.select_all_library,
            width=150
        ).pack(side="left", padx=5)
        
        ModernButton(
            search_inner,
            text="Limpar",
            style="danger",
            command=app.clear_library,
            width=100
        ).pack(side="left")
        
        # Lista de vídeos
        self.videos_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.videos_scroll.pack(fill="both", expand=True)
        
        # Paginação
        self.pagination_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pagination_frame.pack(fill="x", pady=(10, 0))
        
        self.prev_btn = ModernButton(
            self.pagination_frame, 
            text="Anterior", 
            command=self.prev_page,
            width=120,
            height=35,
            style="secondary"
        )
        self.prev_btn.pack(side="left")
        
        self.page_label = ctk.CTkLabel(
            self.pagination_frame,
            text="Página 1",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.page_label.pack(side="left", expand=True)
        
        self.next_btn = ModernButton(
            self.pagination_frame, 
            text="Próximo", 
            command=self.next_page,
            width=120,
            height=35,
            style="secondary"
        )
        self.next_btn.pack(side="right")
        
        self.refresh()
    
    def reset_search(self):
        self.page = 0
        self.refresh()
        
    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.refresh()
            
    def next_page(self):
        self.page += 1
        self.refresh()
    
    def refresh(self):
        self.count_label.configure(text=f"{len(self.app.videos)} vídeos")
        
        # Limpar lista
        for widget in self.videos_scroll.winfo_children():
            widget.destroy()
        
        # Filtrar por busca
        search_term = self.search_entry.get().lower()
        filtered_videos = [
            v for v in self.app.videos
            if search_term in v.get("filename", "").lower()
        ]
        
        if not filtered_videos:
            self.pagination_frame.pack_forget()
            empty_card = ModernCard(self.videos_scroll)
            empty_card.pack(fill="x", pady=20)
            
            ctk.CTkLabel(
                empty_card,
                text="📭 Nenhum vídeo encontrado",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_DIM
            ).pack(pady=40)
            return
        
        self.pagination_frame.pack(fill="x", pady=(10, 0))
        
        # Lógica de Paginação
        total_pages = max(1, (len(filtered_videos) + self.per_page - 1) // self.per_page)
        if self.page >= total_pages: self.page = total_pages - 1
        
        start = self.page * self.per_page
        end = start + self.per_page
        page_items = filtered_videos[start:end]
        
        self.page_label.configure(text=f"Página {self.page + 1} de {total_pages}")
        self.prev_btn.configure(state="normal" if self.page > 0 else "disabled")
        self.next_btn.configure(state="normal" if end < len(filtered_videos) else "disabled")

        # Criar cards
        for video in page_items:
            card = VideoCard(
                self.videos_scroll,
                video,
                on_select=lambda: None,
                on_remove=lambda v=video: self.app.remove_from_library(v),
                app=self.app
            )
            card.pack(fill="x", pady=5)
            video["widget"] = card

class ScheduleView(ctk.CTkFrame):
    """View de agendamento com calendário"""
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.page = 0
        self.per_page = 15
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        left_header = ctk.CTkFrame(header, fg_color="transparent")
        left_header.pack(side="left")
        
        ctk.CTkLabel(
            left_header,
            text="📅 Agendar",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")
        
        self.count_label = ctk.CTkLabel(
            left_header,
            text=f"{len(app.schedule)} agendados",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_SECONDARY
        )
        self.count_label.pack(side="left", padx=20)
        
        # Botões do header
        buttons_frame = ctk.CTkFrame(header, fg_color="transparent")
        buttons_frame.pack(side="right")
        
        ModernButton(
            buttons_frame,
            text="Limpar Postados",
            icon="🧹",
            style="secondary",
            command=app.clean_posted_from_schedule,
            width=160
        ).pack(side="left", padx=(0, 10))
        
        ModernButton(
            buttons_frame,
            text="Ver no GitHub",
            icon="🌐",
            style="secondary",
            command=app.open_schedule_file,
            width=160
        ).pack(side="left", padx=(0, 10))
        
        ModernButton(
            buttons_frame,
            text="Publicar Agora",
            icon="🚀",
            style="primary",
            command=app.run_bot_now,
            width=160
        ).pack(side="left", padx=(0, 10))
        
        ModernButton(
            buttons_frame,
            text="Sincronizar",
            icon="☁️",
            style="success",
            command=app.sync_cloud,
            width=160
        ).pack(side="left")
        
        # Container principal
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)
        
        # Esquerda: Calendário
        left_panel = ctk.CTkFrame(main_container, fg_color="transparent")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        self.calendar = ModernCalendar(
            left_panel,
            on_date_select=self._on_date_select,
            get_highlights=app.get_highlights
        )
        self.calendar.pack(fill="both", expand=True)
        
        # Botão de agendar
        self.schedule_btn = ModernButton(
            left_panel,
            text="Agendar Vídeos Selecionados",
            icon="✨",
            style="primary",
            command=self._start_schedule,
            height=55
        )
        self.schedule_btn.pack(fill="x", pady=(15, 0))
        
        # Direita: Lista de agendamentos
        right_panel = ModernCard(main_container, width=400)
        right_panel.pack(side="right", fill="both")
        right_panel.pack_propagate(False)
        
        right_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        right_header.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            right_header,
            text="📋 Agendamentos",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")
        
        ModernButton(
            right_header,
            text="Limpar",
            style="danger",
            command=app.clear_schedule,
            width=80,
            height=35
        ).pack(side="right")
        
        self.schedule_scroll = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="transparent"
        )
        self.schedule_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Paginação
        self.pagination_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.pagination_frame.pack(fill="x", pady=(0, 10), padx=10)
        
        self.prev_btn = ModernButton(
            self.pagination_frame, 
            text="◀", 
            command=self.prev_page,
            width=40,
            height=35,
            style="secondary"
        )
        self.prev_btn.pack(side="left")
        
        self.page_label = ctk.CTkLabel(
            self.pagination_frame,
            text="Página 1",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.page_label.pack(side="left", expand=True)
        
        self.next_btn = ModernButton(
            self.pagination_frame, 
            text="▶", 
            command=self.next_page,
            width=40,
            height=35,
            style="secondary"
        )
        self.next_btn.pack(side="right")
        
        self.refresh()
    
    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.refresh()
            
    def next_page(self):
        self.page += 1
        self.refresh()
    
    def _on_date_select(self, dates):
        """Callback quando datas são selecionadas"""
        if dates:
            self.schedule_btn.configure(
                text=f"✨ Agendar para {len(dates)} dia(s)",
                state="normal"
            )
        else:
            self.schedule_btn.configure(
                text="Selecione dias no calendário",
                state="disabled"
            )
    
    def _start_schedule(self):
        """Inicia o assistente de agendamento"""
        selected_dates = self.calendar.selected_dates
        
        if not selected_dates:
            messagebox.showwarning("Atenção", "Selecione pelo menos um dia no calendário!")
            return
        
        # Pegar vídeos selecionados
        selected_videos = [
            v for v in self.app.videos
            if v.get("widget") and hasattr(v["widget"], "selected") and v["widget"].selected.get()
        ]
        
        if not selected_videos:
            messagebox.showwarning("Atenção", "Selecione vídeos na Biblioteca primeiro!")
            return
        
        # Abrir wizard
        wizard = QuickScheduleWizard(self.app, selected_videos, selected_dates)
        self.wait_window(wizard)
        
        if wizard.result:
            self.app.process_schedule(selected_videos, selected_dates, wizard.result)
    
    def refresh(self):
        self.count_label.configure(text=f"{len(self.app.schedule)} agendados")
        
        # Atualizar calendário
        self.calendar.update_calendar()
        
        # Limpar lista
        for widget in self.schedule_scroll.winfo_children():
            widget.destroy()
        
        if not self.app.schedule:
            ctk.CTkLabel(
                self.schedule_scroll,
                text="📭 Nenhum agendamento",
                font=ctk.CTkFont(size=13),
                text_color=TEXT_DIM
            ).pack(pady=40)
            return
        
        # Ordenar e mostrar
        sorted_schedule = sorted(self.app.schedule, key=lambda x: x["schedule_time"])
        
        # Lógica de Paginação
        total_pages = max(1, (len(sorted_schedule) + self.per_page - 1) // self.per_page)
        if self.page >= total_pages: self.page = total_pages - 1
        
        start = self.page * self.per_page
        end = start + self.per_page
        page_items = sorted_schedule[start:end]
        
        self.page_label.configure(text=f"Página {self.page + 1} de {total_pages}")
        self.prev_btn.configure(state="normal" if self.page > 0 else "disabled")
        self.next_btn.configure(state="normal" if end < len(sorted_schedule) else "disabled")
        
        for item in page_items:
            card = ScheduleCard(
                self.schedule_scroll,
                item,
                on_edit=lambda s=item: self.app.edit_schedule(s),
                on_remove=lambda s=item: self.app.remove_schedule(s)
            )
            card.pack(fill="x", pady=5)


class AccountsView(ctk.CTkFrame):
    """Gerenciamento de contas"""
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        # Header
        ctk.CTkLabel(
            self,
            text="👥 Contas",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 30))
        
        # Adicionar conta
        add_card = ModernCard(self)
        add_card.pack(fill="x", pady=(0, 30))
        
        add_container = ctk.CTkFrame(add_card, fg_color="transparent")
        add_container.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            add_container,
            text="➕ Adicionar Nova Conta",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 15))
        
        input_frame = ctk.CTkFrame(add_container, fg_color="transparent")
        input_frame.pack(fill="x")
        
        self.token_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Cole o Token de Acesso aqui...",
            height=45,
            corner_radius=10,
            border_width=0,
            fg_color=BG_SECONDARY
        )
        self.token_entry.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        ModernButton(
            input_frame,
            text="Adicionar",
            icon="✨",
            style="primary",
            command=self._add_account,
            width=150
        ).pack(side="left")
        
        # Lista de contas
        ctk.CTkLabel(
            self,
            text="Contas Configuradas",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 15))
        
        self.accounts_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.accounts_scroll.pack(fill="both", expand=True)
        
        self.refresh()
    
    def _add_account(self):
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showwarning("Atenção", "Cole um token de acesso!")
            return
        
        self.app.log("Analisando token...")
        threading.Thread(target=self._process_token, args=(token,), daemon=True).start()
    
    def _process_token(self, token):
        try:
            api = MetaAPI(access_token=token)
            long_token, expires = api.refresh_token(token)
            if long_token:
                token = long_token
            
            details = api.get_account_details(token)
            if not details:
                self.app.after(0, lambda: messagebox.showerror("Erro", "Nenhuma conta encontrada!"))
                return
            
            added = 0
            for det in details:
                # Permite adicionar se tiver IG OU se tiver FB Page ID (flexível)
                if det.get("ig_account_id") or det.get("fb_page_id"):
                    exists = any(a['fb_page_id'] == det['fb_page_id'] for a in self.app.accounts)
                    if not exists:
                        new_acc = {
                            "name": det["name"],
                            "ig_account_id": det["ig_account_id"],
                            "fb_page_id": det["fb_page_id"],
                            "access_token": det["access_token"],
                            "profile_pic": det.get("profile_pic"),
                            "token_expiry": int(time.time()) + (expires if expires else 5184000),
                            "last_renewed": int(time.time())
                        }
                        self.app.accounts.append(new_acc)
                        added += 1
            
            if added > 0:
                self.app.save_accounts()
                self.app.after(0, self.refresh)
                self.app.after(0, lambda: messagebox.showinfo("Sucesso", f"{added} conta(s) adicionada(s)!"))
                self.app.after(0, lambda: self.token_entry.delete(0, 'end'))
            else:
                self.app.after(0, lambda: messagebox.showwarning("Aviso", "Nenhuma conta nova encontrada."))
        except Exception as e:
            self.app.log(f"Erro: {e}")
            self.app.after(0, lambda: messagebox.showerror("Erro", str(e)))
    
    def refresh(self):
        for widget in self.accounts_scroll.winfo_children():
            widget.destroy()
        
        if not self.app.accounts:
            empty_card = ModernCard(self.accounts_scroll)
            empty_card.pack(fill="x", pady=20)
            
            ctk.CTkLabel(
                empty_card,
                text="📭 Nenhuma conta configurada",
                font=ctk.CTkFont(size=14),
                text_color=TEXT_DIM
            ).pack(pady=40)
            return
        
        for acc in self.app.accounts:
            card = ModernCard(self.accounts_scroll)
            card.pack(fill="x", pady=5)
            
            container = ctk.CTkFrame(card, fg_color="transparent")
            container.pack(fill="x", padx=20, pady=15)
            
            # Checkbox
            var = self.app.acc_vars.get(acc['name'], tk.BooleanVar(value=False))
            self.app.acc_vars[acc['name']] = var
            
            cb = ctk.CTkCheckBox(
                container,
                text="",
                variable=var,
                width=24,
                height=24,
                fg_color=ACCENT_BLUE,
                hover_color=ACCENT_PURPLE
            )
            cb.pack(side="left", padx=(0, 15))
            
            # Info
            info_frame = ctk.CTkFrame(container, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True)
            
            ctk.CTkLabel(
                info_frame,
                text=acc.get("name", "Sem nome"),
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=TEXT_PRIMARY,
                anchor="w"
            ).pack(anchor="w")
            
            details = f"IG: {acc.get('ig_account_id', 'N/A')[:15]}... • FB: {acc.get('fb_page_id', 'N/A')[:15]}..."
            ctk.CTkLabel(
                info_frame,
                text=details,
                font=ctk.CTkFont(size=11),
                text_color=TEXT_SECONDARY,
                anchor="w"
            ).pack(anchor="w")
            
            # Status do token
            expiry = acc.get("token_expiry", 0)
            days_left = (expiry - time.time()) / 86400
            
            if days_left < 0:
                status_text = "🔴 Expirado"
                status_color = ACCENT_RED
            elif days_left < 7:
                status_text = f"🟡 {int(days_left)}d restantes"
                status_color = ACCENT_ORANGE
            else:
                status_text = f"🟢 {int(days_left)}d restantes"
                status_color = ACCENT_GREEN
            
            ctk.CTkLabel(
                container,
                text=status_text,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=status_color
            ).pack(side="right", padx=10)

class SettingsView(ctk.CTkFrame):
    """Configurações"""
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        
        ctk.CTkLabel(
            self,
            text="⚙️ Configurações",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 30))
        
        # Legenda padrão
        caption_card = ModernCard(self)
        caption_card.pack(fill="x", pady=(0, 20))
        
        caption_container = ctk.CTkFrame(caption_card, fg_color="transparent")
        caption_container.pack(fill="x", padx=20, pady=20)
        
        header_frame = ctk.CTkFrame(caption_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            header_frame,
            text="📝 Legenda Padrão",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")
        
        self.char_counter = ctk.CTkLabel(
            header_frame,
            text="0 / 2200",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=TEXT_SECONDARY
        )
        self.char_counter.pack(side="right")
        
        self.caption_text = ctk.CTkTextbox(
            caption_container,
            height=150,
            corner_radius=10,
            fg_color=BG_SECONDARY,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.caption_text.pack(fill="x", pady=(0, 15))
        self.caption_text.insert("1.0", app.settings.get("default_caption", ""))
        self.caption_text.bind("<KeyRelease>", self._on_caption_keyup)
        self.app.after(100, self._on_caption_keyup) # Init counter
        
        ModernButton(
            caption_container,
            text="Salvar",
            icon="💾",
            style="primary",
            command=self._save_caption,
            width=120
        ).pack(anchor="e")
        
        # Links úteis
        links_card = ModernCard(self)
        links_card.pack(fill="x", pady=(0, 20))
        
        links_container = ctk.CTkFrame(links_card, fg_color="transparent")
        links_container.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            links_container,
            text="🔗 Links Rápidos",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(anchor="w", pady=(0, 15))
        
        links_grid = ctk.CTkFrame(links_container, fg_color="transparent")
        links_grid.pack(fill="x")
        
        ModernButton(
            links_grid,
            text="Google Drive",
            icon="📁",
            style="secondary",
            command=app.open_drive_browser,
            width=180
        ).pack(side="left", padx=(0, 10))
        
        ModernButton(
            links_grid,
            text="GitHub Actions",
            icon="👁️",
            style="secondary",
            command=app.open_github_actions,
            width=180
        ).pack(side="left", padx=(0, 10))
        
        ModernButton(
            links_grid,
            text="Ver Fila",
            icon="📋",
            style="secondary",
            command=app.open_schedule_file,
            width=180
        ).pack(side="left")
    
    def _on_caption_keyup(self, event=None):
        """Monitora o tamanho da legenda e limita a 2200 caracteres"""
        text = self.caption_text.get("1.0", "end-1c")
        count = len(text)
        
        if count > 2200:
            # Cortar o texto excedente
            self.caption_text.delete("1.0", "end")
            self.caption_text.insert("1.0", text[:2200])
            count = 2200
            self.char_counter.configure(text_color=ACCENT_RED)
        elif count > 2100:
            self.char_counter.configure(text_color=ACCENT_ORANGE)
        else:
            self.char_counter.configure(text_color=TEXT_SECONDARY)
            
        self.char_counter.configure(text=f"{count} / 2200")
        
    def _save_caption(self):
        caption = self.caption_text.get("1.0", "end-1c").strip()
        
        # Alerta se tiver muitas hashtags
        tag_count = caption.count('#')
        if tag_count > 30:
            messagebox.showwarning(
                "Muitas Hashtags",
                f"Sua legenda tem {tag_count} hashtags.\nO Instagram NÃO ACEITA mais de 30 hashtags!\n\nSeu robô cortará as excedentes automaticamente para evitar que a legenda inteira suma do Instagram."
            )
            
        self.app.settings["default_caption"] = caption
        self.app.save_settings()
        if tag_count <= 30:
            messagebox.showinfo("Sucesso", "Legenda salva com sucesso!")


# === MAIN APPLICATION ===

class MetaStudioApp(ctk.CTk):
    """Aplicação principal"""
    def __init__(self):
        super().__init__()
        
        # Configuração da janela
        self.title("Meta Studio Pro - Agendador de Reels")
        self.geometry("1600x900")
        
        # Carregar dados - ORDEM CORRIGIDA: histórico primeiro!
        self.settings = self.load_settings()
        self.accounts = self.load_accounts()
        self.history = self.load_history()     # <--- Essencial carregar histórico antes do schedule
        self.videos = self.load_library()
        self.schedule = self.load_schedule()    # <--- Agora load_schedule pode usar self.history com segurança
        
        self.acc_vars = {
            acc['name']: tk.BooleanVar(value=(acc['name'] in self.settings.get("last_used_accounts", [])))
            for acc in self.accounts
        }
        
        self.configure(fg_color=BG_PRIMARY)
        
        self._build_ui()
        
        # Auto-renovar tokens
        self.check_token_renewals()
    
    def _build_ui(self):
        # Sidebar
        sidebar = ctk.CTkFrame(
            self,
            width=250,
            fg_color=BG_SECONDARY,
            corner_radius=0
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Logo
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(pady=40)
        
        ctk.CTkLabel(
            logo_frame,
            text="✨",
            font=ctk.CTkFont(size=40)
        ).pack()
        
        ctk.CTkLabel(
            logo_frame,
            text="META STUDIO",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=ACCENT_BLUE
        ).pack(pady=(10, 0))
        
        ctk.CTkLabel(
            logo_frame,
            text="PRO",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM
        ).pack()
        
        # Menu de navegação
        nav_items = [
            ("dashboard", "📊", "Dashboard"),
            ("library", "📚", "Biblioteca"),
            ("schedule", "📅", "Agendar"),
            ("accounts", "👥", "Contas"),
            ("settings", "⚙️", "Configurações")
        ]
        
        self.nav_buttons = {}
        
        for view_id, icon, label in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=f"{icon}  {label}",
                height=50,
                corner_radius=12,
                fg_color="transparent",
                hover_color=HOVER_COLOR,
                anchor="w",
                font=ctk.CTkFont(size=15),
                command=lambda v=view_id: self.show_view(v)
            )
            btn.pack(fill="x", padx=15, pady=5)
            self.nav_buttons[view_id] = btn
        
        # Relógio atual
        clock_card = ctk.CTkFrame(
            sidebar,
            fg_color=BG_CARD,
            corner_radius=15
        )
        clock_card.pack(side="bottom", fill="x", padx=15, pady=(15, 10))
        
        clock_container = ctk.CTkFrame(clock_card, fg_color="transparent")
        clock_container.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            clock_container,
            text="🕐 HORÁRIO ATUAL",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT_GREEN
        ).pack()
        
        self.current_time_label = ctk.CTkLabel(
            clock_container,
            text="--:--:--",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=TEXT_PRIMARY
        )
        self.current_time_label.pack(pady=5)
        
        self.current_date_label = ctk.CTkLabel(
            clock_container,
            text="-- de ---- de ----",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_SECONDARY
        )
        self.current_date_label.pack()
        
        # Status da nuvem
        status_card = ctk.CTkFrame(
            sidebar,
            fg_color=BG_CARD,
            corner_radius=15
        )
        status_card.pack(side="bottom", fill="x", padx=15, pady=(10, 30))
        
        status_container = ctk.CTkFrame(status_card, fg_color="transparent")
        status_container.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            status_container,
            text="☁️ CÉREBRO CLOUD",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT_BLUE
        ).pack()
        
        ctk.CTkLabel(
            status_container,
            text="Próxima verificação:",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_DIM
        ).pack(pady=(5, 0))
        
        self.countdown_label = ctk.CTkLabel(
            status_container,
            text="--:--",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=ACCENT_GREEN
        )
        self.countdown_label.pack(pady=5)
        
        self.next_time_label = ctk.CTkLabel(
            status_container,
            text="às --:--",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_DIM
        )
        self.next_time_label.pack()
        
        # Separador
        ctk.CTkFrame(status_container, height=1, fg_color=BORDER_COLOR).pack(fill="x", pady=10)
        
        # Lista de próximos horários
        ctk.CTkLabel(
            status_container,
            text="Próximas verificações:",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEXT_DIM
        ).pack(pady=(0, 5))
        
        # Frame scrollable para os horários
        self.schedule_times_frame = ctk.CTkFrame(status_container, fg_color=BG_SECONDARY, corner_radius=8)
        self.schedule_times_frame.pack(fill="x")
        
        self.schedule_times_label = ctk.CTkLabel(
            self.schedule_times_frame,
            text="",
            font=ctk.CTkFont(size=8),
            text_color=TEXT_SECONDARY,
            justify="left"
        )
        self.schedule_times_label.pack(padx=8, pady=8)
        
        # Container principal
        self.main_container = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.main_container.pack(side="right", fill="both", expand=True)
        
        # Criar views
        self.views = {
            "dashboard": DashboardView(self.main_container, self),
            "library": LibraryView(self.main_container, self),
            "schedule": ScheduleView(self.main_container, self),
            "accounts": AccountsView(self.main_container, self),
            "settings": SettingsView(self.main_container, self)
        }
        
        # Mostrar dashboard
        self.show_view("dashboard")
        
        # Iniciar countdown
        self.update_countdown()
        
        # Buscar dados do GitHub ao iniciar (via HTTP, sem Git)
        self.after(1000, self.fetch_github_schedule)
    
    def show_view(self, view_id):
        """Mostra uma view específica"""
        # Esconder todas
        for view in self.views.values():
            view.pack_forget()
        
        # Mostrar selecionada
        self.views[view_id].pack(fill="both", expand=True, padx=40, pady=30)
        
        # Atualizar botões
        for vid, btn in self.nav_buttons.items():
            if vid == view_id:
                btn.configure(fg_color=ACCENT_BLUE, hover_color=ACCENT_PURPLE)
            else:
                btn.configure(fg_color="transparent", hover_color=HOVER_COLOR)
        
        # Refresh da view
        if hasattr(self.views[view_id], "refresh"):
            self.views[view_id].refresh()
    
    def update_countdown(self):
        """Atualiza o countdown do Cérebro Cloud e o relógio atual"""
        now = datetime.datetime.now()
        
        # Atualizar relógio atual
        months_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        self.current_time_label.configure(text=now.strftime("%H:%M:%S"))
        self.current_date_label.configure(
            text=f"{now.day} de {months_pt[now.month-1]} de {now.year}"
        )
        
        # O robô acorda nos minutos terminados em 2 e 7 (ex: 02, 07, 12...)
        # e geralmente por volta de 27-28 segundos após o início do minuto.
        target_minute_offset = 2
        target_second = 27
        
        # Próximo minuto que termina em 2 ou 7
        # k = (2 - M) % 5
        minutes_to_next = (target_minute_offset - now.minute) % 5
        
        # Se estamos no minuto do alvo, verificar se já passou o segundo do alvo
        if minutes_to_next == 0 and now.second >= target_second:
            minutes_to_next = 5
        
        # Calcular o próximo horário exato
        next_dt = now.replace(second=target_second, microsecond=0) + datetime.timedelta(minutes=minutes_to_next)
        
        # Calcular diferença em segundos
        diff = int((next_dt - now).total_seconds())
        if diff <= 0:
            diff = 5 * 60
            next_dt = next_dt + datetime.timedelta(minutes=5)
        
        # Atualizar countdown
        m, s = divmod(diff, 60)
        self.countdown_label.configure(text=f"{m:02d}:{s:02d}")
        self.next_time_label.configure(text=f"às {next_dt.strftime('%H:%M')}")
        
        # Calcular próximos 12 horários (seguindo o padrão 2/7)
        next_times = []
        current_time = next_dt
        for i in range(12):
            next_times.append(current_time.strftime('%H:%M'))
            current_time += datetime.timedelta(minutes=5)
        
        # Formatar em 3 colunas de 4 linhas
        times_text = ""
        for i in range(4):
            row = []
            for j in range(3):
                idx = i + (j * 4)
                if idx < len(next_times):
                    row.append(next_times[idx])
            times_text += "  ".join(row) + "\n"
        
        self.schedule_times_label.configure(text=times_text.strip())
        
        self.after(1000, self.update_countdown)
    
    def fetch_github_schedule(self):
        """Busca schedule_queue.json do GitHub via HTTP e faz merge inteligente"""
        self.log("=" * 60)
        self.log("🔍 VERIFICANDO GITHUB")
        self.log("=" * 60)
        
        def task():
            try:
                # URL do arquivo no GitHub
                url = "https://raw.githubusercontent.com/agenciaaguiacontact-sys/ig-fb-reels-bot/main/schedule_queue.json"
                
                # 1. Obter o histórico remoto para garantir que o merge identifique o que foi postado
                history_url = "https://raw.githubusercontent.com/agenciaaguiacontact-sys/ig-fb-reels-bot/main/posted_history.json"
                h_resp = requests.get(history_url, timeout=10)
                remote_history = None
                
                if h_resp.status_code == 200:
                    remote_history = json.loads(h_resp.text)
                else:
                    # Tentar via git show se HTTP falhar
                    show_h = subprocess.run(["git", "show", "origin/main:posted_history.json"], capture_output=True, text=True, shell=True, timeout=10)
                    if show_h.returncode == 0:
                        remote_history = json.loads(show_h.stdout)
                
                if remote_history:
                    self.history = self.merge_json_data('history', self.history, remote_history)
                    # Salvar histórico mesclado
                    with open("posted_history.json", "w", encoding="utf-8") as f:
                        json.dump(self.history[-500:], f, indent=2)

                # 2. Obter e mesclar o schedule
                self.log("📥 Buscando dados do GitHub via HTTP...")
                response = requests.get(url, timeout=10)
                
                # Se falhar via HTTP (especialmente 404 em repos privados), tentar via comando GIT
                github_schedule = None
                if response.status_code != 200:
                    self.log(f"⚠️ Erro HTTP {response.status_code}. Tentando via comando Git...")
                    
                    # Tentar buscar do remoto via git show (funciona se o git estiver logado no PC)
                    try:
                        # Primeiro garantir que o repo local sabe das novidades
                        subprocess.run(["git", "fetch", "origin", "main"], capture_output=True, text=True, shell=True, timeout=15)
                        
                        show_res = subprocess.run(["git", "show", "origin/main:schedule_queue.json"], capture_output=True, text=True, shell=True, timeout=10)
                        if show_res.returncode == 0:
                            github_schedule = json.loads(show_res.stdout)
                            self.log("✅ Dados obtidos via comando Git")
                        else:
                            self.log(f"❌ Falha no comando Git: {show_res.stderr}")
                    except Exception as ge:
                        self.log(f"❌ Erro ao tentar Git: {ge}")
                else:
                    try:
                        github_schedule = json.loads(response.text)
                    except json.JSONDecodeError:
                        self.log("⚠️ Erro ao ler JSON do GitHub")
                
                if github_schedule is None:
                    self.log("✅ Usando dados locais (sincronização remota falhou)")
                    return
                
                # Converter schedule local para comparison/merge
                local_schedule_data = []
                for s in self.schedule:
                    item = s.copy()
                    if isinstance(item["schedule_time"], datetime.datetime):
                        item["schedule_time"] = int(item["schedule_time"].timestamp())
                    local_schedule_data.append(item)
                
                self.log(f"📊 Local: {len(local_schedule_data)} agendamentos")
                self.log(f"📊 GitHub: {len(github_schedule)} agendamentos")
                
                # Fazer merge inteligente
                merged_schedule = self.merge_json_data('schedule', local_schedule_data, github_schedule)
                
                # Verificar se houve mudança real
                local_ids = set(item.get("gdrive_id") for item in local_schedule_data if item.get("gdrive_id"))
                merged_ids = set(item.get("gdrive_id") for item in merged_schedule if item.get("gdrive_id"))
                
                if local_ids == merged_ids and len(local_schedule_data) == len(merged_schedule):
                    self.log("✅ Dados locais e GitHub estão sincronizados")
                    return
                
                self.log(f"🔄 Sincronizado: {len(merged_schedule)} agendamentos totais")
                
                # Há diferenças - fazer merge
                self.log("🔄 Detectadas diferenças - fazendo merge...")
                
                # IDs que estão no local mas não no GitHub = foram postados
                posted_ids = local_ids - github_ids
                
                if posted_ids:
                    self.log(f"✅ {len(posted_ids)} vídeo(s) foram postados")
                    for vid_id in posted_ids:
                        # Encontrar o vídeo
                        for item in local_schedule_data:
                            if item.get("gdrive_id") == vid_id:
                                self.log(f"  ✓ Postado: {item.get('filename')}")
                                
                                # Adicionar ao histórico se não estiver
                                if not any(h.get("id") == vid_id for h in self.history):
                                    self.history.append({
                                        "id": vid_id,
                                        "filename": item.get("filename"),
                                        "post_time": int(time.time())
                                    })
                                break
                
                # Criar novo schedule: GitHub (verdade) + novos locais
                merged_schedule = []
                processed_ids = set()
                
                # 1. Adicionar TUDO do GitHub (é a verdade)
                for github_item in github_schedule:
                    gdrive_id = github_item.get("gdrive_id")
                    
                    # Verificar se já foi postado
                    is_posted = any(
                        h.get("id") == gdrive_id or h.get("filename") == github_item.get("filename")
                        for h in self.history
                    )
                    
                    if not is_posted:
                        merged_schedule.append(github_item)
                        if gdrive_id:
                            processed_ids.add(gdrive_id)
                        self.log(f"  ✓ Do GitHub: {github_item.get('filename')}")
                
                # 2. Adicionar novos locais que não estão no GitHub
                for local_item in local_schedule_data:
                    gdrive_id = local_item.get("gdrive_id")
                    
                    if gdrive_id and gdrive_id in processed_ids:
                        continue
                    
                    # Verificar se já foi postado
                    is_posted = any(
                        h.get("id") == gdrive_id or h.get("filename") == local_item.get("filename")
                        for h in self.history
                    )
                    
                    if not is_posted:
                        merged_schedule.append(local_item)
                        if gdrive_id:
                            processed_ids.add(gdrive_id)
                        self.log(f"  + Novo local: {local_item.get('filename')}")
                
                # Salvar o merge
                with open("schedule_queue.json", "w", encoding="utf-8") as f:
                    json.dump(merged_schedule, f, indent=2, ensure_ascii=False)
                
                # Salvar histórico atualizado
                with open("posted_history.json", "w", encoding="utf-8") as f:
                    json.dump(self.history[-500:], f, indent=2)
                
                self.log(f"✅ Merge concluído: {len(merged_schedule)} agendamentos")
                
                # Recarregar dados
                self.schedule = self.load_schedule()
                
                # Atualizar interface
                self.after(0, lambda: self.views["schedule"].refresh())
                self.after(0, lambda: self.views["dashboard"].refresh())
                self.after(0, lambda: self.views["library"].refresh())
                
                # Mostrar notificação
                if posted_ids:
                    self.after(0, lambda: self.show_toast(
                        f"✅ Atualizado do GitHub\n"
                        f"📅 {len(merged_schedule)} agendados\n"
                        f"✅ {len(posted_ids)} postados"
                    ))
                
            except requests.exceptions.RequestException as e:
                self.log(f"⚠️ Erro ao conectar ao GitHub: {e}")
                self.log("✅ Usando dados locais")
            except Exception as e:
                self.log(f"⚠️ Erro: {e}")
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=task, daemon=True).start()
    
    def auto_sync_on_startup(self):
        """Sincronização automática silenciosa ao iniciar o programa"""
        self.log("=" * 60)
        self.log("🔄 SINCRONIZAÇÃO AUTOMÁTICA AO INICIAR")
        self.log("=" * 60)
        
        def task():
            try:
                # Fazer pull silencioso para pegar dados do GitHub
                self.log("📥 Buscando dados do GitHub...")
                
                # Fetch primeiro
                fetch = subprocess.run(
                    ["git", "fetch", "origin", "main"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if fetch.returncode != 0:
                    self.log(f"⚠️ Aviso no fetch: {fetch.stderr}")
                    return
                
                # Verificar se há mudanças remotas
                diff_check = subprocess.run(
                    ["git", "diff", "HEAD", "origin/main", "--", "schedule_queue.json", "posted_history.json"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                has_remote_changes = bool(diff_check.stdout.strip())
                
                if has_remote_changes:
                    self.log("📋 Detectadas mudanças na nuvem - fazendo merge inteligente...")
                    
                    # NÃO fazer pull automático! Fazer merge manual para não perder dados
                    # Ler o schedule remoto
                    remote_schedule_raw = subprocess.run(
                        ["git", "show", "origin/main:schedule_queue.json"],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    
                    if remote_schedule_raw.returncode == 0:
                        try:
                            # 1. Primeiro, mesclar histórico se houver no remoto
                            remote_history_raw = subprocess.run(
                                ["git", "show", "origin/main:posted_history.json"],
                                capture_output=True, text=True, shell=True
                            )
                            if remote_history_raw.returncode == 0:
                                try:
                                    remote_history = json.loads(remote_history_raw.stdout)
                                    self.history = self.merge_json_data('history', self.history, remote_history)
                                    with open("posted_history.json", "w", encoding="utf-8") as f:
                                        json.dump(self.history[-500:], f, indent=2)
                                except Exception as e_h:
                                    self.log(f"⚠️ Erro ao mesclar histórico remoto: {e_h}")

                            # 2. Mesclar o schedule
                            try:
                                remote_schedule = json.loads(remote_schedule_raw.stdout)
                                
                                # Converter schedule local
                                local_schedule_data = []
                                for s in self.schedule:
                                    item = s.copy()
                                    if isinstance(item["schedule_time"], datetime.datetime):
                                        item["schedule_time"] = int(item["schedule_time"].timestamp())
                                    local_schedule_data.append(item)
                                
                                # MERGE inteligente
                                merged_schedule = self.merge_json_data('schedule', local_schedule_data, remote_schedule)
                                
                                # Salvar o merge
                                with open("schedule_queue.json", "w", encoding="utf-8") as f:
                                    json.dump(merged_schedule, f, indent=2, ensure_ascii=False)
                                
                                self.log(f"🔄 Merge automático concluído: {len(merged_schedule)} agendamentos")
                            except Exception as e_s:
                                self.log(f"⚠️ Erro ao mesclar schedule remoto: {e_s}")
                            
                            # Recarregar dados
                            self.schedule = self.load_schedule()
                            self.videos = self.load_library()
                            self.history = self.load_history()
                            self.accounts = self.load_accounts()
                            
                            # Atualizar interface
                            self.after(0, lambda: self.views["schedule"].refresh())
                            self.after(0, lambda: self.views["dashboard"].refresh())
                            self.after(0, lambda: self.views["library"].refresh())
                            
                            scheduled_count = len(self.schedule)
                            posted_count = len(self.history)
                            
                            self.log(f"📊 Status: {scheduled_count} agendados, {posted_count} postados")
                            
                            # Mostrar toast notification
                            self.after(0, lambda: self.show_toast(
                                f"✅ Dados atualizados\n"
                                f"📅 {scheduled_count} agendados • ✅ {posted_count} postados"
                            ))
                        except Exception as e_task:
                            self.log(f"⚠️ Erro na tarefa de merge: {e_task}")
                            
                        except json.JSONDecodeError as je:
                            self.log(f"⚠️ Erro ao fazer merge: {je}")
                else:
                    self.log("✅ Dados locais já estão atualizados")
                    
                    # Mesmo sem mudanças, mostrar status
                    scheduled_count = len(self.schedule)
                    posted_count = len(self.history)
                    self.log(f"📊 Status: {scheduled_count} agendados, {posted_count} postados")
                
            except Exception as e:
                self.log(f"⚠️ Erro na sincronização automática: {e}")
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=task, daemon=True).start()
    
    def show_toast(self, message):
        """Mostra uma notificação toast (não modal) no canto da tela"""
        toast = ctk.CTkToplevel(self)
        toast.title("")
        toast.geometry("350x100")
        
        # Posicionar no canto inferior direito
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = screen_width - 370
        y = screen_height - 150
        toast.geometry(f"+{x}+{y}")
        
        toast.overrideredirect(True)  # Sem borda
        toast.attributes("-topmost", True)  # Sempre no topo
        toast.configure(fg_color=BG_CARD)
        
        # Container
        container = ctk.CTkFrame(toast, fg_color=BG_CARD, corner_radius=15, border_width=2, border_color=ACCENT_GREEN)
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Mensagem
        label = ctk.CTkLabel(
            container,
            text=message,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_PRIMARY,
            justify="left"
        )
        label.pack(padx=20, pady=20)
        
        # Fechar automaticamente após 4 segundos
        def close_toast():
            if toast.winfo_exists():
                toast.destroy()
        
        toast.after(4000, close_toast)
        
        # Permitir fechar clicando
        container.bind("<Button-1>", lambda e: close_toast())
    
    def log(self, message):
        """Log de mensagens"""
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

    def merge_json_data(self, file_type, local_data, remote_data):
        """
        Mescla dados locais e remotos de forma inteligente.
        file_type: 'schedule', 'history' ou 'library'
        """
        self.log(f"🧩 Mesclando {file_type} (Local: {len(local_data)}, Remoto: {len(remote_data)})")
        
        if file_type == 'history':
            # Para histórico: união simples baseada em ID ou filename
            merged = local_data.copy()
            local_ids = {h.get("id") for h in merged if h.get("id")}
            local_names = {h.get("filename") for h in merged if h.get("filename")}
            
            for rh in remote_data:
                rid = rh.get("id")
                rname = rh.get("filename")
                if (rid and rid not in local_ids) or (not rid and rname and rname not in local_names):
                    merged.append(rh)
            
            # Ordenar por tempo de postagem
            merged.sort(key=lambda x: x.get("post_time", 0))
            return merged[-500:] # Mantém apenas os últimos 500
            
        elif file_type == 'schedule':
            # Para fila: união, mas REMOVE o que já está no histórico mesclado
            history_ids = {h.get("id") for h in getattr(self, 'history', []) if h.get("id")}
            history_names = {h.get("filename") for h in getattr(self, 'history', []) if h.get("filename")}
            
            merged_map = {}
            
            # Adiciona remotos primeiro (prioridade base)
            for item in remote_data:
                key = item.get("gdrive_id") or item.get("filename")
                if key:
                    merged_map[key] = item
            
            # Adiciona locais (pode sobrescrever remotos - útil se o usuário editou algo localmente)
            for item in local_data:
                key = item.get("gdrive_id") or item.get("filename")
                if key:
                    merged_map[key] = item
            
            # Filtrar o que já foi postado
            final_schedule = []
            for item in merged_map.values():
                gid = item.get("gdrive_id")
                fname = item.get("filename")
                if (gid and gid in history_ids) or (fname and fname in history_names):
                    self.log(f"  🗑️ Ignorando {fname} (já postado)")
                    continue
                final_schedule.append(item)
                
            # Ordenar por tempo
            final_schedule.sort(key=lambda x: x.get("schedule_time", 0))
            return final_schedule

        elif file_type == 'library':
            # Para biblioteca: união simples por path ou gdrive_id
            merged = local_data.copy()
            local_keys = {v.get("gdrive_id") or v.get("path") for v in merged}
            for rv in remote_data:
                rkey = rv.get("gdrive_id") or rv.get("path")
                if rkey not in local_keys:
                    merged.append(rv)
            return merged
        
        return local_data
    
    # === DATA MANAGEMENT ===
    
    def load_settings(self):
        if os.path.exists("settings.json"):
            try:
                with open("settings.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"default_caption": "", "last_used_accounts": [], "posts_per_day": 1, "interval_hours": 1}
    
    def save_settings(self):
        accs = [acc['name'] for acc in self.accounts if self.acc_vars[acc['name']].get()]
        self.settings["last_used_accounts"] = accs
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
    
    def load_library(self):
        if os.path.exists("library.json"):
            try:
                with open("library.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def save_library(self):
        data = []
        for v in self.videos:
            item = v.copy()
            if "widget" in item:
                del item["widget"]
            data.append(item)
        with open("library.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_schedule(self):
        """Carrega agendamentos e remove automaticamente vídeos já postados"""
        sched = []
        if os.path.exists("schedule_queue.json"):
            try:
                with open("schedule_queue.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Carregar histórico para verificação
                    history_ids = set()
                    history_filenames = set()
                    
                    # Garantir que history existe e está carregado
                    if not hasattr(self, 'history') or not self.history:
                        # Tentar carregar se ainda não foi (failsafe)
                        temp_history = self.load_history()
                        if temp_history:
                            self.history = temp_history
                    
                    for h in getattr(self, 'history', []):
                        if h.get("id"):
                            history_ids.add(h.get("id"))
                        if h.get("filename"):
                            history_filenames.add(h.get("filename"))
                    
                    removed_count = 0
                    for item in data:
                        if "schedule_time" in item:
                            # Converte timestamp UTC para datetime local
                            item["schedule_time"] = datetime.datetime.fromtimestamp(item["schedule_time"])
                        
                        # Verificar se já foi postado
                        gdrive_id = item.get("gdrive_id")
                        filename = item.get("filename")
                        
                        is_posted = (gdrive_id and gdrive_id in history_ids) or (filename and filename in history_filenames)
                        
                        if not is_posted:
                            sched.append(item)
                        else:
                            removed_count += 1
                            self.log(f"🗑️ Removido da fila (já postado): {filename}")
                    
                    if removed_count > 0:
                        self.log(f"✅ Limpeza automática: {removed_count} vídeo(s) já postado(s) removido(s)")
                        # Salvar a fila limpa
                        self.schedule = sched
                        self.save_schedule()
            except Exception as e:
                self.log(f"Erro ao carregar agendamentos: {e}")
        return sched
    
    def save_schedule(self):
        """Salva agendamentos com backup automático"""
        # Criar backup antes de salvar
        if os.path.exists("schedule_queue.json"):
            import shutil
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"schedule_queue_backup_{timestamp}.json"
            try:
                shutil.copy2("schedule_queue.json", backup_file)
                self.log(f"💾 Backup criado: {backup_file}")
                
                # Manter apenas os últimos 5 backups
                backups = sorted([f for f in os.listdir(".") if f.startswith("schedule_queue_backup_")])
                if len(backups) > 5:
                    for old_backup in backups[:-5]:
                        os.remove(old_backup)
            except Exception as e:
                self.log(f"⚠️ Erro ao criar backup: {e}")
        
        # Ordenar por horário
        self.schedule.sort(key=lambda x: x["schedule_time"].timestamp() if isinstance(x["schedule_time"], datetime.datetime) else x["schedule_time"])
        
        data = []
        for s in self.schedule:
            item = s.copy()
            if isinstance(item["schedule_time"], datetime.datetime):
                # Converte datetime local para timestamp UTC
                item["schedule_time"] = int(item["schedule_time"].timestamp())
            data.append(item)
        
        with open("schedule_queue.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.log(f"✅ Salvos {len(data)} agendamentos")
    
    def load_accounts(self):
        if os.path.exists("accounts.json"):
            try:
                with open("accounts.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def save_accounts(self):
        with open("accounts.json", "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, indent=2, ensure_ascii=False)
    
    def load_history(self):
        if os.path.exists("posted_history.json"):
            try:
                with open("posted_history.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [x for x in data if isinstance(x, dict)]
            except:
                pass
        return []
    
    def check_token_renewals(self):
        """Verifica e renova tokens expirados"""
        def task():
            changed = False
            now = time.time()
            for i, acc in enumerate(self.accounts):
                expiry = acc.get("token_expiry", 0)
                if expiry - now < 864000:  # 10 dias
                    self.log(f"Renovando token para {acc['name']}...")
                    api = MetaAPI(access_token=acc['access_token'])
                    new_token, expires_in = api.refresh_token(acc['access_token'])
                    if new_token and new_token != acc['access_token']:
                        self.accounts[i]['access_token'] = new_token
                        if expires_in:
                            self.accounts[i]['token_expiry'] = int(now + expires_in)
                        else:
                            self.accounts[i]['token_expiry'] = int(now + 5184000)
                        self.accounts[i]['last_renewed'] = int(now)
                        changed = True
                        self.log(f"Token renovado: {acc['name']}")
            
            if changed:
                self.save_accounts()
                self.after(0, lambda: self.views["accounts"].refresh() if "accounts" in self.views else None)
        
        threading.Thread(target=task, daemon=True).start()
    
    def get_highlights(self):
        """Retorna datas com agendamentos/postagens"""
        h = {}
        for s in self.schedule:
            d = s["schedule_time"].strftime("%d/%m/%Y")
            if d not in h:
                h[d] = {"total": 0, "future": 0}
            h[d]["total"] += 1
            h[d]["future"] += 1
        
        for pas in self.history:
            try:
                d = datetime.datetime.fromtimestamp(pas["post_time"]).strftime("%d/%m/%Y")
                if d not in h:
                    h[d] = {"total": 0, "future": 0}
                h[d]["total"] += 1
            except:
                pass
        
        return h

    
    # === ACTIONS ===
    
    def add_videos(self):
        """Adiciona vídeos do computador"""
        files = filedialog.askopenfilenames(filetypes=[("Vídeos", "*.mp4 *.mov")])
        for f in files:
            name = os.path.basename(f)
            if not any(v['path'] == f for v in self.videos):
                self.videos.append({
                    "path": f,
                    "filename": name,
                    "caption": "",
                    "gdrive_id": None
                })
        
        self.save_library()
        self.views["library"].refresh()
        
        if files:
            messagebox.showinfo("Sucesso", f"{len(files)} vídeo(s) adicionado(s)!")
    
    def pull_from_drive(self, account_name="Geral"):
        """Puxa vídeos do Google Drive incluindo subpastas"""
        def task():
            try:
                folder_id = None
                if account_name and account_name != "Geral":
                    acc = next((a for a in self.accounts if a['name'] == account_name), None)
                    if acc:
                        folder_id = acc.get("gdrive_folder_id")
                
                drive = GoogleDriveAPI()
                # Usar a nova função que lista vídeos com informação de subpasta
                files = drive.list_mp4_files_with_folders(folder_id=folder_id)
                added = 0
                
                for v in files:
                    if not any(x.get("gdrive_id") == v['id'] for x in self.videos):
                        self.videos.append({
                            "path": v['name'],
                            "filename": v['name'],
                            "caption": "",
                            "gdrive_id": v['id'],
                            "account": account_name if account_name != "Geral" else None,
                            "folder": v.get('folder')  # Nome da subpasta
                        })
                        added += 1
                
                if added > 0:
                    self.save_library()
                    self.log(f"Drive: {added} novos vídeos")
                    self.after(0, lambda: self.views["library"].refresh())
                    self.after(0, lambda: messagebox.showinfo("Sucesso", f"{added} vídeo(s) do Drive!"))
                else:
                    self.log("Drive: Nenhum vídeo novo")
                    self.after(0, lambda: messagebox.showinfo("Info", "Nenhum vídeo novo no Drive"))
            except Exception as e:
                self.log(f"Erro Drive: {e}")
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao acessar Drive: {e}"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def remove_from_library(self, video):
        """Remove vídeo da biblioteca"""
        if messagebox.askyesno("Confirmar", f"Remover '{video['filename']}'?"):
            self.videos.remove(video)
            self.save_library()
            self.views["library"].refresh()
    
    def select_all_library(self):
        """Seleciona todos os vídeos"""
        for v in self.videos:
            if "widget" in v and hasattr(v["widget"], "selected"):
                v["widget"].selected.set(True)
    
    def clear_library(self):
        """Limpa toda a biblioteca"""
        if messagebox.askyesno("Confirmar", "Limpar toda a biblioteca?"):
            self.videos = []
            self.save_library()
            self.views["library"].refresh()
    
    def process_schedule(self, videos, dates, config):
        """Processa o agendamento em lote com verificação de vídeos já postados"""
        sorted_dates = sorted(dates)
        all_generated = []
        video_idx = 0
        skipped_videos = []
        
        # Verificar quais vídeos já foram postados
        for v in videos[:]:  # Criar cópia da lista para iterar
            video_id = v.get("gdrive_id")
            video_name = v.get("filename")
            
            # Verificar no histórico se já foi postado
            is_posted = any(
                (video_id and h.get("id") == video_id) or (h.get("filename") == video_name)
                for h in self.history
            )
            
            # Verificar se já está agendado
            is_scheduled = any(
                (video_id and s.get("gdrive_id") == video_id) or (s.get("filename") == video_name)
                for s in self.schedule
            )
            
            if is_posted:
                skipped_videos.append(f"✅ {video_name} (já postado)")
                videos.remove(v)
            elif is_scheduled:
                skipped_videos.append(f"⏰ {video_name} (já agendado)")
                videos.remove(v)
        
        # Mostrar aviso se houver vídeos pulados
        if skipped_videos:
            skip_msg = "Os seguintes vídeos foram ignorados:\n\n" + "\n".join(skipped_videos[:10])
            if len(skipped_videos) > 10:
                skip_msg += f"\n\n... e mais {len(skipped_videos) - 10} vídeos"
            
            if not messagebox.askyesno(
                "Vídeos Ignorados",
                skip_msg + "\n\nDeseja continuar com os vídeos restantes?",
                icon="warning"
            ):
                return
        
        # Se não sobrou nenhum vídeo válido
        if not videos:
            messagebox.showwarning(
                "Nenhum Vídeo Válido",
                "Todos os vídeos selecionados já foram postados ou agendados!"
            )
            return
        
        for date in sorted_dates:
            if video_idx >= len(videos):
                break
            
            # Horário base do dia
            base_dt = datetime.datetime.combine(
                date,
                datetime.time(config["start_hour"], config["start_min"])
            )
            
            # Distribuir vídeos no dia
            videos_today = config["posts_per_day"]
            interval = config["interval_hours"]
            
            for _ in range(videos_today):
                if video_idx >= len(videos):
                    break
                
                v = videos[video_idx]
                
                # Determinar legenda
                if config["caption_mode"] == "title":
                    caption = os.path.splitext(v["filename"])[0]
                else:
                    caption = config["default_caption"]
                
                new_post = {
                    "gdrive_id": v.get("gdrive_id"),
                    "filename": v["filename"],
                    "caption": caption,
                    "schedule_time": base_dt,
                    "accounts": config["accounts"]
                }
                
                all_generated.append(new_post)
                base_dt += datetime.timedelta(hours=interval)
                video_idx += 1
        
        # Adicionar à fila
        self.schedule.extend(all_generated)
        
        # Desselecionar vídeos
        for v in self.videos:  # Usar self.videos ao invés de videos
            if "widget" in v and hasattr(v["widget"], "selected"):
                v["widget"].selected.set(False)
        
        # Limpar seleção do calendário
        if "schedule" in self.views:
            self.views["schedule"].calendar.selected_dates = []
        
        self.save_schedule()
        self.views["schedule"].refresh()
        self.views["library"].refresh()
        self.views["dashboard"].refresh()
        
        # Mensagem de sucesso com informações
        success_msg = f"✨ {len(all_generated)} vídeo(s) agendados!"
        if skipped_videos:
            success_msg += f"\n\n⚠️ {len(skipped_videos)} vídeo(s) ignorados"
        
        messagebox.showinfo("Sucesso", success_msg)
        self.show_view("schedule")
        
        # NÃO sincronizar automaticamente - deixar usuário decidir
        # self.log("🔄 Sincronizando automaticamente com a nuvem...")
        # self.sync_cloud()
    
    def edit_schedule(self, item):
        """Edita um agendamento"""
        from tkinter import simpledialog
        
        current_time = item["schedule_time"].strftime("%H:%M")
        new_time = simpledialog.askstring(
            "Editar Horário",
            "Novo horário (HH:MM):\n(Recomendado: :01, :06, :11, :16, :21, :26, :31, :36, :41, :46, :51, :56)",
            initialvalue=current_time
        )
        
        if new_time:
            try:
                h, m = map(int, new_time.split(":"))
                idx = self.schedule.index(item)
                self.schedule[idx]["schedule_time"] = item["schedule_time"].replace(hour=h, minute=m)
                self.save_schedule()
                self.views["schedule"].refresh()
                self.views["dashboard"].refresh()
                
                self.log(f"✏️ Horário editado: {item['filename']} -> {new_time}")
            except:
                messagebox.showerror("Erro", "Formato inválido! Use HH:MM")
    
    def remove_schedule(self, item):
        """Remove um agendamento"""
        if messagebox.askyesno("Confirmar", f"Remover agendamento de '{item['filename']}'?"):
            self.schedule.remove(item)
            self.save_schedule()
            self.views["schedule"].refresh()
            self.views["dashboard"].refresh()
            
            self.log(f"🗑️ Agendamento removido: {item['filename']}")
    
    def clear_schedule(self):
        """Limpa todos os agendamentos"""
        if messagebox.askyesno("Confirmar", "Limpar TODOS os agendamentos?"):
            self.schedule = []
            self.save_schedule()
            self.views["schedule"].refresh()
            self.views["dashboard"].refresh()
    
    def clean_posted_from_schedule(self):
        """Remove da fila de agendamentos os vídeos que já foram postados"""
        if not self.schedule:
            messagebox.showinfo("Info", "Não há agendamentos na fila!")
            return
        
        self.log("🧹 Limpando vídeos já postados da fila...")
        
        # Criar sets para busca rápida
        history_ids = set()
        history_filenames = set()
        for h in self.history:
            if h.get("id"):
                history_ids.add(h.get("id"))
            if h.get("filename"):
                history_filenames.add(h.get("filename"))
        
        # Filtrar agendamentos
        original_count = len(self.schedule)
        new_schedule = []
        removed_videos = []
        
        for item in self.schedule:
            gdrive_id = item.get("gdrive_id")
            filename = item.get("filename")
            
            is_posted = (gdrive_id and gdrive_id in history_ids) or (filename and filename in history_filenames)
            
            if not is_posted:
                new_schedule.append(item)
            else:
                removed_videos.append(filename)
                self.log(f"  🗑️ Removido: {filename}")
        
        removed_count = original_count - len(new_schedule)
        
        if removed_count > 0:
            self.schedule = new_schedule
            self.save_schedule()
            self.views["schedule"].refresh()
            self.views["dashboard"].refresh()
            
            msg = f"✅ Limpeza concluída!\n\n"
            msg += f"🗑️ {removed_count} vídeo(s) já postado(s) removido(s)\n"
            msg += f"📋 {len(new_schedule)} agendamento(s) restante(s)\n\n"
            
            if removed_videos:
                msg += "Vídeos removidos:\n" + "\n".join([f"• {v}" for v in removed_videos[:5]])
                if len(removed_videos) > 5:
                    msg += f"\n... e mais {len(removed_videos) - 5}"
            
            messagebox.showinfo("Limpeza Concluída", msg)
            
            # Perguntar se quer sincronizar
            if messagebox.askyesno("Sincronizar", "Deseja sincronizar com a nuvem agora?"):
                self.sync_cloud()
        else:
            messagebox.showinfo("Info", "✅ Nenhum vídeo já postado encontrado na fila!\n\nTodos os agendamentos são válidos.")
    
    def sync_cloud(self):
        """Sincroniza com o GitHub - VERSÃO SIMPLIFICADA E SEGURA"""
        self.log("=" * 60)
        self.log("🔄 SINCRONIZAÇÃO COM A NUVEM")
        self.log("=" * 60)
        
        now = datetime.datetime.now()
        self.log(f"🕐 Horário: {now.strftime('%d/%m/%Y %H:%M:%S')}")
        
        # PASSO 1: Salvar dados locais COM BACKUP
        self.log("💾 Salvando dados locais...")
        
        # SEGURANÇA: Verificar se o schedule está vazio MAS o arquivo local tem dados
        # Isso evita que um erro de carregamento zere o arquivo ao salvar
        if not self.schedule and os.path.exists("schedule_queue.json"):
            try:
                with open("schedule_queue.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data and len(data) > 0:
                        self.log("⚠️ AVISO: Schedule local vazio mas arquivo tem dados. Carregando antes de salvar.")
                        self.schedule = self.load_schedule()
            except:
                pass
                
        self.save_schedule()
        self.save_accounts()
        
        def task():
            try:
                # PASSO 2: Sincronização com Google Drive (Contas, Fila e Histórico)
                self.log("☁️ Sincronizando com Google Drive...")
                drive_result = subprocess.run(
                    [sys.executable, "execution/sync_manager.py", "--action", "upload"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if drive_result.returncode == 0:
                    self.log("✅ Dados sincronizados no Drive")
                else:
                    self.log(f"⚠️ Aviso Drive: {drive_result.stderr}")

                # PASSO 3: Adicionar tudo ao Git
                self.log("📦 Adicionando arquivos ao Git...")
                subprocess.run(["git", "add", "."], capture_output=True, shell=True)
                
                # PASSO 4: Commit
                self.log("📝 Criando commit...")
                commit_result = subprocess.run(
                    ["git", "commit", "-m", f"sync {now.strftime('%Y-%m-%d %H:%M:%S')} [skip ci]"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if "nothing to commit" in commit_result.stdout:
                    self.log("ℹ️ Nenhuma mudança para commitar")
                else:
                    self.log("✅ Commit criado")
                
                # PASSO 5: Pull com MERGE (não rebase)
                self.log("📥 Sincronizando com GitHub...")
                pull_result = subprocess.run(
                    ["git", "pull", "--no-rebase"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                # Se houver conflito, resolver com MERGE inteligente
                if pull_result.returncode != 0:
                    if "CONFLICT" in pull_result.stdout or "CONFLICT" in pull_result.stderr:
                        self.log("⚠️ Conflito detectado - resolvendo com merge inteligente...")
                        
                        for file_name in ["posted_history.json", "schedule_queue.json", "library.json"]:
                            try:
                                # 1. Pegar versão remota
                                remote_raw = subprocess.run(
                                    ["git", "show", f"origin/main:{file_name}"],
                                    capture_output=True, text=True, shell=True
                                )
                                if remote_raw.returncode != 0: continue
                                remote_json = json.loads(remote_raw.stdout)
                                
                                # 2. Pegar versão local (que já foi salva no passo 1)
                                with open(file_name, "r", encoding="utf-8") as f:
                                    local_json = json.load(f)
                                
                                # 3. Mesclar
                                ftype = file_name.split("_")[0] if "_" in file_name else file_name.split(".")[0]
                                if ftype == "schedule":
                                    # Converter datetime objetos em int para o merge
                                    for item in local_json:
                                        if isinstance(item.get("schedule_time"), datetime.datetime):
                                            item["schedule_time"] = int(item["schedule_time"].timestamp())
                                
                                merged_json = self.merge_json_data(ftype, local_json, remote_json)
                                
                                # 4. Salvar e adicionar ao git
                                with open(file_name, "w", encoding="utf-8") as f:
                                    json.dump(merged_json, f, indent=2, ensure_ascii=False)
                                subprocess.run(["git", "add", file_name], capture_output=True, shell=True)
                                
                            except Exception as em:
                                self.log(f"❌ Erro ao mesclar {file_name}: {em}")
                        
                        # Concluir o merge
                        subprocess.run(["git", "commit", "--no-edit"], capture_output=True, shell=True)
                        self.log("✅ Conflito resolvido com merge inteligente")
                else:
                    self.log("✅ Pull concluído")
                
                # PASSO 6: Push
                self.log("📤 Enviando para GitHub...")
                push_result = subprocess.run(
                    ["git", "push"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                
                if push_result.returncode == 0:
                    self.log("=" * 60)
                    self.log("� SINCRONIZAÇÃO COMPLETA!")
                    self.log("=" * 60)
                    
                    # Recarregar dados
                    self.schedule = self.load_schedule()
                    self.videos = self.load_library()
                    self.history = self.load_history()
                    self.accounts = self.load_accounts()
                    
                    # Atualizar interface
                    self.after(0, lambda: self.views["schedule"].refresh())
                    self.after(0, lambda: self.views["dashboard"].refresh())
                    self.after(0, lambda: self.views["library"].refresh())
                    
                    count = len(self.schedule)
                    posted = len(self.history)
                    
                    self.after(0, lambda: messagebox.showinfo(
                        "Sucesso",
                        f"✅ Sincronizado!\n\n"
                        f"� {count} agendados\n"
                        f"✅ {posted} postados\n"
                        f"🕐 {now.strftime('%d/%m/%Y %H:%M')}"
                    ))
                else:
                    self.log(f"❌ Erro no push: {push_result.stderr}")
                    self.after(0, lambda: messagebox.showerror(
                        "Erro",
                        f"Falha ao enviar para GitHub:\n\n{push_result.stderr}"
                    ))
                    
            except Exception as e:
                self.log(f"❌ Erro: {e}")
                import traceback
                traceback.print_exc()
                self.after(0, lambda: messagebox.showerror("Erro", str(e)))
        
        threading.Thread(target=task, daemon=True).start()
    
    def run_bot_now(self):
        """Executa o robô imediatamente (simula o que o GitHub Actions faz)"""
        if not self.schedule:
            messagebox.showwarning("Atenção", "Não há agendamentos na fila!")
            return
        
        # Verificar se há agendamentos prontos para publicar
        current_time = int(time.time())
        ready_to_post = [s for s in self.schedule if s.get("schedule_time", 0) <= current_time]
        
        if not ready_to_post:
            # Mostrar próximo agendamento
            next_schedule = min(self.schedule, key=lambda x: x.get("schedule_time", 0))
            next_time = datetime.datetime.fromtimestamp(next_schedule["schedule_time"])
            time_diff = next_schedule["schedule_time"] - current_time
            minutes = time_diff // 60
            
            msg = f"Nenhum vídeo pronto para publicar agora.\n\n"
            msg += f"Próximo agendamento:\n"
            msg += f"📹 {next_schedule['filename']}\n"
            msg += f"🕐 {next_time.strftime('%d/%m/%Y às %H:%M')}\n"
            msg += f"⏱️ Faltam {minutes} minutos"
            
            if messagebox.askyesno("Aguardando", msg + "\n\nDeseja publicar mesmo assim?"):
                ready_to_post = self.schedule[:1]  # Pega o primeiro da fila
            else:
                return
        
        count = len(ready_to_post)
        if not messagebox.askyesno(
            "Confirmar",
            f"🚀 Executar robô agora?\n\n"
            f"Isso vai publicar {count} vídeo(s) imediatamente.\n\n"
            f"Deseja continuar?"
        ):
            return
        
        self.log("🚀 === EXECUTANDO ROBÔ MANUALMENTE ===")
        
        def task():
            try:
                from gdrive_api import GoogleDriveAPI
                from meta_api import MetaAPI
                import os
                
                drive = GoogleDriveAPI()
                if not drive.service:
                    self.log("❌ Erro: API do Drive não inicializada")
                    self.after(0, lambda: messagebox.showerror("Erro", "Google Drive não configurado!"))
                    return
                
                posted_count = 0
                failed_count = 0
                new_schedule = []
                
                for job in self.schedule:
                    schedule_time = job.get("schedule_time", 0)
                    
                    # Só processa se estiver na lista de prontos
                    if job not in ready_to_post:
                        new_schedule.append(job)
                        continue
                    
                    filename = job.get("filename", "video.mp4")
                    file_id = job.get("gdrive_id")
                    caption = job.get("caption", "")
                    accounts = job.get("accounts", [])
                    
                    self.log(f"\n📹 Processando: {filename}")
                    
                    # Download do vídeo
                    local_path = drive.download_file(file_id, filename)
                    if not local_path or not os.path.exists(local_path):
                        self.log(f"❌ Falha ao baixar {filename}")
                        new_schedule.append(job)
                        failed_count += 1
                        continue
                    
                    failed_accounts = []
                    any_success = False
                    
                    for acc in accounts:
                        acc_name = acc.get("name", "Sem Nome")
                        self.log(f"  📱 Conta: {acc_name}")
                        
                        meta = MetaAPI(
                            ig_account_id=acc.get("ig_account_id"),
                            fb_page_id=acc.get("fb_page_id"),
                            access_token=acc.get("access_token")
                        )
                        
                        # Instagram
                        if meta.ig_account_id:
                            self.log(f"    📸 Tentando Instagram...")
                            if meta.upload_ig_reels_resumable(local_path, caption):
                                self.log(f"    ✅ Instagram OK!")
                                acc['ig_account_id'] = None
                                any_success = True
                            else:
                                self.log(f"    ❌ Instagram falhou")
                        
                        # Facebook
                        if meta.fb_page_id:
                            self.log(f"    📘 Tentando Facebook...")
                            if meta.upload_fb_reels_resumable(local_path, caption):
                                self.log(f"    ✅ Facebook OK!")
                                acc['fb_page_id'] = None
                                any_success = True
                            else:
                                self.log(f"    ❌ Facebook falhou")
                        
                        # Se ainda tem IDs pendentes, adiciona à lista de falhas
                        if acc.get('ig_account_id') or acc.get('fb_page_id'):
                            failed_accounts.append(acc)
                    
                    # Limpar arquivo local
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    
                    # Decidir o que fazer com o job
                    if not failed_accounts and any_success:
                        self.log(f"✅ {filename} publicado com sucesso!")
                        posted_count += 1
                        
                        # Adicionar ao histórico
                        self.history.append({
                            "id": file_id,
                            "filename": filename,
                            "post_time": current_time
                        })
                        
                        # Tentar deletar do Drive
                        try:
                            drive.delete_file(file_id)
                            self.log(f"🗑️ {filename} removido do Drive")
                        except:
                            self.log(f"⚠️ Não foi possível remover {filename} do Drive")
                    
                    elif failed_accounts:
                        self.log(f"⚠️ {filename} publicado parcialmente")
                        job["accounts"] = failed_accounts
                        new_schedule.append(job)
                        posted_count += 1
                    else:
                        self.log(f"❌ {filename} falhou completamente")
                        new_schedule.append(job)
                        failed_count += 1
                
                # Atualizar schedule
                self.schedule = new_schedule
                self.save_schedule()
                
                # Salvar histórico
                with open("posted_history.json", "w", encoding="utf-8") as f:
                    json.dump(self.history[-500:], f, indent=2)
                
                self.log(f"\n{'='*60}")
                self.log(f"🎉 ROBÔ CONCLUÍDO!")
                self.log(f"✅ Publicados: {posted_count}")
                self.log(f"❌ Falhas: {failed_count}")
                self.log(f"📋 Restantes na fila: {len(new_schedule)}")
                self.log(f"{'='*60}")
                
                # Atualizar interface
                self.after(0, lambda: self.views["schedule"].refresh())
                self.after(0, lambda: self.views["dashboard"].refresh())
                self.after(0, lambda: self.views["library"].refresh())
                
                # Mensagem final
                msg = f"🎉 Robô executado!\n\n"
                msg += f"✅ Publicados: {posted_count}\n"
                msg += f"❌ Falhas: {failed_count}\n"
                msg += f"📋 Restantes: {len(new_schedule)}"
                
                if posted_count > 0:
                    msg += f"\n\n💡 Sincronize com a nuvem para atualizar o GitHub!"
                
                self.after(0, lambda: messagebox.showinfo("Concluído", msg))
                
            except Exception as e:
                self.log(f"❌ Erro crítico: {e}")
                import traceback
                self.log(traceback.format_exc())
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro ao executar robô:\n{str(e)}"))
        
        threading.Thread(target=task, daemon=True).start()
    
    def post_now(self):
        """Posta vídeos imediatamente"""
        active = [acc for acc in self.accounts if self.acc_vars[acc['name']].get()]
        selected = [
            v for v in self.videos
            if v.get("widget") and hasattr(v["widget"], "selected") and v["widget"].selected.get()
        ]
        
        if not active or not selected:
            messagebox.showwarning("Atenção", "Selecione vídeos e contas!")
            return
        
        if not messagebox.askyesno("Confirmar", f"Postar {len(selected)} vídeo(s) AGORA em {len(active)} conta(s)?"):
            return
        
        def task():
            try:
                global_cap = self.settings.get("default_caption", "")
                print(f"\n{'='*60}")
                print(f"INICIANDO POSTAGEM IMEDIATA")
                print(f"{'='*60}")
                print(f"📝 Legenda padrão configurada: '{global_cap}'")
                print(f"📝 Tamanho da legenda: {len(global_cap)} caracteres")
                
                for v in selected:
                    video_caption = v.get("caption") or global_cap
                    video_path = v.get('path', '')
                    
                    print(f"\n� Vídeo: {v.get('name', 'sem nome')}")
                    print(f"� Caminho original: {video_path}")
                    
                    # Se o vídeo não existe localmente, tentar baixar do Drive
                    if not os.path.exists(video_path):
                        gdrive_id = v.get('gdrive_id')
                        if gdrive_id:
                            print(f"� Vídeo não encontrado localmente, baixando do Drive...")
                            try:
                                drive = GoogleDriveAPI()
                                local_path = drive.download_file(gdrive_id, v.get('filename', 'video.mp4'))
                                video_path = local_path
                                print(f"✅ Download concluído: {video_path}")
                            except Exception as download_err:
                                error_msg = f"Erro ao baixar do Drive: {download_err}"
                                print(f"❌ {error_msg}")
                                self.log(error_msg)
                                continue
                        else:
                            error_msg = f"Arquivo não encontrado e sem ID do Drive: {video_path}"
                            print(f"❌ {error_msg}")
                            self.log(error_msg)
                            continue
                    
                    print(f"� Caminho final: {video_path}")
                    print(f"📝 Legenda do vídeo: '{v.get('caption', 'NENHUMA')}'")
                    print(f"� Legenda final a ser usada: '{video_caption}'")
                    
                    for acc in active:
                        print(f"\n� Conta: {acc['name']}")
                        meta = MetaAPI(
                            acc['ig_account_id'],
                            acc['fb_page_id'],
                            acc['access_token']
                        )
                        
                        if acc.get('ig_account_id'):
                            print(f"📱 Postando no Instagram...")
                            meta.upload_ig_reels_resumable(video_path, video_caption)
                        
                        if acc.get('fb_page_id'):
                            print(f"📘 Postando no Facebook...")
                            meta.upload_fb_reels_resumable(video_path, video_caption)
                
                self.after(0, lambda: messagebox.showinfo("Sucesso", "Postagens concluídas!"))
            except Exception as err:
                error_msg = str(err)
                self.log(f"Erro: {error_msg}")
                self.after(0, lambda msg=error_msg: messagebox.showerror("Erro", msg))
        
        threading.Thread(target=task, daemon=True).start()
    
    def open_drive_browser(self):
        """Abre o Google Drive no navegador"""
        folder_id = getattr(config, "GDRIVE_FOLDER_ID", None)
        if folder_id:
            webbrowser.open(f"https://drive.google.com/drive/u/0/folders/{folder_id}")
    
    def open_github_actions(self):
        """Abre o GitHub Actions no navegador"""
        webbrowser.open("https://github.com/agenciaaguiacontact-sys/reels-bot-publico/actions")
    
    def open_schedule_file(self):
        """Abre o arquivo de fila no GitHub"""
        webbrowser.open("https://github.com/agenciaaguiacontact-sys/reels-bot-publico/blob/main/schedule_queue.json")


if __name__ == "__main__":
    app = MetaStudioApp()
    app.mainloop()
