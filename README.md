# Kuroki Archives

Site d'actus et de communauté anime avec comptes utilisateurs, articles par catégorie,
favoris, fil communautaire et interface PWA installable (5 onglets en bas d'écran :
Accueil, Catégories, Communauté, Favoris, Profil).

## En local (test rapide)

```
pip install -r requirements.txt
python app.py
```

Le site tourne sur http://localhost:5000

## Le premier compte créé devient automatiquement administrateur

C'est ce compte admin qui peut publier des articles (bouton "Publier" visible
dans l'onglet Profil et bouton ✎ flottant sur l'accueil). Les autres utilisateurs
peuvent commenter, mettre en favoris et poster dans l'onglet Communauté.

## Déploiement sur Render

1. Pousse ce dossier sur un repo GitHub (via l'interface web GitHub, en évitant
   toute sauvegarde locale sur la tablette pour ne pas déclencher le bug de
   renommage `-1`).
2. Sur Render : New → Web Service → connecte le repo.
3. Build command : `pip install -r requirements.txt`
4. Start command : `gunicorn app:app` (déjà dans le Procfile, Render le détecte
   automatiquement)
5. Ajoute une variable d'environnement `SECRET_KEY` avec une valeur aléatoire.
6. Déploie. La base SQLite se crée automatiquement au premier lancement.

⚠️ Sur le plan gratuit de Render, le disque n'est pas persistant entre les
redéploiements : la base SQLite sera réinitialisée à chaque déploiement. Pour
une vraie persistance, ajoute un disque Render (payant) ou passe à une base
Postgres (Render en propose une gratuite) — dis-moi si tu veux que je fasse
cette migration.

## Icônes PWA

Les fichiers `static/icons/icon-192.png` et `icon-512.png` sont à fournir
(logo Kuroki Archives). Sans eux, le site fonctionne mais l'icône d'installation
sera vide.

## Structure

```
kuroki-archives/
  app.py                 # routes, modèles, logique
  requirements.txt
  Procfile
  templates/              # 11 pages Jinja2
  static/css/style.css     # identité visuelle (encre + vermillon, screentone)
  static/js/app.js         # enregistrement du service worker
  static/manifest.json     # config PWA
  static/sw.js              # cache offline basique
```
