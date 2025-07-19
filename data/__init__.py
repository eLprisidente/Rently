from .database import (
    init_db,
    add_user,
    get_user_by_email,
    add_item,
    get_all_items,
    add_comment,            # Добавили
    get_comments_by_item    # Добавили
)
from .add_items import handle_new_item

# Инициализация базы данных при запуске приложения
init_db()
