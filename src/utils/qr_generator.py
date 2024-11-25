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
    # Создаем QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # Высокая коррекция ошибок, чтобы логотип не повредил QR
        box_size=qr_size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # Создаем изображение QR-кода
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    # Открываем изображение логотипа
    logo = Image.open("resources/logo.png").convert("RGBA")

    # Определяем размер логотипа в зависимости от QR-кода
    logo_size = int(min(qr_img.size) * logo_size_ratio)
    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

    # Определяем позицию логотипа в центре QR-кода
    pos = ((qr_img.size[0] - logo_size) // 2, (qr_img.size[1] - logo_size) // 2)

    # Вставляем логотип в центр QR-кода
    qr_img.paste(logo, pos, mask=logo)

    qr_img.save(file_path)
