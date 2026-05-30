"""
Create a system admin or superuser for SchemePro.

Usage examples:
  py -3 create_admin.py --role superuser --name "Admin User" --username admin2 --email admin2@schemepro.co.ke --password Secret123
  py -3 create_admin.py --role admin --name "Office Admin" --username admin1 --email admin1@schemepro.co.ke
"""
import argparse
import getpass
from app import create_app, db, bcrypt
from app.models.user import User
from app.models.role import Role
from app.models.wallet import Wallet


def parse_args():
    parser = argparse.ArgumentParser(description='Create a SchemePro admin or superuser account.')
    parser.add_argument('--role', choices=['superuser', 'admin'], required=True,
                        help='Role of the new account.')
    parser.add_argument('--name', required=True, help='Full name for the new user.')
    parser.add_argument('--username', required=True, help='Username for login.')
    parser.add_argument('--email', required=True, help='Email address for the new user.')
    parser.add_argument('--password', help='Password for the new user. If omitted, prompts securely.')
    parser.add_argument('--region', default='', help='Optional region for the user profile.')
    parser.add_argument('--balance', type=float, default=0.0,
                        help='Initial wallet balance to seed for the new user.')
    return parser.parse_args()


def get_password(password_arg):
    if password_arg:
        return password_arg

    while True:
        password = getpass.getpass('Password: ')
        confirm = getpass.getpass('Confirm Password: ')
        if password != confirm:
            print('Passwords do not match. Try again.')
            continue
        if len(password) < 8:
            print('Password must be at least 8 characters.')
            continue
        return password


def main():
    args = parse_args()
    password = get_password(args.password)

    app = create_app()
    with app.app_context():
        db.create_all()

        role = Role.query.filter_by(tag=args.role).first()
        if not role:
            raise SystemExit(f'Role "{args.role}" not found in the database.')

        if User.query.filter_by(username=args.username.strip()).first():
            raise SystemExit(f'Username "{args.username}" is already taken.')

        if User.query.filter_by(email=args.email.strip().lower()).first():
            raise SystemExit(f'Email "{args.email}" is already registered.')

        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            name=args.name.strip(),
            username=args.username.strip(),
            email=args.email.strip().lower(),
            password=pw_hash,
            role_id=role.id,
            region=args.region.strip() or None,
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(Wallet(user_id=user.id, balance=args.balance))
        db.session.commit()

        print(f'Successfully created {args.role} account: {user.username} ({user.email})')
        if args.balance:
            print(f'Initial wallet balance: KES {args.balance:.2f}')


if __name__ == '__main__':
    main()
