import os
from werkzeug.utils import secure_filename
from data.database import add_item

UPLOAD_FOLDER = 'static/uploads'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def handle_new_item(form_data, file_data):
    title = form_data.get('title')
    description = form_data.get('description')
    category = form_data.get('category')
    price = form_data.get('price') or None
    image = file_data.get('image')

    if not (title and description and category and image):
        raise ValueError("All fields except price are required!")

    filename = secure_filename(image.filename)
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    image.save(image_path)

    add_item(title, description, category, price, image_path)
