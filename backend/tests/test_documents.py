"""Tests d'intégration HTTP des routes documents (PRD-02).

Couvre les critères d'acceptation CA-01 à CA-14 (sauf CA-10/CA-11 versionnement
et CA-12 lien courrier qui dépendent de fonctionnalités non livrées en v1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, AuditLog, Categorie, Document, Tenant
from app.services.password import hacher_mot_de_passe


# Petit PDF minimal valide (1 page blanche). Sert d'entrée binaire pour
# vérifier la détection MIME serveur.
PDF_MINIMAL = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n"
    b"0000000053 00000 n\n0000000100 00000 n\n"
    b"trailer<</Size 4/Root 1 0 R>>startxref\n160\n%%EOF"
)

# PNG 1x1 transparent
PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00"
    b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _upload_payload(
    contenu: bytes, *, titre: str, categorie_id: int, **kw
) -> dict:
    """Construit le dict de paramètres httpx pour un upload multipart."""
    meta = {"titre": titre, "categorie_id": categorie_id, **kw}
    return {
        "files": {"fichier": ("test.pdf", contenu, "application/pdf")},
        "data": {"metadonnees": json.dumps(meta)},
    }


# ----- Upload basique --------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_pdf_chiffre_et_enregistre(
    client: AsyncClient,
    db: AsyncSession,
    archiviste: Agent,
    categorie: Categorie,
    storage_dir: Path,
) -> None:
    """CA-01 : upload PDF → enregistrement créé + fichier chiffré sur disque."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/documents",
        **_upload_payload(PDF_MINIMAL, titre="Mon PDF", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["titre"] == "Mon PDF"
    assert body["mime"] == "application/pdf"
    assert body["statut"] == "pret"
    assert len(body["checksum_sha256"]) == 64  # SHA-256 hex

    # Le fichier chiffré existe dans le tenant
    chemin = storage_dir / str(archiviste.tenant_id) / f"{body['checksum_sha256']}.enc"
    assert chemin.exists()
    octets = chemin.read_bytes()
    assert PDF_MINIMAL not in octets, "Le contenu brut ne doit pas se trouver sur disque"


@pytest.mark.asyncio
async def test_upload_inscrit_audit_log(
    client: AsyncClient,
    db: AsyncSession,
    archiviste: Agent,
    categorie: Categorie,
) -> None:
    """CA-14 : audit_log contient document.upload après upload réussi."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/documents",
        **_upload_payload(b"Hello world", titre="T", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201

    rows = await db.execute(
        select(AuditLog).where(
            AuditLog.action == "document.upload",
            AuditLog.tenant_id == archiviste.tenant_id,
        )
    )
    log = rows.scalar_one()
    assert log.entite == "documents"
    assert log.agent_id == archiviste.id


# ----- Déduplication ---------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_doublon_409_avec_id_existant(
    client: AsyncClient, archiviste: Agent, categorie: Categorie
) -> None:
    """CA-02 : upload du même contenu deux fois → HTTP 409 avec id existant."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    contenu = b"contenu identique pour test dedup"

    response1 = await client.post(
        "/api/documents",
        **_upload_payload(contenu, titre="Premier", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response1.status_code == 201
    id_existant = response1.json()["id"]

    response2 = await client.post(
        "/api/documents",
        **_upload_payload(contenu, titre="Doublon", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response2.status_code == 409
    assert "déjà présent" in response2.json()["detail"]
    assert response2.headers.get("X-Document-Existant-Id") == str(id_existant)


@pytest.mark.asyncio
async def test_meme_contenu_dans_deux_tenants_distincts(
    client: AsyncClient,
    db: AsyncSession,
    archiviste: Agent,
    autre_tenant: Tenant,
    categorie: Categorie,
) -> None:
    """CA-03 : isolation tenant — même fichier dans deux tenants = deux docs distincts."""
    contenu = b"contenu partage entre tenants"

    # Upload tenant A
    token_a = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response_a = await client.post(
        "/api/documents",
        **_upload_payload(contenu, titre="A", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token_a),  # type: ignore[attr-defined]
    )
    assert response_a.status_code == 201

    # Créer une catégorie + agent dans le second tenant, puis upload
    cat_b = Categorie(tenant_id=autre_tenant.id, libelle="cat-b")
    agent_b = Agent(
        tenant_id=autre_tenant.id,
        login="archb",
        password_hash=hacher_mot_de_passe("Password123!"),
        auth_provider="local",
        nom="B",
        prenom="Arch",
        email="archb@test.local",
        role_id=2,
        actif=True,
    )
    db.add_all([cat_b, agent_b])
    await db.flush()

    token_b = await pytest.jeton_pour(client, "archb")  # type: ignore[attr-defined]
    response_b = await client.post(
        "/api/documents",
        **_upload_payload(contenu, titre="B", categorie_id=cat_b.id),
        headers=pytest.en_tete_auth(token_b),  # type: ignore[attr-defined]
    )
    assert response_b.status_code == 201, response_b.text

    # Deux documents distincts en base
    nb = await db.scalar(select(Document.id).where(Document.checksum_sha256.is_not(None)))
    assert nb is not None
    docs = (await db.execute(select(Document))).scalars().all()
    assert len({d.tenant_id for d in docs}) == 2


# ----- Streaming déchiffré ---------------------------------------------------


@pytest.mark.asyncio
async def test_contenu_dechiffre_identique_a_l_original(
    client: AsyncClient, archiviste: Agent, categorie: Categorie
) -> None:
    """CA-04 : GET /contenu retourne les octets exactement identiques à l'upload."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    contenu = b"\x00\x01PAYLOAD-BINAIRE\xff\xfe" + b"abcdef" * 100

    upload = await client.post(
        "/api/documents",
        **_upload_payload(contenu, titre="X", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]

    response = await client.get(
        f"/api/documents/{doc_id}/contenu",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    assert response.content == contenu
    assert response.headers.get("cache-control") == "no-store"


@pytest.mark.asyncio
async def test_acces_contenu_par_autre_tenant_404(
    client: AsyncClient,
    db: AsyncSession,
    archiviste: Agent,
    autre_tenant: Tenant,
    categorie: Categorie,
) -> None:
    """CA-05 : un agent d'un autre tenant ne voit même pas l'existence."""
    # Upload côté tenant A
    token_a = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    up = await client.post(
        "/api/documents",
        **_upload_payload(b"secret A", titre="docA", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token_a),  # type: ignore[attr-defined]
    )
    doc_id = up.json()["id"]

    # Agent du tenant B
    agent_b = Agent(
        tenant_id=autre_tenant.id,
        login="agentb",
        password_hash=hacher_mot_de_passe("Password123!"),
        auth_provider="local",
        nom="B",
        prenom="Agent",
        email="b@b.local",
        role_id=2,
        actif=True,
    )
    db.add(agent_b)
    await db.flush()
    token_b = await pytest.jeton_pour(client, "agentb")  # type: ignore[attr-defined]

    response = await client.get(
        f"/api/documents/{doc_id}/contenu",
        headers=pytest.en_tete_auth(token_b),  # type: ignore[attr-defined]
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confidentiel_403_pour_agent_standard(
    client: AsyncClient,
    db: AsyncSession,
    archiviste: Agent,
    agent_standard: Agent,
    categorie: Categorie,
) -> None:
    """CA-06 : document confidentiel → 403 pour agent_standard sur /contenu."""
    token_arch = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    up = await client.post(
        "/api/documents",
        **_upload_payload(
            b"top secret",
            titre="confid",
            categorie_id=categorie.id,
            confidentiel=True,
        ),
        headers=pytest.en_tete_auth(token_arch),  # type: ignore[attr-defined]
    )
    doc_id = up.json()["id"]

    token_std = await pytest.jeton_pour(client, agent_standard.login)  # type: ignore[attr-defined]
    response = await client.get(
        f"/api/documents/{doc_id}/contenu",
        headers=pytest.en_tete_auth(token_std),  # type: ignore[attr-defined]
    )
    assert response.status_code == 403


# ----- Validation ------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_sans_categorie_422(
    client: AsyncClient, archiviste: Agent
) -> None:
    """CA-07 : `categorie_id` absente → HTTP 422."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    meta = {"titre": "Test"}  # categorie_id manquante
    response = await client.post(
        "/api/documents",
        files={"fichier": ("test.pdf", b"data", "application/pdf")},
        data={"metadonnees": json.dumps(meta)},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mime_serveur_ignore_le_client(
    client: AsyncClient, archiviste: Agent, categorie: Categorie
) -> None:
    """CA-09 : un PNG envoyé sous .pdf est détecté image/png côté serveur.

    Note : si python-magic n'est pas dispo en venv local (Windows sans
    libmagic), le service retombe sur 'application/octet-stream'. Le test
    vérifie au minimum que le MIME client n'est pas mémorisé tel quel.
    """
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    response = await client.post(
        "/api/documents",
        files={
            # Extension et MIME-client mensongers
            "fichier": ("photo.pdf", PNG_1x1, "application/pdf")
        },
        data={
            "metadonnees": json.dumps(
                {"titre": "image-renommee", "categorie_id": categorie.id}
            )
        },
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    # Le serveur doit avoir détecté image/png ou retombé sur octet-stream,
    # mais en aucun cas application/pdf (mensonge client).
    assert body["mime"] != "application/pdf"


# ----- Suppression -----------------------------------------------------------


@pytest.mark.asyncio
async def test_suppression_par_superviseur_invisible_dans_recherche(
    client: AsyncClient,
    superviseur: Agent,
    categorie: Categorie,
) -> None:
    """CA-13 : DELETE → soft delete, absent de GET /documents."""
    token = await pytest.jeton_pour(client, superviseur.login)  # type: ignore[attr-defined]
    up = await client.post(
        "/api/documents",
        **_upload_payload(b"a supprimer", titre="trash", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    doc_id = up.json()["id"]

    del_response = await client.delete(
        f"/api/documents/{doc_id}",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert del_response.status_code == 200

    # Plus dans la liste
    liste = await client.get(
        "/api/documents",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    ids = {d["id"] for d in liste.json()}
    assert doc_id not in ids

    # Détail aussi en 404
    detail = await client.get(
        f"/api/documents/{doc_id}",
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert detail.status_code == 404


@pytest.mark.asyncio
async def test_suppression_par_agent_standard_403(
    client: AsyncClient,
    archiviste: Agent,
    agent_standard: Agent,
    categorie: Categorie,
) -> None:
    """Suppression réservée au superviseur."""
    token_arch = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    up = await client.post(
        "/api/documents",
        **_upload_payload(b"data", titre="d", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token_arch),  # type: ignore[attr-defined]
    )
    doc_id = up.json()["id"]

    token_std = await pytest.jeton_pour(client, agent_standard.login)  # type: ignore[attr-defined]
    response = await client.delete(
        f"/api/documents/{doc_id}",
        headers=pytest.en_tete_auth(token_std),  # type: ignore[attr-defined]
    )
    assert response.status_code == 403


# ----- Mise à jour -----------------------------------------------------------


@pytest.mark.asyncio
async def test_maj_metadonnees_par_createur(
    client: AsyncClient, archiviste: Agent, categorie: Categorie
) -> None:
    """L'auteur peut modifier les métadonnées de son propre document."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    up = await client.post(
        "/api/documents",
        **_upload_payload(b"abc", titre="ancien", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    doc_id = up.json()["id"]

    response = await client.put(
        f"/api/documents/{doc_id}",
        json={"titre": "nouveau", "mots_cles": "test, document"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 200, response.text
    assert response.json()["titre"] == "nouveau"


@pytest.mark.asyncio
async def test_seul_superviseur_modifie_confidentiel(
    client: AsyncClient, archiviste: Agent, categorie: Categorie
) -> None:
    """RG-3 §5.5 PRD-02 : un archiviste ne peut pas toggler `confidentiel`."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]
    up = await client.post(
        "/api/documents",
        **_upload_payload(b"abc", titre="t", categorie_id=categorie.id),
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    doc_id = up.json()["id"]

    response = await client.put(
        f"/api/documents/{doc_id}",
        json={"confidentiel": True},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 403


# ----- Recherche FTS ---------------------------------------------------------


@pytest.mark.asyncio
async def test_recherche_par_mot_cle(
    client: AsyncClient, archiviste: Agent, categorie: Categorie
) -> None:
    """Recherche FTS sur titre + mots_cles."""
    token = await pytest.jeton_pour(client, archiviste.login)  # type: ignore[attr-defined]

    # Trois documents avec des termes distincts
    for titre, mots in [
        ("Rapport annuel 2026", "finance budget"),
        ("Compte-rendu réunion", "rh équipe"),
        ("Facture fournisseur", "compta tva"),
    ]:
        await client.post(
            "/api/documents",
            **_upload_payload(
                titre.encode() + b"\n" + mots.encode(),
                titre=titre,
                categorie_id=categorie.id,
                mots_cles=mots,
            ),
            headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
        )

    response = await client.get(
        "/api/documents",
        params={"q": "budget"},
        headers=pytest.en_tete_auth(token),  # type: ignore[attr-defined]
    )
    assert response.status_code == 200
    titres = [d["titre"] for d in response.json()]
    assert "Rapport annuel 2026" in titres
    assert "Facture fournisseur" not in titres
