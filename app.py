import os
from flask import Flask, request, render_template, redirect, url_for, flash, g
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import joinedload

# Подключаем сессию и модели
from data.db_session import global_init, create_session
from data.email_handler import init_mail, send_email
from data.forms import RegisterForm, LoginForm
from data.models import User, Item, Comment, Message, Favorite

# Подключаем нужные функции из database.py
from data.database import (
    add_item,
    get_all_items,
    add_comment,
    get_items_by_user,
    update_seller_rating
)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '0054414@gmail.com'
app.config['MAIL_PASSWORD'] = 'qcmd rnzy qyqe uyvw'

# Инициализируем БД и почту
global_init("../db/database.db")
init_mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    session = create_session()
    user = session.query(User).get(int(user_id))
    session.close()
    return user

@app.before_request
def before_request():
    g.user = current_user

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        if not name or not email or not message:
            flash('All fields are required!', 'error')
            return redirect(url_for('contact'))

        send_email(name, email, message)
        return redirect(url_for('confirmation'))

    return render_template('contact.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = create_session()
        user = session.query(User).filter_by(email=form.email.data).first()
        if not user:
            flash('This user does not exist!', 'error')
            session.close()
            return redirect(url_for('login'))

        if check_password_hash(user.password, form.password.data):
            login_user(user)
            session.close()
            return redirect(url_for('home'))
        else:
            session.close()
            flash('Wrong password!', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        session = create_session()
        existing_user = session.query(User).filter_by(email=form.email.data).first()
        if existing_user:
            flash('This email is already registered!', 'error')
            session.close()
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        session.add(new_user)
        session.commit()
        session.close()

        flash('You successfully registered! Now you can log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/explore', methods=['GET'])
@login_required
def explore():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    max_price = request.args.get('max_price', '')

    items = get_all_items(search, category, max_price)
    return render_template('explore.html', items=items)

@app.route('/post_item', methods=['GET', 'POST'])
@login_required
def post_item():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            price = request.form.get('price') or 0

            main_image = request.files.get('image')
            if not title or not description or not main_image:
                flash("Some required fields are empty!", 'error')
                return redirect(url_for('post_item'))

            # Сохраняем главное изображение
            main_filename = secure_filename(main_image.filename)
            main_path = os.path.join(app.config['UPLOAD_FOLDER'], main_filename)
            main_image.save(main_path)

            # Относительный путь (для использования в шаблонах)
            main_rel_path = f"static/uploads/{main_filename}"

            # Сохраняем дополнительные изображения
            additional_files = request.files.getlist('images')
            additional_rel_paths = []
            for f in additional_files:
                if f and f.filename:
                    fname = secure_filename(f.filename)
                    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
                    f.save(path)
                    additional_rel_paths.append(f"static/uploads/{fname}")  # относительный путь

            session = create_session()
            new_item = Item(
                user_id=current_user.id,
                title=title,
                description=description,
                category=category,
                price=float(price),
                image_path=main_rel_path  # сохраняем относительный путь
            )
            new_item.additional_images = additional_rel_paths

            session.add(new_item)
            session.commit()
            session.close()

            flash('Your item has been created!', 'success')
            return redirect(url_for('post_confirmation'))
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('post_item'))

    return render_template('post_item.html')

@app.route('/confirmation_post')
def post_confirmation():
    return render_template('confirmation_post.html')

@app.route('/rent', methods=['GET'])
@login_required
def rent():
    """
    Отображает страницу со списком товаров,
    у которых нет цены (price=0 или price=None).
    """
    session = create_session()

    # Здесь предполагаем, что "нет цены" значит price == 0 ИЛИ price == None
    rent_items = session.query(Item).filter(
        (Item.price == 0) | (Item.price == None)
    ).all()

    session.close()
    return render_template('explore.html', items=rent_items)

@app.route('/community')
@login_required
def community():
    return render_template('community.html')

# ================== Профиль ==================
@app.route('/profile')
@login_required
def profile():
    session = create_session()
    items = session.query(Item).filter(Item.user_id == current_user.id).all()
    total_items = len(items)

    # Подсчитаем общее число отзывов на все товары пользователя
    number_of_comments = 0
    for it in items:
        number_of_comments += len(it.comments)

    # Вместо локального среднего оставляем seller_rating
    average_rating = current_user.seller_rating

    session.close()
    return render_template('profile.html',
                           items=items,
                           total_items=total_items,
                           number_of_comments=number_of_comments,
                           average_rating=average_rating)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    session = create_session()
    user = session.query(User).get(current_user.id)

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if new_username:
            user.username = new_username
        if new_email:
            user.email = new_email
        if new_password:
            if new_password != confirm_password:
                session.close()
                flash("Passwords doesn't match!", 'error')
                return redirect(url_for('edit_profile'))
            user.set_password(new_password)

        session.commit()
        session.close()
        flash('Your account info has been updated!', 'success')
        return redirect(url_for('profile'))
    else:
        current_data = {
            'username': user.username,
            'email': user.email
        }
        session.close()
        return render_template('edit_profile.html', current_data=current_data)

# ================== Отзывы / Рейтинг (продавца) ==================
@app.route('/item/<int:item_id>', methods=['GET'])
def item_detail(item_id):
    session = create_session()
    item = (
        session.query(Item)
        .options(
            joinedload(Item.owner),
            joinedload(Item.comments).joinedload(Comment.user)
        )
        .filter(Item.id == item_id)
        .first()
    )
    if not item:
        session.close()
        flash("No items found!", "error")
        return redirect(url_for('explore'))

    # Проверяем, есть ли в избранном
    fav = None
    if current_user.is_authenticated:
        fav = session.query(Favorite).filter_by(
            user_id=current_user.id,
            item_id=item.id
        ).first()

    # Рейтинг продавца (owner)
    seller_rating = item.owner.seller_rating
    comments = item.comments

    session.close()
    return render_template('item_detail.html',
                           item=item,
                           comments=comments,
                           avg_rating=seller_rating,
                           is_favorite=(fav is not None))

@app.route('/item/<int:item_id>/add_comment', methods=['POST'])
@login_required
def add_comment_route(item_id):
    comment_text = request.form.get('comment_text', '').strip()
    rating_str = request.form.get('rating')
    if not comment_text:
        flash("Empty field!", "error")
        return redirect(url_for('item_detail', item_id=item_id))

    rating = None
    if rating_str and rating_str.isdigit():
        val = int(rating_str)
        if 1 <= val <= 5:
            rating = val

    result = add_comment(
        user_id=current_user.id,
        item_id=item_id,
        content=comment_text,
        rating=rating
    )
    if "error" in result:
        flash(result["error"], "error")

    return redirect(url_for('item_detail', item_id=item_id))

# ================== Мини-мессенджер ==================
@app.route('/messages')
@login_required
def inbox():
    session = create_session()
    msgs = session.query(Message).filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).all()

    interlocutor_ids = set()
    for m in msgs:
        interlocutor_ids.add(m.sender_id)
        interlocutor_ids.add(m.receiver_id)

    interlocutors = session.query(User).filter(User.id.in_(interlocutor_ids)).all()
    session.close()

    return render_template('inbox.html', interlocutors=interlocutors)

@app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def messages_conversation(user_id):
    session = create_session()
    other_user = session.query(User).get(user_id)
    if not other_user:
        session.close()
        flash('No user have been found!', 'error')
        return redirect(url_for('inbox'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            msg = Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                content=content
            )
            session.add(msg)
            session.commit()
            flash('Message was sent successfully!', 'success')
        session.close()
        return redirect(url_for('messages_conversation', user_id=user_id))

    msgs = session.query(Message).filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()

    session.close()
    return render_template('messages_conversation.html',
                           other_user=other_user, messages=msgs)

@app.route('/favorites')
@login_required
def favorites_list():
    session = create_session()
    favs = session.query(Favorite).filter_by(user_id=current_user.id).all()
    item_ids = [f.item_id for f in favs]
    items = []
    if item_ids:
        items = session.query(Item).filter(Item.id.in_(item_ids)).all()
    session.close()
    return render_template('favorites.html', items=items)

@app.route('/favorites/add/<int:item_id>', methods=['GET'])
@login_required
def add_to_favorites(item_id):
    session = create_session()
    existing = session.query(Favorite).filter_by(
        user_id=current_user.id, item_id=item_id
    ).first()
    if existing:
        flash("This item is already in favourites!", "info")
        session.close()
        return redirect(url_for('item_detail', item_id=item_id))

    new_fav = Favorite(user_id=current_user.id, item_id=item_id)
    session.add(new_fav)
    session.commit()
    session.close()

    flash("Item has been successfully added to favourites!", "success")
    return redirect(url_for('item_detail', item_id=item_id))

@app.route('/favorites/remove/<int:item_id>', methods=['GET'])
@login_required
def remove_from_favorites(item_id):
    session = create_session()
    fav = session.query(Favorite).filter_by(
        user_id=current_user.id, item_id=item_id
    ).first()
    if not fav:
        flash("This item isn't in favourites yet!", "info")
        session.close()
        return redirect(url_for('item_detail', item_id=item_id))

    session.delete(fav)
    session.commit()
    session.close()

    flash("Item has been successfully removed from favourites!", "success")
    return redirect(url_for('item_detail', item_id=item_id))

@app.route('/delete_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def delete_item(item_id):
    """
    Удаляет товар (Item) из базы, если он принадлежит текущему пользователю.
    """
    session = create_session()
    # Ищем товар по ID и проверяем, что user_id == current_user.id
    item = session.query(Item).filter(Item.id == item_id, Item.user_id == current_user.id).first()

    if not item:
        session.close()
        flash("Item not found or you are not the owner.", "error")
        return redirect(url_for('profile'))

    # Удаляем
    session.delete(item)
    session.commit()
    session.close()

    flash("Item has been deleted!", "success")
    return redirect(url_for('profile'))


if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1')
