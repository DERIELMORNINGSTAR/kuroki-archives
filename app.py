import os
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-moi-en-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', f"sqlite:///{os.path.join(basedir, 'kuroki.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Connecte-toi pour accéder à cette page."

CATEGORIES = ["Shonen", "Seinen", "Shojo", "Isekai", "Saison", "Film"]


# ---------- Modèles ----------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    articles = db.relationship('Article', backref='author', lazy=True)
    favorites = db.relationship('Favorite', backref='user', lazy=True)
    posts = db.relationship('CommunityPost', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    category = db.Column(db.String(50), default="Shonen")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    favorites = db.relationship('Favorite', backref='article', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='article', lazy=True, cascade="all, delete-orphan")


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)

    user = db.relationship('User')


class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------- Routes : Accueil ----------

@app.route('/')
def accueil():
    articles = Article.query.order_by(Article.created_at.desc()).limit(30).all()
    return render_template('index.html', articles=articles, active_tab='accueil')


@app.route('/categorie/<nom>')
def categorie(nom):
    articles = Article.query.filter_by(category=nom).order_by(Article.created_at.desc()).all()
    return render_template(
        'categorie.html', articles=articles, nom=nom,
        categories=CATEGORIES, active_tab='categories'
    )


@app.route('/categories')
def categories():
    return render_template('categories.html', categories=CATEGORIES, active_tab='categories')


@app.route('/article/<int:article_id>', methods=['GET', 'POST'])
def article(article_id):
    art = Article.query.get_or_404(article_id)
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash("Connecte-toi pour commenter.", "error")
            return redirect(url_for('login'))
        contenu = request.form.get('content', '').strip()
        if contenu:
            db.session.add(Comment(content=contenu, user_id=current_user.id, article_id=art.id))
            db.session.commit()
        return redirect(url_for('article', article_id=art.id))

    is_fav = False
    if current_user.is_authenticated:
        is_fav = Favorite.query.filter_by(user_id=current_user.id, article_id=art.id).first() is not None
    return render_template('article.html', article=art, is_fav=is_fav, active_tab='accueil')


# ---------- Routes : Communauté ----------

@app.route('/communaute', methods=['GET', 'POST'])
@login_required
def communaute():
    if request.method == 'POST':
        contenu = request.form.get('content', '').strip()
        if contenu:
            db.session.add(CommunityPost(content=contenu, user_id=current_user.id))
            db.session.commit()
        return redirect(url_for('communaute'))
    posts = CommunityPost.query.order_by(CommunityPost.created_at.desc()).limit(50).all()
    return render_template('communaute.html', posts=posts, active_tab='communaute')


# ---------- Routes : Favoris ----------

@app.route('/favoris')
@login_required
def favoris():
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    articles = [f.article for f in favs]
    return render_template('favoris.html', articles=articles, active_tab='favoris')


@app.route('/favoris/<int:article_id>/toggle', methods=['POST'])
@login_required
def toggle_favori(article_id):
    fav = Favorite.query.filter_by(user_id=current_user.id, article_id=article_id).first()
    if fav:
        db.session.delete(fav)
    else:
        db.session.add(Favorite(user_id=current_user.id, article_id=article_id))
    db.session.commit()
    return redirect(request.referrer or url_for('accueil'))


# ---------- Routes : Profil / Auth ----------

@app.route('/profil')
@login_required
def profil():
    mes_articles = Article.query.filter_by(author_id=current_user.id).order_by(Article.created_at.desc()).all()
    return render_template('profil.html', articles=mes_articles, active_tab='profil')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('accueil'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash("Remplis tous les champs.", "error")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Ce nom d'utilisateur ou cet email est déjà pris.", "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            # Le tout premier compte créé devient admin automatiquement
            if User.query.count() == 0:
                user.is_admin = True
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Bienvenue sur Kuroki Archives !", "success")
            return redirect(url_for('accueil'))
    return render_template('register.html', active_tab='profil')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('accueil'))
    if request.method == 'POST':
        identifiant = request.form.get('identifiant', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter(
            (User.username == identifiant) | (User.email == identifiant)
        ).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('accueil'))
        flash("Identifiants incorrects.", "error")
    return render_template('login.html', active_tab='profil')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('accueil'))


# ---------- Routes : Publication (admin) ----------

@app.route('/publier', methods=['GET', 'POST'])
@login_required
def publier():
    if not current_user.is_admin:
        abort(403)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        image_url = request.form.get('image_url', '').strip()
        category = request.form.get('category', CATEGORIES[0])
        if title and content:
            art = Article(
                title=title, content=content, image_url=image_url,
                category=category, author_id=current_user.id
            )
            db.session.add(art)
            db.session.commit()
            flash("Article publié !", "success")
            return redirect(url_for('article', article_id=art.id))
        flash("Titre et contenu obligatoires.", "error")
    return render_template('publier.html', categories=CATEGORIES, active_tab='profil')


# ---------- PWA ----------

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')


@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js')


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
