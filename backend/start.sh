#!/usr/bin/env sh
# Démarrage de l'API sur Render : migrations puis serveur.
# Déporté dans un script pour éviter les soucis de guillemets/`&&` dans
# `dockerCommand` (Render interprétait toute la chaîne comme un seul programme).
set -e

echo "==> Migrations Alembic"
alembic upgrade head

echo "==> Démarrage uvicorn sur le port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
