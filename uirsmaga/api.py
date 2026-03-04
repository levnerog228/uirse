from flask import Blueprint, request
import database

api_bp = Blueprint('api', __name__)

@api_bp.route('/add_user', methods=['POST'])
def add_user():
    return database.add_user()

@api_bp.route('/get_users', methods=['GET'])
def get_users():
    return database.get_users()

@api_bp.route('/get_user_actions', methods=['GET'])
def get_user_actions():
    return database.get_user_actions()
