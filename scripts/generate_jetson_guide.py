from __future__ import annotations

import os
import textwrap
from datetime import date
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "pdf"
TMP_DIR = ROOT / "tmp" / "pdfs"
OUTPUT_PDF = OUTPUT_DIR / "jetson_nano_kurulum_ve_kodlama_rehberi.pdf"

PAGE_W, PAGE_H = A4
MARGIN_X = 44
CONTENT_W = PAGE_W - 2 * MARGIN_X
TOP_Y = PAGE_H - 72
BOTTOM_Y = 46

NAVY = HexColor("#12212B")
INK = HexColor("#1E2C35")
MUTED = HexColor("#62717C")
GREEN = HexColor("#76B900")
GREEN_DARK = HexColor("#4F7F00")
TEAL = HexColor("#0B7A75")
BLUE = HexColor("#2A6F97")
AMBER = HexColor("#D99000")
RED = HexColor("#B53A3A")
LIGHT = HexColor("#F3F6F7")
LIGHT_GREEN = HexColor("#EEF7DD")
LIGHT_BLUE = HexColor("#EAF3F8")
LIGHT_AMBER = HexColor("#FFF4D8")
LIGHT_RED = HexColor("#FBEAEA")
CODE_BG = HexColor("#142129")
CODE_INK = HexColor("#E7F2F5")
GRID = HexColor("#D5DEE2")


def register_fonts() -> None:
    fonts = {
        "UI": r"C:\Windows\Fonts\segoeui.ttf",
        "UI-Semibold": r"C:\Windows\Fonts\seguisb.ttf",
        "UI-Bold": r"C:\Windows\Fonts\segoeuib.ttf",
        "Mono": r"C:\Windows\Fonts\consola.ttf",
        "Mono-Bold": r"C:\Windows\Fonts\consolab.ttf",
    }
    for name, path in fonts.items():
        if not Path(path).exists():
            raise FileNotFoundError(f"Gerekli yazı tipi bulunamadı: {path}")
        pdfmetrics.registerFont(TTFont(name, path))


def wrap_text(text: str, font: str, size: float, width: float) -> list[str]:
    if not text:
        return [""]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        probe = word if not current else current + " " + word
        if pdfmetrics.stringWidth(probe, font, size) <= width:
            current = probe
        else:
            if current:
                lines.append(current)
            if pdfmetrics.stringWidth(word, font, size) <= width:
                current = word
            else:
                piece = ""
                for ch in word:
                    if pdfmetrics.stringWidth(piece + ch, font, size) <= width:
                        piece += ch
                    else:
                        lines.append(piece)
                        piece = ch
                current = piece
    if current:
        lines.append(current)
    return lines


def wrap_code_line(line: str, font: str, size: float, width: float) -> list[str]:
    if pdfmetrics.stringWidth(line, font, size) <= width:
        return [line]
    indent = len(line) - len(line.lstrip(" "))
    prefix = " " * indent
    out: list[str] = []
    rest = line
    while rest:
        cut = len(rest)
        while cut > 1 and pdfmetrics.stringWidth(rest[:cut], font, size) > width:
            cut -= 1
        if cut < len(rest):
            split_at = rest.rfind(" ", 0, cut)
            if split_at > max(indent + 5, cut // 2):
                cut = split_at
        out.append(rest[:cut].rstrip())
        rest = prefix + "  " + rest[cut:].lstrip()
    return out


class PageBuilder:
    def __init__(self, c: canvas.Canvas, page_no: int, section: str, title: str):
        self.c = c
        self.page_no = page_no
        self.section_name = section
        self.page_title = title
        self.y = TOP_Y
        self._header()

    def _header(self) -> None:
        self.c.setFillColor(NAVY)
        self.c.rect(0, PAGE_H - 46, PAGE_W, 46, fill=1, stroke=0)
        self.c.setFillColor(GREEN)
        self.c.rect(0, PAGE_H - 46, 9, 46, fill=1, stroke=0)
        self.c.setFont("UI-Semibold", 8.6)
        self.c.setFillColor(HexColor("#BFD0D8"))
        self.c.drawString(MARGIN_X, PAGE_H - 19, self.section_name.upper())
        self.c.setFont("UI", 8.2)
        self.c.setFillColor(white)
        self.c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 19, "JETSON NANO | KURULUM VE KODLAMA")

    def finish(self) -> None:
        self.c.setStrokeColor(GRID)
        self.c.line(MARGIN_X, 34, PAGE_W - MARGIN_X, 34)
        self.c.setFont("UI", 7.6)
        self.c.setFillColor(MUTED)
        self.c.drawString(MARGIN_X, 20, "Waveshare Jetson Nano Dev Kit A - kişisel çalışma kılavuzu")
        self.c.drawRightString(PAGE_W - MARGIN_X, 20, str(self.page_no))

    def ensure(self, height: float) -> None:
        if self.y - height < BOTTOM_Y:
            raise RuntimeError(
                f"Sayfa {self.page_no} taştı: '{self.page_title}', y={self.y:.1f}, gerekli={height:.1f}"
            )

    def h1(self, title: str, kicker: str | None = None) -> None:
        if kicker:
            self.c.setFont("UI-Semibold", 8.2)
            self.c.setFillColor(GREEN_DARK)
            self.c.drawString(MARGIN_X, self.y, kicker.upper())
            self.y -= 15
        lines = wrap_text(title, "UI-Bold", 20, CONTENT_W)
        self.ensure(len(lines) * 24 + 14)
        self.c.setFillColor(NAVY)
        self.c.setFont("UI-Bold", 20)
        for line in lines:
            self.c.drawString(MARGIN_X, self.y, line)
            self.y -= 24
        self.y -= 9

    def h2(self, title: str, color=TEAL) -> None:
        self.ensure(27)
        self.y -= 3
        self.c.setFillColor(color)
        self.c.rect(MARGIN_X, self.y - 12, 4, 15, fill=1, stroke=0)
        self.c.setFillColor(NAVY)
        self.c.setFont("UI-Semibold", 12)
        self.c.drawString(MARGIN_X + 11, self.y - 9, title)
        self.y -= 24

    def paragraph(self, text: str, size: float = 9.2, leading: float = 12.3, color=INK, gap: float = 7) -> None:
        lines = wrap_text(text, "UI", size, CONTENT_W)
        self.ensure(len(lines) * leading + gap)
        self.c.setFillColor(color)
        self.c.setFont("UI", size)
        for line in lines:
            self.c.drawString(MARGIN_X, self.y, line)
            self.y -= leading
        self.y -= gap

    def bullet(self, text: str, level: int = 0, color=INK, gap: float = 3) -> None:
        indent = 14 + level * 18
        width = CONTENT_W - indent
        lines = wrap_text(text, "UI", 8.9, width)
        height = len(lines) * 11.7 + gap
        self.ensure(height)
        bullet_x = MARGIN_X + level * 18
        self.c.setFillColor(GREEN if level == 0 else TEAL)
        self.c.circle(bullet_x + 3, self.y + 3, 2.2 if level == 0 else 1.6, fill=1, stroke=0)
        self.c.setFillColor(color)
        self.c.setFont("UI", 8.9)
        for i, line in enumerate(lines):
            self.c.drawString(MARGIN_X + indent, self.y, line)
            self.y -= 11.7
        self.y -= gap

    def numbered(self, n: str, text: str) -> None:
        width = CONTENT_W - 30
        lines = wrap_text(text, "UI", 8.9, width)
        height = max(21, len(lines) * 11.7) + 4
        self.ensure(height)
        self.c.setFillColor(GREEN)
        self.c.circle(MARGIN_X + 10, self.y - 2, 9, fill=1, stroke=0)
        self.c.setFillColor(NAVY)
        self.c.setFont("UI-Bold", 8.4)
        self.c.drawCentredString(MARGIN_X + 10, self.y - 5, str(n))
        self.c.setFont("UI", 8.9)
        self.c.setFillColor(INK)
        for line in lines:
            self.c.drawString(MARGIN_X + 30, self.y, line)
            self.y -= 11.7
        self.y -= 7

    def code(self, code: str, label: str = "JETSON TERMİNALİ", font_size: float = 7.3) -> None:
        lines: list[str] = []
        for raw in code.strip("\n").splitlines():
            lines.extend(wrap_code_line(raw.rstrip(), "Mono", font_size, CONTENT_W - 24))
        leading = font_size + 3.0
        height = 24 + len(lines) * leading + 12
        self.ensure(height + 6)
        self.c.setFillColor(CODE_BG)
        self.c.roundRect(MARGIN_X, self.y - height, CONTENT_W, height, 5, fill=1, stroke=0)
        self.c.setFillColor(GREEN)
        self.c.roundRect(MARGIN_X + 10, self.y - 18, 69, 12, 3, fill=1, stroke=0)
        self.c.setFillColor(NAVY)
        self.c.setFont("UI-Bold", 6.3)
        self.c.drawCentredString(MARGIN_X + 44.5, self.y - 15, label[:19])
        self.c.setFillColor(CODE_INK)
        self.c.setFont("Mono", font_size)
        yy = self.y - 32
        for line in lines:
            self.c.drawString(MARGIN_X + 12, yy, line)
            yy -= leading
        self.y -= height + 7

    def callout(self, title: str, text: str, kind: str = "info") -> None:
        palette = {
            "info": (LIGHT_BLUE, BLUE),
            "safe": (LIGHT_GREEN, GREEN_DARK),
            "warn": (LIGHT_AMBER, AMBER),
            "danger": (LIGHT_RED, RED),
        }
        bg, accent = palette[kind]
        lines = wrap_text(text, "UI", 8.5, CONTENT_W - 28)
        height = 29 + len(lines) * 11.2 + 8
        self.ensure(height + 6)
        self.c.setFillColor(bg)
        self.c.setStrokeColor(accent)
        self.c.roundRect(MARGIN_X, self.y - height, CONTENT_W, height, 5, fill=1, stroke=1)
        self.c.setFillColor(accent)
        self.c.rect(MARGIN_X, self.y - height, 5, height, fill=1, stroke=0)
        self.c.setFont("UI-Semibold", 9)
        self.c.drawString(MARGIN_X + 14, self.y - 17, title)
        self.c.setFont("UI", 8.5)
        self.c.setFillColor(INK)
        yy = self.y - 32
        for line in lines:
            self.c.drawString(MARGIN_X + 14, yy, line)
            yy -= 11.2
        self.y -= height + 7

    def table(self, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
        if widths is None:
            widths = [CONTENT_W / len(headers)] * len(headers)
        if abs(sum(widths) - CONTENT_W) > 0.5:
            scale = CONTENT_W / sum(widths)
            widths = [w * scale for w in widths]
        all_rows = [headers] + rows
        row_heights: list[float] = []
        wrapped: list[list[list[str]]] = []
        for ridx, row in enumerate(all_rows):
            wr: list[list[str]] = []
            max_lines = 1
            font = "UI-Semibold" if ridx == 0 else "UI"
            size = 7.6 if ridx == 0 else 7.7
            for cell, width in zip(row, widths):
                lines = wrap_text(str(cell), font, size, width - 12)
                wr.append(lines)
                max_lines = max(max_lines, len(lines))
            wrapped.append(wr)
            row_heights.append(max(21, 8 + max_lines * 9.6))
        total_h = sum(row_heights)
        self.ensure(total_h + 8)
        y_top = self.y
        for ridx, (row, h) in enumerate(zip(wrapped, row_heights)):
            x = MARGIN_X
            self.c.setFillColor(NAVY if ridx == 0 else (LIGHT if ridx % 2 else white))
            self.c.rect(MARGIN_X, y_top - h, CONTENT_W, h, fill=1, stroke=0)
            for cidx, (cell_lines, width) in enumerate(zip(row, widths)):
                self.c.setStrokeColor(GRID)
                self.c.rect(x, y_top - h, width, h, fill=0, stroke=1)
                self.c.setFillColor(white if ridx == 0 else INK)
                self.c.setFont("UI-Semibold" if ridx == 0 else "UI", 7.6 if ridx == 0 else 7.7)
                yy = y_top - 14
                for line in cell_lines:
                    self.c.drawString(x + 6, yy, line)
                    yy -= 9.6
                x += width
            y_top -= h
        self.y -= total_h + 8

    def small(self, text: str, color=MUTED) -> None:
        lines = wrap_text(text, "UI", 7.6, CONTENT_W)
        self.ensure(len(lines) * 10 + 4)
        self.c.setFont("UI", 7.6)
        self.c.setFillColor(color)
        for line in lines:
            self.c.drawString(MARGIN_X, self.y, line)
            self.y -= 10
        self.y -= 4


def draw_cover(c: canvas.Canvas) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.rect(0, 0, 14, PAGE_H, fill=1, stroke=0)
    c.setFillColor(HexColor("#1A303C"))
    c.circle(PAGE_W - 38, PAGE_H - 85, 130, fill=1, stroke=0)
    c.setStrokeColor(HexColor("#33505E"))
    for r in (40, 70, 100):
        c.circle(PAGE_W - 38, PAGE_H - 85, r, fill=0, stroke=1)
    c.setFillColor(GREEN)
    c.roundRect(MARGIN_X, PAGE_H - 152, 132, 26, 6, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("UI-Bold", 10)
    c.drawCentredString(MARGIN_X + 66, PAGE_H - 143, "UYGULAMALI EĞİTİM")
    c.setFillColor(white)
    c.setFont("UI-Bold", 31)
    c.drawString(MARGIN_X, PAGE_H - 215, "JETSON NANO")
    c.setFont("UI-Semibold", 23)
    c.setFillColor(HexColor("#D7E5EA"))
    c.drawString(MARGIN_X, PAGE_H - 251, "Kurulum, Linux, GPIO ve")
    c.drawString(MARGIN_X, PAGE_H - 282, "Kodlama Rehberi")
    c.setFillColor(GREEN)
    c.rect(MARGIN_X, PAGE_H - 307, 246, 4, fill=1, stroke=0)
    c.setFillColor(HexColor("#BFD0D8"))
    c.setFont("UI", 11)
    c.drawString(MARGIN_X, PAGE_H - 341, "Waveshare Jetson Nano Dev Kit A")
    c.drawString(MARGIN_X, PAGE_H - 360, "Başsız kullanım: USB seri + SSH + VNC")
    c.drawString(MARGIN_X, PAGE_H - 379, "JetPack 4.6.5 | CUDA 10.2 | Python | Jetson.GPIO")

    # Stylized terminal window
    x, y, w, h = MARGIN_X, 164, CONTENT_W, 212
    c.setFillColor(HexColor("#0D171D"))
    c.roundRect(x, y, w, h, 9, fill=1, stroke=0)
    c.setFillColor(HexColor("#263944"))
    c.roundRect(x, y + h - 28, w, 28, 9, fill=1, stroke=0)
    for i, col in enumerate((RED, AMBER, GREEN)):
        c.setFillColor(col)
        c.circle(x + 18 + i * 17, y + h - 14, 4, fill=1, stroke=0)
    c.setFont("Mono", 9)
    c.setFillColor(HexColor("#D9E9EE"))
    lines = [
        "jetson@jetson-desktop:~$ findmnt -n -o SOURCE /",
        "/dev/mmcblk1p1",
        "",
        "jetson@jetson-desktop:~$ /usr/local/cuda/bin/nvcc --version",
        "Cuda compilation tools, release 10.2, V10.2.300",
        "",
        "jetson@jetson-desktop:~$ ./deviceQuery",
        "Detected 1 CUDA Capable device(s)",
        "Device 0: NVIDIA Tegra X1",
        "Result = PASS",
    ]
    yy = y + h - 51
    for line in lines:
        c.drawString(x + 18, yy, line)
        yy -= 15
    c.setFont("UI", 8.5)
    c.setFillColor(HexColor("#9BB1BC"))
    c.drawString(MARGIN_X, 96, "Hazırlanma tarihi: 15 Temmuz 2026")
    c.drawString(MARGIN_X, 79, "Sürüm 1.0 - mevcut cihaz durumuna göre özelleştirilmiştir")
    c.setFillColor(GREEN)
    c.setFont("UI-Semibold", 10)
    c.drawRightString(PAGE_W - MARGIN_X, 79, "ÖĞREN • DENE • ÖLÇ • DÜZELT")


def draw_architecture(pb: PageBuilder) -> None:
    pb.ensure(202)
    c = pb.c
    top = pb.y
    boxes = [
        (MARGIN_X, top - 78, 135, 70, "Windows bilgisayar", "PowerShell • PuTTY • VNC"),
        (MARGIN_X + 185, top - 78, 135, 70, "USB bağlantısı", "Seri COM5 + RNDIS ağ"),
        (MARGIN_X + 370, top - 78, 137, 70, "Jetson Nano", "Ubuntu 18.04 • JetPack"),
    ]
    for x, y, w, h, title, sub in boxes:
        c.setFillColor(LIGHT_BLUE if "Windows" in title else LIGHT_GREEN if "Jetson" in title else LIGHT)
        c.setStrokeColor(BLUE if "Windows" in title else GREEN_DARK if "Jetson" in title else MUTED)
        c.roundRect(x, y, w, h, 7, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont("UI-Semibold", 9.2)
        c.drawCentredString(x + w / 2, y + 43, title)
        c.setFillColor(MUTED)
        c.setFont("UI", 7.5)
        c.drawCentredString(x + w / 2, y + 23, sub)
    c.setStrokeColor(GREEN)
    c.setLineWidth(2)
    c.line(MARGIN_X + 137, top - 43, MARGIN_X + 183, top - 43)
    c.line(MARGIN_X + 322, top - 43, MARGIN_X + 368, top - 43)
    c.setFillColor(GREEN)
    c.drawString(MARGIN_X + 174, top - 46, ">")
    c.drawString(MARGIN_X + 359, top - 46, ">")
    c.setFont("UI", 7.6)
    c.setFillColor(MUTED)
    c.drawCentredString(PAGE_W / 2, top - 101, "Aynı USB kablosu: terminal erişimi + yerel ağ + Windows internet paylaşımı")
    c.setFillColor(LIGHT)
    c.roundRect(MARGIN_X, top - 170, CONTENT_W, 48, 6, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Mono", 8)
    c.drawString(MARGIN_X + 14, top - 143, "Windows: 192.168.137.1  <---- USB ağ ---->  Jetson: 192.168.137.2")
    c.setFont("UI", 7.8)
    c.setFillColor(MUTED)
    c.drawString(MARGIN_X + 14, top - 159, "SSH: port 22  •  VNC :1: port 5901  •  Seri konsol: COM5 / 115200 baud")
    pb.y -= 194


def draw_storage(pb: PageBuilder) -> None:
    pb.ensure(206)
    c = pb.c
    top = pb.y
    c.setFillColor(LIGHT_BLUE)
    c.setStrokeColor(BLUE)
    c.roundRect(MARGIN_X, top - 125, 205, 106, 7, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("UI-Semibold", 11)
    c.drawString(MARGIN_X + 15, top - 43, "16 GB eMMC")
    c.setFont("UI", 8.3)
    c.setFillColor(INK)
    c.drawString(MARGIN_X + 15, top - 65, "mmcblk0 • dahili depolama")
    c.drawString(MARGIN_X + 15, top - 83, "Boot kayıtları / kurtarma kopyası")
    c.drawString(MARGIN_X + 15, top - 101, "İlk sistem burada çalışıyordu")

    c.setFillColor(LIGHT_GREEN)
    c.setStrokeColor(GREEN_DARK)
    c.roundRect(PAGE_W - MARGIN_X - 205, top - 125, 205, 106, 7, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("UI-Semibold", 11)
    c.drawString(PAGE_W - MARGIN_X - 190, top - 43, "64 GB microSD")
    c.setFont("UI", 8.3)
    c.setFillColor(INK)
    c.drawString(PAGE_W - MARGIN_X - 190, top - 65, "mmcblk1p1 • ext4 • 58 GB")
    c.drawString(PAGE_W - MARGIN_X - 190, top - 83, "Aktif kök sistem: /")
    c.drawString(PAGE_W - MARGIN_X - 190, top - 101, "15 GB kullanılmış, 41 GB boş")

    c.setStrokeColor(GREEN)
    c.setLineWidth(3)
    c.line(MARGIN_X + 214, top - 72, PAGE_W - MARGIN_X - 214, top - 72)
    c.setFillColor(GREEN)
    c.setFont("UI-Bold", 16)
    c.drawCentredString(PAGE_W / 2, top - 78, ">")
    c.setFont("UI-Semibold", 8)
    c.setFillColor(GREEN_DARK)
    c.drawCentredString(PAGE_W / 2, top - 51, "root=/dev/mmcblk1p1")
    c.setFillColor(LIGHT)
    c.roundRect(MARGIN_X, top - 181, CONTENT_W, 36, 6, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Mono", 8.3)
    c.drawCentredString(PAGE_W / 2, top - 168, "findmnt -n -o SOURCE /   →   /dev/mmcblk1p1")
    pb.y -= 198


def draw_gpio_header(pb: PageBuilder) -> None:
    pb.ensure(282)
    c = pb.c
    top = pb.y
    x0 = MARGIN_X + 88
    y0 = top - 24
    cell_w, cell_h = 34, 10.5
    c.setFont("UI-Semibold", 5.7)
    for row in range(20):
        odd = row * 2 + 1
        even = row * 2 + 2
        y = y0 - row * cell_h
        for col, pin in enumerate((odd, even)):
            x = x0 + col * 240
            highlight = pin in (6, 12)
            power = pin in (1, 2, 4, 9, 14, 17, 20, 25, 30, 34, 39)
            c.setFillColor(LIGHT_GREEN if highlight else LIGHT_AMBER if power else LIGHT)
            c.setStrokeColor(GREEN_DARK if highlight else GRID)
            c.roundRect(x, y, cell_w, 8.3, 2, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.drawCentredString(x + cell_w / 2, y + 1.7, str(pin))
    c.setFillColor(NAVY)
    c.setFont("UI-Semibold", 9)
    c.drawString(x0 - 8, top - 7, "Tek numaralı pinler")
    c.drawString(x0 + 226, top - 7, "Çift numaralı pinler")
    c.setFillColor(GREEN_DARK)
    c.setFont("UI-Semibold", 8.4)
    c.drawString(MARGIN_X, top - 252, "LED deneyinde kullanılanlar: fiziksel pin 12 = dijital çıkış, fiziksel pin 6 = GND")
    c.setFillColor(MUTED)
    c.setFont("UI", 7.7)
    c.drawString(MARGIN_X, top - 269, "Şema yönü mutlaka kart üzerindeki Pin 1 işaretiyle doğrulanmalıdır; kartı kapatmadan kablo taşımayın.")
    pb.y -= 282


def draw_breadboard(pb: PageBuilder) -> None:
    pb.ensure(230)
    c = pb.c
    top = pb.y
    # Board
    c.setFillColor(HexColor("#E8ECEE"))
    c.setStrokeColor(MUTED)
    c.roundRect(MARGIN_X, top - 180, CONTENT_W, 150, 9, fill=1, stroke=1)
    # rails
    c.setStrokeColor(RED)
    c.line(MARGIN_X + 22, top - 55, PAGE_W - MARGIN_X - 22, top - 55)
    c.setStrokeColor(BLUE)
    c.line(MARGIN_X + 22, top - 158, PAGE_W - MARGIN_X - 22, top - 158)
    # holes
    c.setFillColor(HexColor("#C1C9CD"))
    for col in range(24):
        for row in range(5):
            c.circle(MARGIN_X + 28 + col * 19, top - 76 - row * 13, 1.7, fill=1, stroke=0)
    # LED
    led_x = MARGIN_X + 197
    c.setFillColor(HexColor("#F7D14B"))
    c.setStrokeColor(AMBER)
    c.circle(led_x, top - 94, 12, fill=1, stroke=1)
    c.setStrokeColor(INK)
    c.line(led_x - 5, top - 106, led_x - 5, top - 139)
    c.line(led_x + 5, top - 106, led_x + 5, top - 129)
    # resistor
    c.setStrokeColor(INK)
    c.line(MARGIN_X + 80, top - 94, MARGIN_X + 115, top - 94)
    c.setFillColor(HexColor("#D8BE82"))
    c.roundRect(MARGIN_X + 115, top - 100, 50, 12, 4, fill=1, stroke=1)
    c.line(MARGIN_X + 165, top - 94, led_x - 12, top - 94)
    c.setFillColor(NAVY)
    c.setFont("UI-Semibold", 8)
    c.drawString(MARGIN_X + 108, top - 82, "220-330 Ω")
    # wires labels
    c.setStrokeColor(GREEN_DARK)
    c.setLineWidth(2)
    c.line(MARGIN_X + 10, top - 94, MARGIN_X + 80, top - 94)
    c.setFillColor(GREEN_DARK)
    c.drawString(MARGIN_X + 12, top - 82, "Pin 12")
    c.setStrokeColor(BLUE)
    c.line(led_x - 5, top - 139, led_x - 5, top - 158)
    c.line(led_x - 5, top - 158, PAGE_W - MARGIN_X - 30, top - 158)
    c.setFillColor(BLUE)
    c.drawString(PAGE_W - MARGIN_X - 83, top - 148, "Pin 6 / GND")
    c.setFillColor(INK)
    c.setFont("UI", 7.8)
    c.drawString(MARGIN_X + 18, top - 202, "Akım yolu: Pin 12 → direnç → LED uzun bacak (anot) → LED kısa bacak (katot) → GND")
    pb.y -= 220


def draw_fan_scale(pb: PageBuilder) -> None:
    pb.ensure(170)
    c = pb.c
    top = pb.y
    x = MARGIN_X + 25
    width = CONTENT_W - 50
    c.setFillColor(LIGHT)
    c.roundRect(MARGIN_X, top - 125, CONTENT_W, 105, 7, fill=1, stroke=0)
    c.setFillColor(GRID)
    c.roundRect(x, top - 72, width, 18, 9, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.roundRect(x, top - 72, width, 18, 9, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("UI-Bold", 8)
    for val, pos in [(0, 0), (64, .25), (128, .5), (192, .75), (255, 1)]:
        xx = x + width * pos
        c.setStrokeColor(NAVY)
        c.line(xx, top - 79, xx, top - 48)
        c.drawCentredString(xx, top - 42, str(val))
    c.setFont("UI", 7.6)
    c.setFillColor(MUTED)
    c.drawString(x, top - 97, "Kapalı")
    c.drawCentredString(x + width / 2, top - 97, "Orta hız")
    c.drawRightString(x + width, top - 97, "Tam hız")
    pb.y -= 144


def page(c, page_no: int, section: str, title: str, body) -> None:
    pb = PageBuilder(c, page_no, section, title)
    key = f"page-{page_no}"
    c.bookmarkPage(key)
    c.addOutlineEntry(title, key, level=0, closed=False)
    body(pb)
    pb.finish()
    c.showPage()


def build_pdf() -> Path:
    register_fonts()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUTPUT_PDF), pagesize=A4, pageCompression=1)
    c.setTitle("Jetson Nano Kurulum, Linux, GPIO ve Kodlama Rehberi")
    c.setAuthor("Codex - kullanıcı kurulumu temel alınarak")
    c.setSubject("Waveshare Jetson Nano Dev Kit A için başsız kurulum ve geliştirme kılavuzu")
    c.setCreator("ReportLab")

    draw_cover(c)
    c.showPage()

    pages = []

    def p2(pb):
        pb.h1("Bu belgeyi nasıl kullanacaksın?", "Başlangıç")
        pb.paragraph("Bu kılavuz genel bir internet özeti değildir. Senin cihazında gerçekten doğruladığımız donanım, disk, ağ, JetPack, CUDA, VNC, LED ve fan durumuna göre hazırlanmıştır. Amaç yalnızca komut kopyalamak değil; her komutun neyi değiştirdiğini anlayarak kendi projelerini kurabilmendir.")
        pb.h2("Üç katmanlı öğrenme yöntemi")
        pb.numbered("1", "Önce kavramı oku: eMMC, SD kart, SSH, GPIO veya PWM ne işe yarıyor?")
        pb.numbered("2", "Sonra yalnızca 'yazılacak komut' kutusunu çalıştır. Terminal istemini ve örnek çıktıyı kopyalama.")
        pb.numbered("3", "Çıktıyı kontrol et. Beklenen sonuç gelmediyse sonraki adıma geçme; teşhis bölümünü kullan.")
        pb.callout("En önemli terminal kuralı", "jetson@jetson-desktop:~$ yazısı komut değildir; terminalin senden komut beklediğini gösteren istemdir. 'Setting up ...', 'Result = PASS' veya '[sudo] password' gibi satırlar da çıktıdır; bunları tekrar terminale yazmazsın.", "warn")
        pb.h2("İşaretlerin anlamı")
        pb.table(["İşaret", "Anlam"], [["JETSON TERMİNALİ", "Jetson üzerindeki Ubuntu terminaline yazılır."], ["WINDOWS POWERSHELL", "Windows bilgisayarda PowerShell'e yazılır."], ["GÜVENLİK", "Donanımı korumak için mutlaka uygulanır."], ["KONTROL", "Bir değişiklik yapmaz; mevcut durumu okur."]], [120, CONTENT_W-120])
        pb.small("Belge içindeki komutlar mevcut kurulumun için hazırlanmıştır. Başka bir Jetson modeli, farklı taşıyıcı kart veya farklı JetPack sürümünde aygıt isimleri ve yollar değişebilir.")
    pages.append(("Başlangıç", "Belgeyi kullanma", p2))

    def p3(pb):
        pb.h1("Mevcut sistemin kısa kimliği", "Doğrulanan durum")
        pb.table(["Bileşen", "Senin cihazındaki durum"], [
            ["Donanım", "Waveshare JETSON-NANO-DEV-KIT-A / Jetson Nano 4 GB"],
            ["İşletim sistemi", "Ubuntu 18.04.6 LTS, aarch64"],
            ["Jetson Linux", "L4T R32.7.5, kernel 4.9.337-tegra"],
            ["JetPack", "4.6.5-b29"],
            ["CUDA", "10.2.300; nvcc çalışıyor"],
            ["GPU", "Tegra X1, Compute Capability 5.3, 128 CUDA çekirdeği"],
            ["Kök disk", "/dev/mmcblk1p1; 64 GB SD kart; ext4"],
            ["Boş alan", "Yaklaşık 41 GB"],
            ["Yerel ağ", "Jetson 192.168.137.2; Windows 192.168.137.1"],
            ["Grafik arayüz", "XFCE + TigerVNC; ekran :1"],
            ["Donanım testleri", "CUDA deviceQuery = PASS; LED GPIO testi başarılı"],
            ["Fan", "PWM hedefi başlangıçta 0; komutla 0-255 arası kontrol"],
        ], [126, CONTENT_W-126])
        pb.callout("Sürüm eşleşmesi", "JetPack 4.6.5, Jetson Linux 32.7.5 ile eşleşir. NVIDIA arşivi bu sürümün Jetson Nano'yu desteklediğini belirtir. CUDA 10.2, cuDNN ve TensorRT bu eski fakat kararlı yazılım ailesinin parçalarıdır. [2][3]", "info")
        pb.paragraph("Bu sayfa ileride bir sorun yaşadığında 'çalışan temel durum' kaydıdır. Bir güncellemeden sonra davranış değişirse önce bu tabloyla karşılaştır.")
    pages.append(("Başlangıç", "Sistem kimliği", p3))

    def p4(pb):
        pb.h1("Ekransız çalışma mimarisi", "Bağlantılar")
        pb.paragraph("HDMI ekranın ve modemin olmaması Jetson'u kullanmaya engel olmadı. Windows bilgisayar hem konsol, hem ağ geçidi, hem de uzaktaki ekran görevini üstlendi.")
        draw_architecture(pb)
        pb.h2("Üç erişim yolu neden var?")
        pb.bullet("Seri konsol (COM5): ağ bozukken bile açılış mesajlarını ve login ekranını görürsün. Kurtarma yoludur.")
        pb.bullet("SSH: hızlı, düşük veri tüketen komut satırı erişimidir. Dosya yönetimi ve kurulum için en güvenilir günlük yoldur.")
        pb.bullet("VNC: XFCE masaüstünü Windows'ta gösterir. Geany gibi grafik editörleri ve dosya yöneticisini kullanırsın.")
        pb.callout("Ana fikir", "VNC yalnızca görüntüdür; programlar Jetson üzerinde çalışır. VNC penceresini kapatmak Jetson'u kapatmaz. İnternet ise Windows paylaşımı üzerinden Jetson'a geçer.", "safe")
    pages.append(("Bağlantı", "Ekransız mimari", p4))

    def p5(pb):
        pb.h1("Donanım güvenliği: ilk beş kural", "Elektronik")
        pb.numbered("1", "GPIO pinlerine yalnızca 3.3 V mantık seviyesi uygula. 5 V'u bir GPIO girişine vermek işlemciye zarar verebilir.")
        pb.numbered("2", "LED'i dirençsiz bağlama. 220-330 ohm seri direnç akımı güvenli düzeyde sınırlar.")
        pb.numbered("3", "Motoru, fanı, röleyi veya güçlü LED'i doğrudan GPIO'dan besleme. GPIO bir güç kaynağı değil, kontrol sinyalidir.")
        pb.numbered("4", "Kablo taşırken Jetson'u düzgün kapat: sudo poweroff. Güç LED'i söndükten sonra adaptörü çıkar.")
        pb.numbered("5", "Pin numaralandırmasını kodla eşleştir. GPIO.BOARD kullanıyorsan fiziksel 1-40 numaralarını kullanırsın.")
        pb.h2("Güvenli kapatma")
        pb.code("sudo poweroff", "JETSON TERMİNALİ")
        pb.paragraph("Komuttan sonra terminal bağlantısı kopar. En az 20-30 saniye bekle; fan ve durum LED'leri durduğunda güç kablosunu çıkar. Dosya kopyalanırken fişi çekmek SD karttaki ext4 dosya sistemini bozabilir.")
        pb.callout("Fan için özel uyarı", "Kitle gelen 5 V PWM fanı yalnızca kart üzerindeki FAN konnektörüne, doğru yönde bağla. Waveshare bu fanın 0.27 A çekebildiğini bildirir; GPIO pini bu akımı taşıyamaz. [1][4]", "danger")
    pages.append(("Güvenlik", "Donanım güvenliği", p5))

    def p6(pb):
        pb.h1("Seri konsol: COM5 ile ilk erişim", "Kurtarma kanalı")
        pb.paragraph("Windows, Jetson'un micro-USB aygıtını hem ağ adaptörü hem de USB seri aygıt olarak gördü. Aygıt yöneticisinde VID_0955 ve PID_7020 olan USB Seri Cihaz COM5'ti.")
        pb.h2("Windows'ta portu bulmak")
        pb.code("Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name,PNPDeviceID", "WINDOWS POWERSHELL")
        pb.h2("PuTTY ayarları")
        pb.table(["Alan", "Değer"], [["Connection type", "Serial"], ["Serial line", "COM5"], ["Speed", "115200"], ["Data bits / Stop bits", "8 / 1"], ["Parity / Flow control", "None / None"]], [150, CONTENT_W-150])
        pb.paragraph("Open düğmesine bastığında siyah pencere açılır. Görüntü yoksa bir kez Enter'a bas. 'jetson-desktop login:' geldiğinde kullanıcı adını jetson, ardından şifreni yaz. Linux şifre yazarken ekranda yıldız göstermez; bu normaldir.")
        pb.code("Ubuntu 18.04.6 LTS jetson-desktop ttyGS0\n\njetson-desktop login: jetson\nPassword:", "BEKLENEN EKRAN")
        pb.callout("Ne zaman kullanılır?", "SSH zaman aşımına uğrarsa, IP adresi değişirse veya extlinux ayarı yüzünden açılış sorunu olursa seri konsol ilk teşhis yoludur.", "info")
    pages.append(("Bağlantı", "Seri konsol", p6))

    def p7(pb):
        pb.h1("SSH ve VNC ile günlük kullanım", "Uzaktan erişim")
        pb.h2("SSH bağlantısı")
        pb.code("ssh jetson@192.168.137.2", "WINDOWS POWERSHELL")
        pb.paragraph("İlk bağlantıda anahtar parmak izi sorusu gelir; yalnızca kendi USB bağlantındaki Jetson olduğundan eminsen yes yaz. Sonra jetson kullanıcısının şifresini gir. İstem 'jetson@jetson-desktop:~$' olduğunda artık komutlar Jetson'da çalışır.")
        pb.h2("VNC bağlantısı")
        pb.table(["Alan", "Değer"], [["Sunucu", "192.168.137.2:1"], ["TCP portu", "5901"], ["Masaüstü", "XFCE"], ["Çözünürlük", "1280 x 720"], ["Kimlik doğrulama", "vncpasswd ile belirlenen VNC şifresi"]], [140, CONTENT_W-140])
        pb.code("vncserver -list\nss -ltn | grep 5901", "JETSON TERMİNALİ")
        pb.callout("VNC güvenliği", "-localhost no ayarı VNC'yi ağ arayüzünde dinletir. Bu yapı yalnızca USB ile doğrudan bağlı yerel ağda kullanılmalıdır. Jetson'u ortak Wi-Fi ağına bağlarsan VNC'yi SSH tüneliyle sınırlandır veya güvenlik duvarı kuralı ekle.", "warn")
        pb.h2("Bağlantıyı kapatmak")
        pb.code("exit", "JETSON TERMİNALİ")
        pb.paragraph("exit yalnızca SSH oturumunu kapatır; Jetson çalışmaya devam eder. Jetson'u kapatmak için sudo poweroff kullanılır.")
    pages.append(("Bağlantı", "SSH ve VNC", p7))

    def p8(pb):
        pb.h1("Windows internet paylaşımı nasıl çalışıyor?", "Ağ")
        pb.paragraph("Modem veya Ethernet kablosu olmadan Windows'un Wi-Fi/PdaNet bağlantısı Jetson'a paylaştırıldı. Windows Internet Connection Sharing etkinleştiğinde USB Ethernet arayüzü 192.168.137.1/24 oldu; Jetson'a da 192.168.137.2/24 ve bu ağ geçidi verildi.")
        pb.h2("Jetson tarafındaki doğrulanmış profil")
        pb.code("nmcli -f connection.id,ipv4.method,ipv4.addresses,ipv4.gateway connection show l4tbr0", "JETSON TERMİNALİ")
        pb.code("connection.id:    l4tbr0\nipv4.method:      manual\nipv4.addresses:   192.168.55.1/24, 192.168.137.2/24\nipv4.gateway:     192.168.137.1", "BEKLENEN ÇIKTI")
        pb.h2("Windows tarafını kontrol et")
        pb.code("Get-NetIPAddress -InterfaceAlias 'Ethernet' -AddressFamily IPv4", "WINDOWS POWERSHELL")
        pb.paragraph("Windows'ta paylaşılan bağlantının Özellikler > Paylaşım sekmesinde internet bağlantısının Ethernet arayüzüne paylaşılması gerekir. Bu ayar değişirse Windows adresi tekrar 192.168.137.1 yapılabilir veya Jetson bağlantısı kopabilir.")
        pb.callout("Veri kullanımı", "SSH ve VNC'nin kendisi az veri kullanır. Büyük tüketim apt paketleri, CUDA/JetPack ve Python modelleridir. JetPack kurulumu birkaç gigabayt indirme ve çok daha fazla disk kullanımı doğurabilir; bu işlem tamamlandı.", "info")
    pages.append(("Ağ", "Windows internet paylaşımı", p8))

    def p9(pb):
        pb.h1("Ağ sorunlarını sırayla teşhis et", "Ağ")
        pb.paragraph("Bir ping başarısız olduğunda rastgele ayar değiştirmek yerine aşağıdaki zinciri test et. Her adım bir öncekinin üstüne kurulur.")
        pb.numbered("1", "Jetson'un kendi adresini ve arayüz durumunu gör.")
        pb.code("ip -br address\nip route", "JETSON TERMİNALİ")
        pb.numbered("2", "Windows ağ geçidine ulaşabiliyor musun?")
        pb.code("ping -c 4 192.168.137.1", "JETSON TERMİNALİ")
        pb.numbered("3", "DNS kullanmadan internete çıkabiliyor musun?")
        pb.code("ping -c 4 1.1.1.1", "JETSON TERMİNALİ")
        pb.numbered("4", "DNS isim çözümü çalışıyor mu?")
        pb.code("ping -c 4 google.com\ngetent hosts repo.download.nvidia.com", "JETSON TERMİNALİ")
        pb.table(["Sonuç", "Muhtemel neden"], [[".137.1 yok", "USB ağ / ICS / IP profili"], [".137.1 var, 1.1.1.1 yok", "Windows paylaşımı veya telefon interneti"], ["1.1.1.1 var, google.com yok", "DNS sorunu"], ["Ping var, apt yok", "Repo, TLS, saat veya sürüm uyumsuzluğu"]], [165, CONTENT_W-165])
        pb.callout("Önemli gözlem", "Senin kurulumunda 1.1.1.1 bir ara cevap vermediği hâlde google.com daha sonra yanıt verdi. Ağ durumunu tek bir denemeyle değil, bu dört testin bütünüyle değerlendir.", "warn")
    pages.append(("Ağ", "Ağ teşhisi", p9))

    def p10(pb):
        pb.h1("Linux terminalini okumayı öğren", "Linux temelleri")
        pb.code("jetson@jetson-desktop:~/projeler/led$", "TERMİNAL İSTEMİ")
        pb.table(["Parça", "Anlam"], [["jetson", "Oturum açan kullanıcı"], ["jetson-desktop", "Bilgisayarın ağ adı"], ["~", "/home/jetson klasörünün kısa adı"], ["~/projeler/led", "Şu anda bulunduğun klasör"], ["$", "Normal kullanıcı istemi; root olsaydı # görülebilirdi"]], [145, CONTENT_W-145])
        pb.h2("Günlük komutlar")
        pb.table(["Komut", "Ne yapar?"], [["pwd", "Bulunduğun klasörün tam yolunu gösterir."], ["ls -la", "Gizli dosyalarla birlikte klasör içeriğini listeler."], ["cd klasor", "Klasöre girer; cd .. bir üst klasöre çıkar."], ["mkdir -p ad", "Klasör oluşturur."], ["cp kaynak hedef", "Dosyayı kopyalar."], ["mv eski yeni", "Taşır veya adını değiştirir."], ["cat dosya", "Kısa metin dosyasını terminale basar."], ["nano dosya", "Terminal içinde metin düzenler."], ["sudo komut", "Yalnız o komutu yönetici yetkisiyle çalıştırır."]], [130, CONTENT_W-130])
        pb.callout("cat ne demek?", "cat dosyanın içeriğini okur ve ekrana yazar; dosyayı normalde değiştirmez. Örneğin cat /etc/nv_tegra_release Jetson Linux sürüm kaydını gösterdi.", "info")
    pages.append(("Linux", "Terminal temelleri", p10))

    def p11(pb):
        pb.h1("Dosyalar nerede? Home neden içinde jetson göstermiyor?", "Linux temelleri")
        pb.paragraph("Grafik arayüzde Home simgesine bastığında doğrudan /home/jetson klasörüne girersin. Bu nedenle içeride ayrıca 'jetson' adlı bir klasör görmezsin; zaten onun içindesin. Terminalde ~ işareti de aynı klasörü temsil eder.")
        pb.code("pwd\necho $HOME\nls -la ~", "JETSON TERMİNALİ")
        pb.code("/home/jetson\n/home/jetson", "BEKLENEN ÇIKTI")
        pb.h2("Önerilen kişisel düzen")
        pb.code("mkdir -p ~/projeler/{gpio,kamera,ai,denemeler}\nmkdir -p ~/belgeler ~/veri", "JETSON TERMİNALİ")
        pb.table(["Konum", "Kullanım"], [["~/projeler", "Kendi kodların"], ["~/veri", "Kamera görüntüsü ve veri seti"], ["~/belgeler", "Notlar ve proje kayıtları"], ["/etc", "Sistem ayarları; sudo gerekir"], ["/usr/local/cuda", "CUDA araçları ve örnekleri"], ["/mnt", "Geçici disk bağlama noktaları"], ["/boot/extlinux", "Açılış yapılandırması; yanlış düzenleme açılışı bozabilir"]], [155, CONTENT_W-155])
        pb.callout("Dosya adları", "Linux büyük-küçük harfe duyarlıdır. Led.py, LED.py ve led.py üç farklı addır. Dosya adlarında boşluk yerine alt çizgi kullanmak terminalde işi kolaylaştırır.", "safe")
    pages.append(("Linux", "Dosya sistemi", p11))

    def p12(pb):
        pb.h1("eMMC ve SD kart: ne yaptık?", "Depolama")
        pb.paragraph("Cihaz ilk geldiğinde Ubuntu, 16 GB eMMC üzerindeki /dev/mmcblk0p1 bölümünden çalışıyordu. JetPack kurulduğunda 16 GB hızla dolacağı için 64 GB SD kartı ext4 olarak biçimlendirdik, kök dosya sistemini kopyaladık ve açılışa yeni kökü gösterdik.")
        draw_storage(pb)
        pb.h2("Neden Windows'ta iki farklı disk görünüyordu?")
        pb.bullet("L4T-README adlı yaklaşık 16 MB bölüm, USB üzerinden sunulan küçük bilgilendirme diskidir; ana Linux diski değildir.")
        pb.bullet("Windows exFAT SD kartı görebiliyordu. Linux sistemi için ext4'e çevrilince Windows Gezgini bu bölümü normal sürücü olarak göstermez; bu bozuk olduğu anlamına gelmez.")
        pb.bullet("eMMC cihaz adı mmcblk0, harici SD kart mmcblk1 oldu. p1, diskin birinci bölümünü belirtir.")
        pb.callout("Sonuç", "findmnt ve df çıktıları aktif / kökünün /dev/mmcblk1p1 olduğunu doğruladı. Böylece sistem ve JetPack yaklaşık 58 GB'lık alanda çalışıyor.", "safe")
    pages.append(("Depolama", "eMMC ve SD", p12))

    def p13(pb):
        pb.h1("SD karta geçişin teknik özeti", "Depolama")
        pb.callout("Bu sayfa tekrar yapmak için değil", "Aşağıdaki kayıt geçmişte yaptığımız işlemi öğretmek içindir. Şu anda sistem zaten SD karttan çalışıyor; biçimlendirme komutlarını tekrar çalıştırma.", "danger")
        pb.h2("1. SD kartı ext4 hazırlama")
        pb.code("sudo mkfs.ext4 /dev/mmcblk1p1", "GEÇMİŞ İŞLEM")
        pb.paragraph("mkfs.ext4 seçilen bölüme Linux dosya sistemi kurar ve içindeki veriyi siler. Bu yüzden aygıt adı iki kez doğrulanmadan çalıştırılmaz.")
        pb.h2("2. Bağlama ve sistem kopyası")
        pb.code("sudo mkdir -p /mnt/sdroot\nsudo mount /dev/mmcblk1p1 /mnt/sdroot\nsudo cp -a --one-file-system /. /mnt/sdroot/", "GEÇMİŞ İŞLEM")
        pb.bullet("mount: SD bölümünü /mnt/sdroot klasöründe erişilebilir yapar.")
        pb.bullet("cp -a: sahiplik, izin, sembolik bağlantı ve zaman bilgisini koruyarak kopyalar.")
        pb.bullet("--one-file-system: /dev, /proc gibi sanal veya başka bağlı dosya sistemlerine taşmayı engeller.")
        pb.h2("3. Açılış kökünü değiştirme")
        pb.code("root=/dev/mmcblk0p1  →  root=/dev/mmcblk1p1", "EXTLINUX DEĞİŞİKLİĞİ")
        pb.paragraph("Hem çalışan /boot kopyasında hem de SD'deki kopyada extlinux.conf yedeği alınarak root= parametresi değiştirildi. Yeniden başlatmadan önce grep ile satır kontrol edildi.")
        pb.code("grep -n 'APPEND' /boot/extlinux/extlinux.conf", "KONTROL")
    pages.append(("Depolama", "SD geçiş özeti", p13))

    def p14(pb):
        pb.h1("Açılış doğrulaması ve kurtarma", "Depolama")
        pb.h2("Her açılıştan sonra üç hızlı kontrol")
        pb.code("findmnt -n -o SOURCE /\ndf -h /\nlsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL", "JETSON TERMİNALİ")
        pb.code("/dev/mmcblk1p1\nFilesystem       Size  Used Avail Use% Mounted on\n/dev/mmcblk1p1    58G   15G   41G  27% /", "DOĞRULANAN ÖRNEK")
        pb.h2("15 dakika siyah terminalde kalmış gibi görünürse")
        pb.paragraph("sudo reboot komutu bağlantıyı sonlandırırken PuTTY penceresi bazen eski ekranı göstermeye devam eder. Ctrl+C'nin çalışmaması, kablonun artık veri taşımaması veya terminalin kapanma aşamasında olması olabilir. Jetson'un durum LED'ini izle, 1-2 dakika sonra seri portu yeniden aç veya SSH'yi tekrar dene.")
        pb.h2("SD kart açılmazsa güvenli yaklaşım")
        pb.numbered("1", "Gücü kes, SD kartı çıkar ve eMMC'nin tek başına açılıp açılmadığını seri konsoldan kontrol et.")
        pb.numbered("2", "eMMC açılırsa SD kartı tekrar takmadan önce extlinux yedeğini ve kart dosya sistemini başka Linux bilgisayarda incele.")
        pb.numbered("3", "Dosya sistemi onarımı gerekiyorsa bağlı olmayan bölüme fsck uygulanır; çalışan / bölümüne uygulanmaz.")
        pb.callout("Yedek fikri", "eMMC'yi küçük kurtarma sistemi olarak korumak değerlidir. Proje dosyalarını ayrıca Windows'a veya başka bir diske yedekle; SD kart tek yedek değildir.", "safe")
    pages.append(("Depolama", "Açılış ve kurtarma", p14))

    def p15(pb):
        pb.h1("APT, paket ve sürüm eşleşmesi", "JetPack")
        pb.paragraph("apt, Ubuntu'nun paket yöneticisidir. Paket listesini indirir, bağımlılıkları hesaplar ve yazılımları kurar. Jetson'da Ubuntu paketlerine ek olarak NVIDIA'nın L4T deposu bulunur.")
        pb.h2("Temel komutların farkı")
        pb.table(["Komut", "Etkisi"], [["sudo apt update", "Paket listesini yeniler; yazılım kurmaz."], ["apt-cache policy paket", "Kurulu ve aday sürümleri gösterir."], ["apt-get -s install ...", "Simülasyon yapar; değişiklik yapmaz."], ["sudo apt install paket", "Paketi ve bağımlılıklarını gerçekten kurar."], ["dpkg-query -W paket", "Kurulu paket sürümünü okur."], ["sudo apt autoremove", "Kullanılmadığı düşünülen paketleri siler; önce listeyi incele."]], [150, CONTENT_W-150])
        pb.h2("Neden 4.6.5 sürümünü açıkça seçtik?")
        pb.paragraph("Depoda 4.6.6 bileşenleri de görünüyordu; fakat çalışan L4T R32.7.5 ile seçtiğimiz meta paket 4.6.5-b29'du. Yalnız nvidia-jetpack=4.6.5-b29 demek, bazı bağımlılıkların daha yeni 4.6.6 adayını seçmesine yol açtı. Bu yüzden tüm NVIDIA meta bileşenleri aynı 4.6.5-b29 sürümünde simüle edilip kurulmuştur.")
        pb.code("dpkg-query -W nvidia-jetpack nvidia-cuda nvidia-cudnn8 nvidia-tensorrt", "KONTROL")
        pb.code("nvidia-cuda       4.6.5-b29\nnvidia-cudnn8     4.6.5-b29\nnvidia-jetpack    4.6.5-b29\nnvidia-tensorrt   4.6.5-b29", "DOĞRULANAN ÇIKTI")
        pb.callout("Güncelleme politikası", "Jetson Nano'nun bu eski yazılım tabanında körlemesine do-release-upgrade veya büyük dağıtım yükseltmesi yapma. Önce cihaz görüntüsü/yedeği al ve NVIDIA L4T-JetPack eşleşmesini kontrol et.", "warn")
    pages.append(("JetPack", "APT ve sürümler", p15))

    def p16(pb):
        pb.h1("JetPack'in içinde ne var?", "JetPack")
        pb.table(["Katman", "Görevi"], [
            ["L4T / Jetson Linux", "Bootloader, Linux 4.9 çekirdeği, firmware ve NVIDIA sürücüleri"],
            ["CUDA 10.2", "GPU üzerinde paralel hesaplama; nvcc derleyicisi ve çalışma zamanı"],
            ["cuDNN 8", "Sinir ağları için optimize edilmiş konvolüsyon ve aktivasyon işlemleri"],
            ["TensorRT 8.2 ailesi", "Eğitilmiş modelleri Jetson'da düşük gecikmeyle çalıştırma"],
            ["OpenCV 4.1.1", "Görüntü okuma, işleme, kamera ve klasik bilgisayarlı görü"],
            ["VPI 1.2", "Görüntü işleme algoritmaları için NVIDIA arayüzü"],
            ["Container Runtime", "Docker konteynerlerine NVIDIA GPU erişimi"],
            ["Nsight araçları", "Profil çıkarma, performans analizi ve hata ayıklama"],
        ], [142, CONTENT_W-142])
        pb.paragraph("NVIDIA'nın JetPack 4.6.5 sayfası bunun 4.6.4 ile aynı ana bileşenleri taşıdığını ve Jetson Linux 32.7.5 güvenlik düzeltmelerini eklediğini belirtir. CUDA sürümü bu ailede 10.2'dir. [2][3]")
        pb.h2("Sürüm kontrolü")
        pb.code("cat /etc/nv_tegra_release\n/usr/local/cuda/bin/nvcc --version\npython3 --version\ngcc --version | head -n 1", "JETSON TERMİNALİ")
        pb.callout("Eski ama çalışır", "Ubuntu 18.04 ve Python 3.6 güncel masaüstü ekosistemine göre eskidir. En yeni pip paketleri bu Python sürümünü desteklemeyebilir. Projelerde uyumlu sürüm sabitleme ve sanal ortam kullanma alışkanlığı edin.", "info")
    pages.append(("JetPack", "JetPack bileşenleri", p16))

    def p17(pb):
        pb.h1("CUDA'yı nasıl doğruladık?", "GPU")
        pb.h2("Derleyici kontrolü")
        pb.code("/usr/local/cuda/bin/nvcc --version", "JETSON TERMİNALİ")
        pb.code("Cuda compilation tools, release 10.2, V10.2.300", "DOĞRULANAN ÇIKTI")
        pb.h2("deviceQuery neden önemli?")
        pb.paragraph("nvcc'nin bulunması yalnızca araçların kurulduğunu gösterir. deviceQuery küçük bir CUDA programını derler, GPU çalışma zamanını çağırır ve sürücü-runtime iletişimini sınar. Sonucun PASS olması donanımın CUDA tarafından kullanılabildiğini kanıtlar.")
        pb.code("cd ~/cuda-samples/1_Utilities/deviceQuery\nmake\n./deviceQuery", "JETSON TERMİNALİ")
        pb.table(["Alan", "Doğrulanan değer"], [["GPU", "NVIDIA Tegra X1"], ["Compute Capability", "5.3"], ["GPU çekirdeği", "128 CUDA Core"], ["Bellek", "Yaklaşık 3964 MB paylaşımlı"], ["Driver / Runtime", "10.2 / 10.2"], ["Sonuç", "Result = PASS"]], [155, CONTENT_W-155])
        pb.callout("İlk make hatasının nedeni", "Yalnız deviceQuery klasörü kopyalanınca ../../common/inc altındaki helper_cuda.h bulunamadı. Çözüm, CUDA samples ağacını ortak common klasörüyle birlikte kullanmaktı. Derleme hataları çoğu zaman koddan değil, eksik include yolundan çıkar.", "warn")
        pb.h2("Canlı performans gözlemi")
        pb.code("sudo tegrastats", "JETSON TERMİNALİ")
        pb.paragraph("tegrastats bellek, CPU/GPU yükü ve sıcaklığı sürekli basar. Durdurmak için Ctrl+C kullan.")
    pages.append(("GPU", "CUDA doğrulama", p17))

    def p18(pb):
        pb.h1("XFCE ve TigerVNC kurulumu", "Grafik arayüz")
        pb.paragraph("HDMI olmadan masaüstü görmek için hafif XFCE oturumu ve TigerVNC sunucusu kuruldu. VNC gerçek bir fiziksel monitörü kopyalamak yerine :1 numaralı sanal ekran oluşturur.")
        pb.h2("Başlangıç dosyası")
        pb.code("#!/bin/sh\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nexec dbus-launch --exit-with-session startxfce4", "~/.vnc/xstartup")
        pb.paragraph("xstartup, VNC ekranı açıldığında hangi masaüstü oturumunun başlatılacağını söyler. chmod +x komutu bu dosyayı çalıştırılabilir yaptı.")
        pb.code("chmod +x ~/.vnc/xstartup\nvncserver :1 -geometry 1280x720 -depth 24 -localhost no", "JETSON TERMİNALİ")
        pb.table(["Seçenek", "Anlam"], [[":1", "Sanal ekran 1; ağ portu 5901"], ["-geometry 1280x720", "Masaüstü çözünürlüğü"], ["-depth 24", "24 bit renk"], ["-localhost no", "USB ağından doğrudan bağlanmaya izin verir"]], [165, CONTENT_W-165])
        pb.h2("Sunucuyu durdurup yeniden başlatma")
        pb.code("vncserver -kill :1\nvncserver :1 -geometry 1280x720 -depth 24 -localhost no", "JETSON TERMİNALİ")
        pb.callout("Şifre davranışı", "vncpasswd normal erişim ve isteğe bağlı yalnız-görüntüleme şifresi sorar. Şifre en az 6 karakter olmalıdır; terminal yazarken karakter göstermez.", "info")
    pages.append(("Arayüz", "VNC kurulumu", p18))

    def p19(pb):
        pb.h1("Grafik editör ve dosya çalışma akışı", "Kodlama")
        pb.paragraph("Başlangıçta Geany gibi hafif bir editör Jetson Nano için uygundur. VS Code'un güncel sürümleri ARM64 ve Ubuntu 18.04 nedeniyle sorun çıkarabilir; editör seçimi kodun çalışmasından ayrı tutulmalıdır.")
        pb.h2("Bir Python dosyasını GUI'de çalıştırma")
        pb.numbered("1", "VNC masaüstünde Applications > Development > Geany yolunu aç.")
        pb.numbered("2", "File > New ile dosya oluştur; kodu yalnız editör alanına yapıştır.")
        pb.numbered("3", "File > Save As ile /home/jetson/projeler/gpio/led_blink.py olarak kaydet.")
        pb.numbered("4", "Terminali aç ve dosyanın bulunduğu klasöre cd ile gir.")
        pb.code("cd ~/projeler/gpio\nls -l\nsudo python3 led_blink.py", "JETSON TERMİNALİ")
        pb.h2("Yapıştırma yöntemleri")
        pb.bullet("TigerVNC Viewer'da çoğunlukla Ctrl+Shift+V veya orta fare tuşu terminale yapıştırır.")
        pb.bullet("Geany editör alanında normal Ctrl+V çalışır; önce pencerenin odakta olduğundan emin ol.")
        pb.bullet("Uzun kodu terminal satırına değil .py dosyasına yapıştır. Terminal, Python girintilerini çok satırlı yapıştırmada bozabilir.")
        pb.callout("Hızlı kontrol", "python3 -m py_compile led_blink.py komutu programı çalıştırmadan yalnızca sözdizimini denetler. Çıktı yoksa sözdizimi geçmiştir.", "safe")
        pb.code("python3 -m py_compile led_blink.py", "JETSON TERMİNALİ")
    pages.append(("Kodlama", "Editör iş akışı", p19))

    def p20(pb):
        pb.h1("Python'ın temel yapı taşları", "Kodlama")
        pb.h2("Değişken, koşul, döngü ve fonksiyon")
        pb.code("sicaklik = 52\nfan_acik = sicaklik >= 50\n\nif fan_acik:\n    print('Fan çalışmalı')\nelse:\n    print('Fan kapalı kalabilir')\n\nfor sayi in range(3):\n    print(sayi)\n\ndef pwm_yuzde(deger):\n    return round(deger * 100 / 255)\n\nprint(pwm_yuzde(128))", "PYTHON")
        pb.table(["Yapı", "Görevi"], [["değişken", "Bir değere isim verir: sicaklik = 52"], ["bool", "True veya False mantıksal durumudur"], ["if / else", "Koşula göre farklı yol seçer"], ["for", "Belirli elemanları sırayla işler"], ["while", "Koşul doğru kaldıkça döner"], ["def", "Tekrar kullanılabilir fonksiyon tanımlar"], ["return", "Fonksiyonun sonucunu çağırana verir"], ["import", "Başka modülün araçlarını kullanır"]], [135, CONTENT_W-135])
        pb.h2("Girinti neden önemli?")
        pb.paragraph("Python süslü parantez yerine girinti kullanır. if, for, while, def, try gibi iki nokta ile biten satırların içindeki kod aynı miktarda içeriden başlamalıdır. Dört boşluk standarttır; sekme ve boşluğu karıştırma.")
        pb.callout("Hata mesajını oku", "SyntaxError yazım/girinti, NameError tanımsız isim, ModuleNotFoundError eksik paket, PermissionError yetki, FileNotFoundError yol veya dosya adı hatasını düşündürür. Mesajdaki dosya ve satır numarası ilk bakacağın yerdir.", "info")
    pages.append(("Kodlama", "Python temelleri", p20))

    def p21(pb):
        pb.h1("Elektronik temeli: gerilim, akım, direnç", "GPIO")
        pb.table(["Kavram", "Kısa anlam", "Bu projedeki karşılığı"], [["Gerilim (V)", "Elektriksel potansiyel fark", "GPIO HIGH yaklaşık 3.3 V"], ["Akım (A)", "Devreden akan yük miktarı", "LED akımı dirençle sınırlandırılır"], ["Direnç (Ω)", "Akıma karşı koyar", "220-330 Ω seri direnç"], ["GND", "Ortak referans", "Jetson GND ile devre GND'si birleşir"], ["Dijital HIGH/LOW", "Mantıksal 1 / 0", "LED açık / kapalı"], ["PWM", "Hızlı aç-kapa ile ortalama güç", "Fan hızı veya uygun çıkışta parlaklık"]], [100, 160, CONTENT_W-260])
        pb.h2("LED direnci neden var?")
        pb.paragraph("Bir LED yaklaşık sabit bir ileri gerilim düşümüne sahiptir. Kalan gerilim direnç üzerinde düşer. Basit hesap I=(3.3 V - V_LED)/R'dir. Örneğin V_LED yaklaşık 2.0 V ve R=330 Ω ise akım yaklaşık 3.9 mA olur; başlangıç deneyi için güvenlidir.")
        pb.code("I = (3.3 - 2.0) / 330\nI ≈ 0.0039 A = 3.9 mA", "OHM KANUNU")
        pb.h2("GPIO'nun yapmaması gereken iş")
        pb.bullet("Fan, motor, pompa veya röle bobinine doğrudan güç vermek.")
        pb.bullet("5 V toleransı olmayan girişe 5 V uygulamak.")
        pb.bullet("Birden fazla yüksek akım yükünü 40 pin başlığından beslemek.")
        pb.callout("Güç yüklerinde çözüm", "MOSFET/transistör sürücü, ters EMK diyodu, ayrı uygun güç kaynağı ve ortak GND kullanılır. Röle modülü seçerken 3.3 V giriş uyumluluğunu ayrıca doğrula.", "danger")
    pages.append(("GPIO", "Elektronik temeli", p21))

    def p22(pb):
        pb.h1("40 pin GPIO ve numaralandırma", "GPIO")
        pb.paragraph("Jetson.GPIO kütüphanesi BOARD, BCM, TEGRA_SOC ve CVM gibi numaralandırma modlarını destekler. Başlangıçta fiziksel başlık numarasıyla düşünmek daha kolay olduğu için GPIO.BOARD kullandık. NVIDIA'nın kütüphanesi Nano dahil 40 pin Jetson başlıklarını Python ile dijital giriş/çıkış olarak kontrol eder. [5]")
        draw_gpio_header(pb)
        pb.callout("Yön kontrolü", "Kartı önüne aldığında başlığın fiziksel yönünü ürün görseli veya kart üzerindeki '1' işaretiyle doğrula. 'Pin 12' demek, saymaya rastgele bir köşeden başlamak değildir.", "warn")
        pb.h2("Kod ve kablo eşleşmesi")
        pb.code("GPIO.setmode(GPIO.BOARD)\nLED_PIN = 12", "PYTHON")
        pb.paragraph("Bu iki satır birlikte, LED kontrol sinyalinin fiziksel 12 numaralı pine gideceğini söyler. GND pinleri kodda tanımlanmaz; elektriksel dönüş yoludur.")
    pages.append(("GPIO", "GPIO pinleri", p22))

    def p23(pb):
        pb.h1("Breadboard üzerinde LED bağlantısı", "GPIO")
        draw_breadboard(pb)
        pb.h2("Bağlantıyı adım adım yap")
        pb.numbered("1", "Jetson'u sudo poweroff ile kapat ve güç kablosunu çıkar.")
        pb.numbered("2", "LED'in uzun bacağını (anot) ve kısa bacağını/düz kenar tarafını (katot) belirle.")
        pb.numbered("3", "Fiziksel pin 12'den 220-330 Ω dirence, dirençten LED uzun bacağa bağla.")
        pb.numbered("4", "LED kısa bacağını fiziksel pin 6 GND'ye bağla.")
        pb.numbered("5", "Kısa devre olmadığını gözle kontrol et; sonra gücü ver.")
        pb.callout("LED sürekli yanıyorsa", "Program çalışmıyorken yanıyorsa yanlışlıkla 3.3 V veya 5 V güç pinine bağlamış olabilirsin. Hemen kapat ve fiziksel pin numaralarını tekrar kontrol et.", "danger")
    pages.append(("GPIO", "LED bağlantısı", p23))

    def p24(pb):
        pb.h1("LED yak-söndür kodu: satır satır", "GPIO")
        pb.code("import Jetson.GPIO as GPIO\nimport time\n\nLED_PIN = 12\nGPIO.setmode(GPIO.BOARD)\nGPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)\n\ntry:\n    while True:\n        GPIO.output(LED_PIN, GPIO.HIGH)\n        time.sleep(1)\n        GPIO.output(LED_PIN, GPIO.LOW)\n        time.sleep(1)\nexcept KeyboardInterrupt:\n    print('Program durduruldu.')\nfinally:\n    GPIO.output(LED_PIN, GPIO.LOW)\n    GPIO.cleanup()", "~/projeler/gpio/led_blink.py", 7.0)
        pb.table(["Satır / yapı", "Açıklama"], [["import Jetson.GPIO", "GPIO kütüphanesini GPIO kısa adıyla yükler"], ["LED_PIN = 12", "Tek yerde pin seçimi; sonra kolay değiştirilir"], ["GPIO.setup", "Pini çıkış yapar ve başlangıçta LOW tutar"], ["while True", "Ctrl+C gelene kadar sonsuz döngü"], ["GPIO.output", "Pini HIGH veya LOW yapar"], ["time.sleep(1)", "Bir saniye bekler; CPU'yu boşuna yormaz"], ["except KeyboardInterrupt", "Ctrl+C ile temiz bir duruş sağlar"], ["finally / cleanup", "Hata olsa da LED'i kapatıp kaynakları bırakır"]], [145, CONTENT_W-145])
        pb.h2("Çalıştırma")
        pb.code("cd ~/projeler/gpio\nsudo python3 led_blink.py", "JETSON TERMİNALİ")
        pb.paragraph("Durdurmak için terminal penceresine odaklan ve Ctrl+C bas. finally bloğu LED'i LOW yapar.")
    pages.append(("GPIO", "LED kodu", p24))

    def p25(pb):
        pb.h1("İkinci proje: butonla LED kontrolü", "GPIO")
        pb.paragraph("Giriş okumayı öğrenmek için harici 10 kΩ pull-up dirençli bir buton kullan. Fiziksel pin 18 giriş olsun: 10 kΩ ile 3.3 V'a bağlı, buton basıldığında GND'ye çekilsin. Böylece bırakılmış durum HIGH, basılmış durum LOW olur.")
        pb.callout("Bağlantı güvenliği", "Butonu 5 V'a bağlama. Jetson GPIO girişi 3.3 V seviyesindedir. Kablo değişimini güç kapalıyken yap.", "danger")
        pb.code("import Jetson.GPIO as GPIO\nimport time\n\nLED_PIN = 12\nBUTTON_PIN = 18\nGPIO.setmode(GPIO.BOARD)\nGPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)\nGPIO.setup(BUTTON_PIN, GPIO.IN)\n\ntry:\n    while True:\n        basili = GPIO.input(BUTTON_PIN) == GPIO.LOW\n        GPIO.output(LED_PIN, GPIO.HIGH if basili else GPIO.LOW)\n        time.sleep(0.02)\nfinally:\n    GPIO.output(LED_PIN, GPIO.LOW)\n    GPIO.cleanup()", "button_led.py", 7.1)
        pb.h2("Yeni öğrendiğin kavramlar")
        pb.bullet("GPIO.IN: pin artık sinyal üretmez, dışarıdaki gerilimi okur.")
        pb.bullet("Pull-up: buton açıkken girişin havada kalmasını engeller ve HIGH tutar.")
        pb.bullet("Aktif düşük: basılınca GND'ye indiği için 'basılı' durumu LOW'dur.")
        pb.bullet("20 ms bekleme: mekanik buton sıçramasını ve gereksiz CPU kullanımını azaltır.")
        pb.callout("İzinler", "Başlangıçta sudo ile çalıştırabilirsin. Daha sonra NVIDIA Jetson.GPIO belgesindeki gpio grubu ve udev kuralını kurarak normal kullanıcı yetkisiyle GPIO erişimi sağlanabilir. [5]", "info")
    pages.append(("GPIO", "Buton girişi", p25))

    def p26(pb):
        pb.h1("Daha iyi kod yazma: durum, fonksiyon, log", "Kodlama")
        pb.paragraph("Donanım kodu büyüdükçe bütün işlemleri tek while döngüsüne yığmak zorlaşır. İşleri küçük fonksiyonlara böl, sabitleri başta tut ve ne olduğunu zaman damgasıyla kaydet.")
        pb.code("from datetime import datetime\nimport time\n\ndef log(mesaj):\n    zaman = datetime.now().strftime('%H:%M:%S')\n    print(f'[{zaman}] {mesaj}')\n\ndef led_deseni(pin_yaz, tekrar=3):\n    for _ in range(tekrar):\n        pin_yaz(True)\n        time.sleep(0.15)\n        pin_yaz(False)\n        time.sleep(0.15)\n\nlog('Program başladı')", "PYTHON TASARIMI")
        pb.h2("İyi alışkanlıklar")
        pb.bullet("Donanım pinlerini ve eşik değerlerini dosyanın başında sabit olarak tanımla.")
        pb.bullet("setup(), loop() ve cleanup() gibi sorumlulukları ayır.")
        pb.bullet("Her dış kaynakta hata ihtimalini düşün: kamera yok, dosya açılamadı, ağ kesildi.")
        pb.bullet("finally bloğunda GPIO'yu güvenli duruma getir.")
        pb.bullet("Programın ne yaptığını logla; yalnız 'çalışmadı' demek yerine son başarılı adımı gör.")
        pb.h2("Basit hata yakalama")
        pb.code("try:\n    deger = int(input('PWM (0-255): '))\n    if not 0 <= deger <= 255:\n        raise ValueError('Aralık 0-255 olmalı')\nexcept ValueError as hata:\n    print('Geçersiz değer:', hata)", "PYTHON")
        pb.callout("Hata saklama", "except: pass yazmak hatayı görünmez yapar. Başlangıçta istisnayı ekrana bas; gerçek nedeni görmeden donanımı suçlama.", "warn")
    pages.append(("Kodlama", "Kod yapısı", p26))

    def p27(pb):
        pb.h1("Fan kontrolü: 0 neden dönmüyordu?", "Soğutma")
        pb.paragraph("/sys/devices/pwm-fan/target_pwm dosyasındaki değer, PWM fan hedefini gösterir. Okuduğumuz değer 0'dı; bu tam kapalı anlamına gelir. Waveshare, fanı tam hızda çalıştırmak için aynı sysfs yoluna 255 yazılmasını ve 0-255 aralığının hız için kullanılmasını önerir. [4]")
        draw_fan_scale(pb)
        pb.h2("Oku, değiştir, tekrar doğrula")
        pb.code("cat /sys/devices/pwm-fan/target_pwm\nsudo sh -c 'echo 255 > /sys/devices/pwm-fan/target_pwm'\ncat /sys/devices/pwm-fan/target_pwm", "JETSON TERMİNALİ")
        pb.paragraph("sudo yalnız echo komutuna verilirse > yönlendirmesi normal kullanıcı yetkisinde kalır. Bu yüzden bütün ifadeyi root kabuğunda çalıştırmak için sudo sh -c kullanılır.")
        pb.table(["Değer", "Pratik anlam"], [["0", "Kapalı"], ["64", "Düşük hız; fanın kalkış eşiği modele göre değişebilir"], ["128", "Yaklaşık orta görev oranı"], ["192", "Yüksek hız"], ["255", "Tam hız / tanı testi"]], [125, CONTENT_W-125])
        pb.callout("Fan dönmezse", "255 okunmasına rağmen fan dönmüyorsa yazılımı bırak: sudo poweroff, gücü çıkar, fanın özel FAN soketine doğru yönde takıldığını kontrol et. Çalışırken konnektörü oynatma; fanı GPIO'ya taşıma.", "danger")
    pages.append(("Soğutma", "Fan kontrolü", p27))

    def p28(pb):
        pb.h1("Fanı açılışta çalıştırma ve sıcaklık izleme", "Soğutma")
        pb.paragraph("Geçici sysfs değeri yeniden başlatınca sıfırlanabilir. Sabit bir başlangıç hızı istersen systemd oneshot servisi kullanılabilir. Önce 128 değerinin fanı güvenilir biçimde döndürdüğünü elle test et; bazı fanlar düşük PWM'de kalkış yapamaz.")
        pb.h2("Servis dosyası örneği")
        pb.code("[Unit]\nDescription=Jetson PWM fan başlangıç hızı\nAfter=multi-user.target\n\n[Service]\nType=oneshot\nExecStart=/bin/sh -c 'echo 160 > /sys/devices/pwm-fan/target_pwm'\nRemainAfterExit=yes\n\n[Install]\nWantedBy=multi-user.target", "/etc/systemd/system/jetson-fan.service", 6.8)
        pb.h2("Etkinleştirme ve kontrol")
        pb.code("sudo systemctl daemon-reload\nsudo systemctl enable --now jetson-fan.service\nsystemctl status jetson-fan.service --no-pager\ncat /sys/devices/pwm-fan/target_pwm", "JETSON TERMİNALİ", 7.0)
        pb.h2("Sıcaklığı izle")
        pb.code("sudo tegrastats", "JETSON TERMİNALİ")
        pb.paragraph("Fan hızını yalnız sessizliğe göre değil, gerçek sıcaklık ve iş yüküne göre seç. CUDA derleme, kamera ve yapay zekâ çıkarımı sırasında sıcaklık yükselir. Hava girişini kapatma; soğutucuyu tozdan temiz tut.")
        pb.callout("Otomatik kontrol hakkında", "Jetson'un termal altyapısıyla yarışan ikinci bir döngüyü düşünmeden kurma. Önce sabit güvenli hız ve tegrastats gözlemiyle başla. Daha sonra histerezisli sıcaklık kontrolünü ayrı proje olarak geliştir.", "warn")
    pages.append(("Soğutma", "Fan servisi", p28))

    def p29(pb):
        pb.h1("Projeleri düzenli kur: klasör, venv, Git", "Geliştirme")
        pb.h2("Örnek proje yapısı")
        pb.code("~/projeler/led-kontrol/\n├── README.md\n├── requirements.txt\n├── src/\n│   └── main.py\n├── tests/\n│   └── test_logic.py\n├── data/\n└── logs/", "KLASÖR AĞACI")
        pb.h2("Sanal ortam")
        pb.code("sudo apt install python3-venv\ncd ~/projeler/led-kontrol\npython3 -m venv .venv\nsource .venv/bin/activate\npython -m pip install --upgrade 'pip<22'\npython -m pip freeze > requirements.txt\ndeactivate", "JETSON TERMİNALİ", 6.9)
        pb.paragraph("Ubuntu 18.04'te Python 3.6 kullanıldığı için çok yeni pip/paket sürümleri uyumsuz olabilir. pip<22 örneği Python 3.6 uyumluluğunu korumak içindir; her paketin Jetson ARM64 ve CUDA 10.2 desteğini ayrıca doğrula.")
        pb.h2("Git ile sürüm kaydı")
        pb.code("git init\ngit config user.name 'Ad Soyad'\ngit config user.email 'mail@example.com'\nprintf '.venv/\n__pycache__/\n*.pyc\nlogs/\n' > .gitignore\ngit add .\ngit commit -m 'İlk çalışan sürüm'", "JETSON TERMİNALİ", 6.8)
        pb.callout("Git yedek değildir", "Git kod tarihçesidir. Depo yalnız SD kartta kalırsa kart bozulduğunda o da gider. Uzak Git sunucusuna veya Windows'a ayrıca kopyala; şifre, API anahtarı ve büyük veri setini depoya ekleme.", "info")
    pages.append(("Geliştirme", "Proje düzeni", p29))

    def p30(pb):
        pb.h1("Kamera ve OpenCV'ye ilk adım", "Bilgisayarlı görü")
        pb.paragraph("Kit A'nın temel paketinde kamera zorunlu değildir. Başlangıç için UVC uyumlu USB kamera genellikle en kolay yoldur. CSI IMX219 kullanacaksan kablo yönü, kamera portu ve nvarguscamerasrc hattı ayrıca doğrulanır.")
        pb.h2("Kamerayı işletim sisteminde gör")
        pb.code("ls -l /dev/video*\nv4l2-ctl --list-devices", "JETSON TERMİNALİ")
        pb.h2("USB kameradan tek kare kaydet")
        pb.code("import cv2\n\ncap = cv2.VideoCapture(0)\nok, frame = cap.read()\nif not ok:\n    raise RuntimeError('Kameradan kare alınamadı')\ncv2.imwrite('/home/jetson/veri/ilk_kare.jpg', frame)\ncap.release()\nprint(frame.shape)", "camera_capture.py", 7.0)
        pb.h2("Çalıştır ve dosyayı kontrol et")
        pb.code("mkdir -p ~/veri\npython3 camera_capture.py\nfile ~/veri/ilk_kare.jpg\nls -lh ~/veri/ilk_kare.jpg", "JETSON TERMİNALİ")
        pb.paragraph("Başsız sistemde cv2.imshow fiziksel görüntü sunucusu ister ve VNC oturumuyla karışabilir. İlk aşamada görüntüyü dosyaya yazıp VNC dosya yöneticisinden açmak daha güvenilirdir.")
        pb.callout("CSI kamera hattı", "JetPack 4.6.x üzerinde NVIDIA kamera yığını genellikle GStreamer nvarguscamerasrc kullanır. Rastgele bir OpenCV pip paketi kurmak, NVIDIA hızlandırmalı sistem OpenCV'sinin yerini bozabilir; önce dpkg ve cv2 sürümünü kontrol et.", "warn")
        pb.code("python3 -c \"import cv2; print(cv2.__version__); print(cv2.getBuildInformation())\"", "KONTROL", 6.7)
    pages.append(("Görü", "Kamera ve OpenCV", p30))

    def p31(pb):
        pb.h1("Yapay zekâ yolu: model eğitmek ve çalıştırmak farklıdır", "Yapay zekâ")
        pb.paragraph("Jetson Nano güçlü bir uç cihazdır fakat 4 GB belleği ve eski CUDA/Python tabanı vardır. Büyük modeli sıfırdan eğitmek yerine modeli masaüstü veya bulutta eğitip Jetson'da çıkarım yapmak daha gerçekçidir.")
        pb.h2("Önerilen model yaşam döngüsü")
        pb.numbered("1", "Problemi tanımla: sınıflandırma mı, nesne tespiti mi, segmentasyon mu?")
        pb.numbered("2", "Veri topla ve etiketle; eğitim/doğrulama/test bölümlerini ayır.")
        pb.numbered("3", "Modeli güçlü bilgisayarda eğit; doğruluk ve hataları incele.")
        pb.numbered("4", "Modeli ONNX gibi taşınabilir biçime dışa aktar.")
        pb.numbered("5", "Jetson'da desteklenen katmanlarla TensorRT engine üret.")
        pb.numbered("6", "Gerçek kamera akışında gecikme, FPS, sıcaklık ve bellek ölç.")
        pb.h2("Jetson Nano için pratik sınırlar")
        pb.table(["Tercih", "Neden"], [["Küçük giriş boyutu", "Bellek ve hesap yükünü azaltır"], ["Batch size 1", "Gerçek zamanlı uç çıkarımına uygundur"], ["FP16", "Tegra GPU'da genellikle daha hızlı ve daha az bellekli"], ["Hafif mimari", "MobileNet/SSD gibi yapılar Nano'ya daha uygundur"], ["Swap dikkatli", "Çökmeyi azaltabilir ama SD karta yoğun yazma ve yavaşlık yaratır"], ["Ölçüm", "Tahmin yerine tegrastats ve gerçek FPS kullan"]], [135, CONTENT_W-135])
        pb.callout("Uyumluluk tuzağı", "İnternetteki güncel PyTorch/Ultralytics kurulum komutları Python 3.6, ARM64 ve CUDA 10.2 ile çalışmayabilir. 'En yeni' yerine JetPack 4.6.5 uyumlu wheel/konteyner seçmelisin.", "danger")
    pages.append(("Yapay zekâ", "AI ve TensorRT", p31))

    def p32(pb):
        pb.h1("Sekiz haftalık öğrenme planı", "Yol haritası")
        pb.table(["Hafta", "Konu", "Çıktı / mini proje"], [
            ["1", "Linux terminali, dosyalar, izinler", "Klasör oluştur, dosya düzenle, log oku"],
            ["2", "Python temelleri", "Sensör verisi taklidi ve koşullu alarm"],
            ["3", "GPIO çıkışı ve elektrik", "LED desenleri; temiz kapanış"],
            ["4", "GPIO girişi ve olaylar", "Butonla mod seçen LED uygulaması"],
            ["5", "Fan, servis, sistem gözlemi", "Açılış fan servisi; tegrastats kaydı"],
            ["6", "Kamera ve OpenCV", "Kare kaydetme, gri ton, kenar bulma"],
            ["7", "Önceden eğitilmiş model", "Tek görüntü sınıflandırma veya tespit"],
            ["8", "Entegrasyon", "Kamera + model + GPIO uyarı LED'i"],
        ], [48, 175, CONTENT_W-223])
        pb.h2("Her hafta aynı döngü")
        pb.numbered("1", "Oku: kavramı ve pin/gerilim şartlarını öğren.")
        pb.numbered("2", "En küçük çalışan örneği kur.")
        pb.numbered("3", "Bir değişkeni değiştir ve sonucu tahmin et.")
        pb.numbered("4", "Hata üret: kabloyu değil, dosya adı veya yanlış aralık gibi güvenli bir şeyi bilerek boz.")
        pb.numbered("5", "Hata mesajından düzelt ve README'ye not düş.")
        pb.h2("Bitirme projesi önerisi")
        pb.paragraph("Kamera görüntüsünden belirli nesneyi algılayan, algılandığında fiziksel LED'i yakan, zamanı ve güven skorunu CSV'ye yazan, sıcaklık yükseldiğinde fan hızını güvenli seviyeye alan bir uç yapay zekâ sistemi. Her alt modül ayrı test edilebilir olmalı.")
        pb.callout("Başarı ölçütü", "Bir projenin çalışması kadar yeniden başlatınca tekrar çalışması, hata durumunda güvenli kalması ve başka birinin README ile kurabilmesi de başarıdır.", "safe")
    pages.append(("Yol haritası", "8 haftalık plan", p32))

    def p33(pb):
        pb.h1("Hızlı sorun çözme tablosu", "Başvuru")
        pb.table(["Belirti", "Önce kontrol et", "Güvenli sonraki adım"], [
            ["SSH timeout", "ip -br a; Windows .137.1", "Seri COM5'ten l4tbr0 ve route bak"],
            ["Connection refused", "ss -ltn | grep :22", "SSH servis durumunu kontrol et"],
            ["VNC açılmıyor", "vncserver -list; 5901", "Log: ~/.vnc/jetson-desktop:1.log"],
            ["İnternet yok", ".137.1 → 1.1.1.1 → alan adı", "Windows ICS ve telefon internetini kontrol et"],
            ["Disk dolu", "df -h /; du -h --max-depth=1 ~", "Önce büyük dosyayı bul; rastgele silme"],
            ["nvcc yok", "ls -l /usr/local/cuda", "JetPack paket sürümlerini dpkg-query ile bak"],
            ["GPIO izin hatası", "sudo ile test", "gpio grubu + udev kuralını kur"],
            ["LED yanmıyor", "Pin 12, GND, polarite, direnç", "Gücü kapatıp bağlantıyı doğrula"],
            ["Fan dönmüyor", "target_pwm; FAN soketi", "255 test et; sonra gücü kapatıp soketi bak"],
            ["Python modülü yok", "python3 ve pip yolu", "Doğru venv ve uyumlu paket sürümü"],
            ["SyntaxError '('", "Çıktı satırı komut diye yapıştırılmış mı?", "Yalnız kod kutusunu çalıştır"],
            ["Açılış sonrası bekleme", "Seri port yeniden oluştu mu?", "1-2 dk sonra yeni oturum aç"],
        ], [105, 175, CONTENT_W-280])
        pb.h2("Durum raporu gönderirken")
        pb.paragraph("'Olmadı' yerine çalıştırdığın tam komutu, tüm hata metnini, öncesindeki bir satırı ve şu dört çıktıyı paylaş: pwd, id, ip route, df -h /. Donanım sorunuysa gücü kesip üstten net bağlantı fotoğrafı gönder.")
        pb.code("pwd\nid\nip route\ndf -h /", "TANI PAKETİ")
        pb.callout("Kırmızı çizgi", "mkfs, fdisk, parted, rm -rf, extlinux düzenleme ve geniş sistem yükseltmeleri veri veya açılış kaybı yaratabilir. Ne yaptığını anlamadan çalıştırma; önce yedek ve aygıt adı kontrolü yap.", "danger")
    pages.append(("Başvuru", "Sorun çözme", p33))

    def p34(pb):
        pb.h1("Komut cep kartı", "Başvuru")
        pb.table(["Amaç", "Komut"], [
            ["Jetson sürümü", "cat /etc/nv_tegra_release"],
            ["Kök disk", "findmnt -n -o SOURCE /"],
            ["Disk boşluğu", "df -h /"],
            ["Diskleri listele", "lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL"],
            ["IP adresleri", "ip -br address"],
            ["Ağ rotası", "ip route"],
            ["İnternet testi", "ping -c 4 google.com"],
            ["JetPack paketleri", "dpkg-query -W nvidia-jetpack nvidia-cuda"],
            ["CUDA sürümü", "/usr/local/cuda/bin/nvcc --version"],
            ["GPU/ısı", "sudo tegrastats"],
            ["VNC oturumları", "vncserver -list"],
            ["Fan hedefi", "cat /sys/devices/pwm-fan/target_pwm"],
            ["Fan tam hız", "sudo sh -c 'echo 255 > /sys/devices/pwm-fan/target_pwm'"],
            ["Python kontrol", "python3 -m py_compile dosya.py"],
            ["Program çalıştır", "sudo python3 dosya.py"],
            ["Kapat", "sudo poweroff"],
            ["Yeniden başlat", "sudo reboot"],
        ], [132, CONTENT_W-132])
        pb.h2("Çalışan temel doğrulama")
        pb.code("findmnt -n -o SOURCE /\n/usr/local/cuda/bin/nvcc --version\ncd ~/cuda-samples/1_Utilities/deviceQuery && ./deviceQuery\ncat /sys/devices/pwm-fan/target_pwm", "JETSON TERMİNALİ", 6.9)
        pb.callout("Normal değerler", "Kök /dev/mmcblk1p1 olmalı; nvcc CUDA 10.2 göstermeli; deviceQuery PASS vermeli; fan değeri kullanımına göre 0-255 arasında olabilir.", "safe")
    pages.append(("Başvuru", "Komut cep kartı", p34))

    def p35(pb):
        pb.h1("Kaynaklar ve sürüm notu", "Kaynakça")
        pb.paragraph("Bu belge, 15 Temmuz 2026 tarihinde erişilen resmi üretici/NVIDIA kaynakları ile cihazdan alınan gerçek terminal çıktıları birleştirilerek hazırlanmıştır. Web sayfaları ileride değişebilir; Jetson Nano 4.6.x belgeleri arşiv sayfalarında tutulur.")
        sources = [
            ("[1] Waveshare Jetson Nano Development Kit A ürün sayfası", "https://www.waveshare.com/jetson-nano-dev-kit-a.htm", "Kartta 16 GB eMMC, TF kart desteği, GPIO, fan başlıkları ve Kit A aksesuarları."),
            ("[2] NVIDIA JetPack SDK 4.6.5", "https://developer.nvidia.com/jetpack-sdk-465", "JetPack 4.6.5 ve L4T 32.7.5 ilişkisi; CUDA, TensorRT, cuDNN ve OpenCV bileşenleri."),
            ("[3] NVIDIA JetPack Archive", "https://developer.nvidia.com/embedded/jetpack-archive", "Jetson Nano için JetPack 4.6.5 / L4T 32.7.5 sürüm eşleşmesi."),
            ("[4] Waveshare Fan-4020-PWM-5V Wiki", "https://www.waveshare.com/wiki/Fan-4020-PWM-5V", "FAN soketi, 0-255 PWM kontrolü, kablo işlevleri ve fan teknik değerleri."),
            ("[5] NVIDIA Jetson.GPIO", "https://github.com/NVIDIA/jetson-gpio", "40 pin GPIO, Python API, örnekler, gpio grubu ve udev izinleri."),
            ("[6] NVIDIA Jetson Linux 32.7.5 Release Notes", "https://docs.nvidia.com/jetson/archives/l4t-archived/l4t-3275/pdf/Jetson_Linux_Release_Notes_R32.7.5_GA.pdf", "Ubuntu 18.04, kernel 4.9.337, aarch64 ve Jetson Nano desteği."),
        ]
        for title, url, desc in sources:
            pb.h2(title, BLUE)
            pb.small(desc, INK)
            pb.small(url, BLUE)
        pb.callout("Cihazın kayıtlı çalışan durumu", "Ubuntu 18.04.6 LTS • L4T R32.7.5 • JetPack 4.6.5-b29 • CUDA 10.2.300 • /dev/mmcblk1p1 root • XFCE/TigerVNC :1 • USB ağ 192.168.137.2 • deviceQuery PASS", "safe")
        pb.small("Bu kılavuz eğitim amaçlıdır. Donanım bağlantıları ve güç tasarımı projeye göre ayrıca ölçülmeli; kritik veya yüksek güçlü yüklerde uygun sürücü devresi kullanılmalıdır.")
    pages.append(("Kaynakça", "Kaynaklar", p35))

    # Render content pages. Cover is page 1, so content starts at 2.
    for idx, (section, title, body) in enumerate(pages, start=2):
        page(c, idx, section, title, body)

    c.save()
    return OUTPUT_PDF


if __name__ == "__main__":
    path = build_pdf()
    print(path)
