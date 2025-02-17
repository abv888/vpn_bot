from fileinput import filename

import qrcode
from io import BytesIO

from PIL import Image


def generate_qrcode(data, file_path):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(file_path)

def create_qr_with_logo(data,file_path, qr_size=10, logo_size_ratio=0.5):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=qr_size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    logo = Image.open("resources/logo.png").convert("RGBA")

    logo_size = int(min(qr_img.size) * logo_size_ratio)
    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

    pos = ((qr_img.size[0] - logo_size) // 2, (qr_img.size[1] - logo_size) // 2)

    qr_img.paste(logo, pos, mask=logo)

    qr_img.save(file_path)
