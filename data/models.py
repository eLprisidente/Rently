from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from flask_login import UserMixin
from .db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash
import json

class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Рейтинг продавца (средняя оценка)
    seller_rating = Column(Float, default=0.0)

    items = relationship("Item", back_populates="owner", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)

class Item(SqlAlchemyBase):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float)
    image_path = Column(String, nullable=False)
    additional_images_json = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    owner = relationship("User", back_populates="items")

    comments = relationship("Comment", back_populates="item", cascade="all, delete-orphan")

    @property
    def additional_images(self):
        if self.additional_images_json:
            return json.loads(self.additional_images_json)
        return []

    @additional_images.setter
    def additional_images(self, images_list):
        self.additional_images_json = json.dumps(images_list)

class Comment(SqlAlchemyBase):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    item = relationship("Item", back_populates="comments")
    user = relationship("User", back_populates="comments")

class Message(SqlAlchemyBase):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")

class Favorite(SqlAlchemyBase):
    __tablename__ = 'favorites'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", backref="favorites")
    item = relationship("Item", backref="favorited_by")
