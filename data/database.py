from .db_session import create_session, global_init
from .models import User, Item, Comment
from sqlalchemy.sql import func

def init_db():
    global_init("db/database.db")

def add_user(username, email, password):
    session = create_session()
    user = User(username=username, email=email)
    user.set_password(password)
    session.add(user)
    session.commit()
    session.close()

def get_user_by_email(email):
    session = create_session()
    user = session.query(User).filter(User.email == email).first()
    session.close()
    return user

def add_item(user_id, title, description, category, price, image_path):
    session = create_session()
    item = Item(
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        price=price,
        image_path=image_path
    )
    session.add(item)
    session.commit()
    session.close()

def get_all_items(search='', category='', max_price=''):
    session = create_session()
    query = session.query(Item)

    if search:
        query = query.filter(Item.title.ilike(f"%{search}%"))
    if category:
        query = query.filter(Item.category == category)
    if max_price:
        query = query.filter(Item.price <= float(max_price))

    items = query.all()
    session.close()
    return items

def get_items_by_user(user_id):
    session = create_session()
    items = session.query(Item).filter(Item.user_id == user_id).all()
    session.close()
    return items

def update_seller_rating(user_id):
    session = create_session()
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        session.close()
        return

    items = session.query(Item).filter(Item.user_id == user_id).all()
    all_ratings = []
    for it in items:
        ratings = session.query(Comment.rating).filter(
            Comment.item_id == it.id,
            Comment.rating != None
        ).all()
        all_ratings.extend([r[0] for r in ratings])

    if all_ratings:
        user.seller_rating = sum(all_ratings) / len(all_ratings)
    else:
        user.seller_rating = 0.0

    session.commit()
    session.close()

def add_comment(user_id, item_id, content, rating=None):
    session = create_session()
    item = session.query(Item).get(item_id)
    if not item:
        session.close()
        return {"error": "Item not found"}

    comment = Comment(
        user_id=user_id,
        item_id=item_id,
        content=content,
        rating=rating
    )
    session.add(comment)
    session.commit()

    update_seller_rating(item.user_id)

    session.close()
    return {"message": "Comment added successfully"}

def get_comments_by_item(item_id):
    session = create_session()
    comments = session.query(Comment).filter(Comment.item_id == item_id).order_by(Comment.created_at.desc()).all()
    session.close()
    return comments
